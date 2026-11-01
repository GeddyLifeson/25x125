"""Read the old and new zoning districts out of the scanned rezoning ordinances with the Claude Batch API.

The ordinance PDFs on the City Clerk's eLMS site are scans with no text layer. Section 1 of each one says
"changing all the <old> District symbols ... to those of a <new> District". A small model reads the first
two pages of each scan and returns the districts as JSON. The output is data to check, not a source: each
row keeps the model, the PDF it read and the date, and docs/ai-runs.md logs each paid run.

Steps (each one picks up where the last stopped, so a run can be resumed):
  python -m jobs.extract_rezoning_districts fetch     # matter list + ordinance PDFs into data/raw (free)
  python -m jobs.extract_rezoning_districts estimate  # page counts and a dollar estimate (free)
  python -m jobs.extract_rezoning_districts submit    # send the batches (paid, needs CLAUDE_API_KEY_25X125)
  python -m jobs.extract_rezoning_districts collect   # results into data/reference/rezoning_districts.csv
  python -m jobs.extract_rezoning_districts apply     # copy the CSV into the rezoning table
Paid steps need: python -m pip install -e ".[ai]"
Options: --limit N (first N ordinances only, for a test run), --ids O2026-0025357,... (just these).
"""

import argparse
import base64
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from jobs.load_foreclosure_auctions import USER_AGENT
from jobs.load_rezonings import TITLE, matters

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "rezonings"
PDFS = RAW / "pdf"
INDEX = RAW / "index.csv"
STATE = RAW / "batches.json"
OUT = ROOT / "data" / "reference" / "rezoning_districts.csv"
MATTER = "https://api.chicityclerkelms.chicago.gov/matter/{id}"

MODEL = "claude-haiku-5-5"
PAGES = 2  # Section 1 (old and new district) sits on page 1, sometimes running onto page 2
# Batch prices in dollars per million tokens (half the list price of $0.10 in / $0.50 out), 2026-10-06.
PRICE_IN, PRICE_OUT = 0.05, 0.25
TOKENS_PER_PAGE = 1_600  # a letter page sent as PDF: image tokens plus its (empty) text layer
PROMPT_TOKENS = 450
OUT_TOKENS = 150  # JSON answer, thinking off
BATCH_BYTES = 150_000_000  # API cap is 256 MB per batch; stay well under it

INDEX_COLUMNS = ["record_number", "matter_id", "title", "pdf_url", "file_name", "pages", "path", "error"]
OUT_COLUMNS = [
    "record_number", "from_district", "to_district", "changes", "pd_number", "map_no", "readable",
    "confidence", "codes_valid", "app_from_district", "app_to_district", "input_kind", "note", "model", "pdf_url", "extracted_on", "input_tokens", "output_tokens",
]  # fmt: skip

PROMPT = """This is a Chicago City Council zoning map amendment (a rezoning ordinance): a scan, or the OCR text
of one (OCR text may also hold the Clerk's tracking sheet and the zoning application; use the ordinance).
Section 1 says the ordinance changes "all the <old> District symbols and indications as shown on Map No. ..."
"to those of a <new> District". Read it and return:
- changes: every old -> new district change in the ordinance, in order. Write district codes the way the
  Chicago Zoning Ordinance writes them: RS-1, RS-2, RS-3, RT-3.5, RT-4, RM-4.5, RM-5, RM-5.5, RM-6, RM-6.5,
  B1-1 .. B3-5, C1-1 .. C3-5, M1-1 .. M3-3, PMD 1, DX-3 .. DX-16, DC-12, DC-16, DR-3 .. DR-10, DS-3 .. DS-5,
  PD (planned development), POS-1, POS-2, T. A scan may drop the hyphen ("RT4"); put it back ("RT-4").
  Use "PD" plus the number when a planned development is named, e.g. "PD 1234"; use "PD" alone if the
  number is not given or not yet assigned. Use "Residential-Business Planned Development" etc. only as "PD".
- pd_number: the planned development number if the new district is a numbered PD, else null.
- map_no: the map number(s) in Section 1, e.g. "3-K".
- readable: false if the page is not an ordinance or Section 1 cannot be read.
- confidence: high if the codes are printed clearly, medium if you had to fix OCR-like damage, low if guessing.
- note: anything odd in a few words (two-step change, several parcels, handwritten edits), else "".
Copy only what the document says. Do not guess a district that is not written."""

SCHEMA = {
    "type": "object",
    "properties": {
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"from_district": {"type": "string"}, "to_district": {"type": "string"}},
                "required": ["from_district", "to_district"],
                "additionalProperties": False,
            },
        },
        "pd_number": {"type": ["string", "null"]},
        "map_no": {"type": ["string", "null"]},
        "readable": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "note": {"type": "string"},
    },
    "required": ["changes", "pd_number", "map_no", "readable", "confidence", "note"],
    "additionalProperties": False,
}


def get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def pick_ordinance(attachments: list[dict]) -> dict | None:
    """The ordinance text: the 'Legislation' attachment, else a file named like an ordinance."""
    legis = [a for a in attachments if (a.get("attachmentType") or "").lower() == "legislation"]
    named = [a for a in attachments if re.search(r"ordinance", a.get("fileName") or "", re.IGNORECASE)]
    pdfs = [a for a in legis + named if (a.get("path") or "").lower().endswith(".pdf")]
    return pdfs[0] if pdfs else None


def read_index() -> dict[str, dict]:
    if not INDEX.exists():
        return {}
    with INDEX.open(newline="", encoding="utf-8") as f:
        return {r["record_number"]: r for r in csv.DictReader(f)}


def write_index(rows: dict[str, dict]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with INDEX.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, INDEX_COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: r["record_number"]))


def page_count(data: bytes) -> int:
    from pypdf import PdfReader

    return len(PdfReader(io.BytesIO(data)).pages)


def fetch_one(m: dict) -> dict:
    rec = m["recordNumber"]
    row = {"record_number": rec, "matter_id": m["matterId"], "title": " ".join(m["title"].split())}
    try:
        detail = json.loads(get(MATTER.format(id=m["matterId"])))
        att = pick_ordinance(detail.get("attachments") or [])
        if not att:
            return row | {"error": "no ordinance attachment"}
        path = PDFS / f"{rec}.pdf"
        if not path.exists():
            data = get(att["path"])
            path.write_bytes(data)
        pages = page_count(path.read_bytes())
        return row | {"pdf_url": att["path"], "file_name": att.get("fileName"), "pages": pages,
                      "path": str(path.relative_to(ROOT)), "error": ""}  # fmt: skip
    except Exception as e:  # noqa: BLE001 - one bad matter must not stop the other 6,700
        return row | {"error": str(e)[:200]}


def fetch(limit: int | None, ids: set[str] | None, workers: int = 6) -> dict[str, dict]:
    PDFS.mkdir(parents=True, exist_ok=True)
    index = read_index()
    todo = []
    for m in matters(urllib.request.urlopen):
        if not TITLE.match(m.get("title") or "") or not m.get("recordNumber"):
            continue
        if ids and m["recordNumber"] not in ids:
            continue
        done = index.get(m["recordNumber"])
        if done and not done.get("error"):
            continue
        todo.append(m)
        if limit and len(todo) >= limit:
            break
    print(f"to fetch: {len(todo):,} (already have {sum(1 for r in index.values() if not r.get('error')):,})")
    with ThreadPoolExecutor(workers) as pool:
        for i, row in enumerate(pool.map(fetch_one, todo), 1):
            index[row["record_number"]] = row
            if i % 200 == 0:
                write_index(index)
                print(f"  {i:,} fetched")
    write_index(index)
    errors = sum(1 for r in index.values() if r.get("error"))
    print(f"index: {len(index):,} ordinances, {errors:,} without a readable PDF")
    return index


def selected(limit: int | None, ids: set[str] | None) -> list[dict]:
    rows = [r for r in read_index().values() if not r.get("error") and r.get("path")]
    if ids:
        rows = [r for r in rows if r["record_number"] in ids]
    rows.sort(key=lambda r: r["record_number"])
    return rows[:limit] if limit else rows


# Claude Code cloud settings warn that ANTHROPIC_API_KEY "won't be used to authenticate requests" and keep it
# from sessions, so the project key is saved as CLAUDE_API_KEY_25X125. ANTHROPIC_API_KEY still works locally.
KEY_NAMES = ("CLAUDE_API_KEY_25X125", "ANTHROPIC_API_KEY")


def api_key() -> str | None:
    return next((os.environ[k] for k in KEY_NAMES if os.environ.get(k)), None)


def make_client():
    import anthropic

    key = api_key()
    if not key:
        sys.exit(f"no API key: set {' or '.join(KEY_NAMES)}")
    return anthropic.Anthropic(api_key=key)


def guess_tokens(row: dict, source: tuple[str, str | bytes]) -> int:
    kind, data = source
    if kind == "text":
        return round(len(data) / 3.5) + PROMPT_TOKENS
    return min(int(row["pages"] or 1), PAGES) * TOKENS_PER_PAGE + PROMPT_TOKENS


def estimate(rows: list[dict], measure: bool = False, sample: int = 5) -> dict:
    """Dollar estimate from fixed per-page and per-character guesses. With measure=True (needs a key), free
    count_tokens calls on a few real rows of each kind correct the guesses before scaling up."""
    sources = [(r, source_for(ROOT / r["path"])) for r in rows]
    kinds: dict[str, list] = {"text": [], "pdf": []}
    for r, src in sources:
        kinds[src[0]].append((r, src))
    out = {"ordinances": len(rows), "measured": measure}
    tin = 0
    if measure:
        client = make_client()
    for kind, items in kinds.items():
        guess = sum(guess_tokens(r, src) for r, src in items)
        factor = 1.0
        if measure and items:
            picks = items[:: max(1, len(items) // sample)][:sample]
            actual = 0
            for _, src in picks:
                p = request_params(src)
                actual += client.messages.count_tokens(
                    model=p["model"], messages=p["messages"], output_config=p["output_config"]
                ).input_tokens
            factor = actual / sum(guess_tokens(r, src) for r, src in picks)
        out[f"{kind}_rows"] = len(items)
        out[f"{kind}_tokens_in"] = round(guess * factor)
        tin += round(guess * factor)
    tout = len(rows) * OUT_TOKENS
    out |= {"tokens_in": tin, "tokens_out": tout, "dollars": tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT}
    return out


def first_pages(path: Path, n: int = PAGES) -> bytes:
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(str(path))
    if len(reader.pages) <= n:
        return path.read_bytes()
    w = PdfWriter()
    for p in reader.pages[:n]:
        w.add_page(p)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


TEXT_PAGES = (
    6  # bundled files: tracking sheet, ordinance, then the application (Q9 present/proposed district)
)
TEXT_CHARS = 15_000
MIN_TEXT = 300  # below this the file has no usable text layer


def source_for(path: Path) -> tuple[str, str | bytes]:
    """Most 2010-2023 files are bundles (tracking sheet, ordinance, application, 20-90 pages) that carry the
    Clerk's OCR text layer, so their text goes to the model. 2024 on, the ordinance is its own 1-2 page scan
    with no text layer, so its first pages go as a PDF the model reads as images."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "").strip() for p in reader.pages[:TEXT_PAGES]]
    if sum(len(t) for t in pages) >= MIN_TEXT:
        return "text", "\n\n".join(f"[page {i + 1}]\n{t}" for i, t in enumerate(pages))[:TEXT_CHARS]
    return "pdf", first_pages(path)


APPLICATION = re.compile(
    r"Present\s+Zoning\s+District:?\s+([A-Z][A-Z0-9.\- ]{0,12}?)\s+Proposed\s+Zoning\s+District:?\s+"
    r"([A-Z][A-Z0-9.\- ]{0,40}?)(?:\s{2,}|\n|$)",
    re.IGNORECASE,
)


def application_districts(text: str) -> tuple[str | None, str | None]:
    """Free cross-check: the application's question 9 states the present and proposed district."""
    m = APPLICATION.search(text)
    return (clean_district(m.group(1)), clean_district(m.group(2))) if m else (None, None)


def request_params(source: tuple[str, str | bytes]) -> dict:
    kind, data = source
    if kind == "text":
        doc = {"type": "document", "source": {"type": "text", "media_type": "text/plain", "data": data}}
    else:
        doc = {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(data).decode(),
            },
        }
    return {
        "model": MODEL,
        "max_tokens": 1024,
        "thinking": {"type": "disabled"},  # Haiku 5.5 accepts this at effort low; saves thinking tokens
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        "messages": [{"role": "user", "content": [doc, {"type": "text", "text": PROMPT}]}],
    }


def custom_id(record_number: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", record_number)[:64]


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"batches": []}


def save_state(state: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def submit(rows: list[dict], max_dollars: float) -> list[str]:
    est = estimate(rows, measure=True)
    print(f"estimate (count_tokens on sample rows): {json.dumps(est)}")
    if est["dollars"] > max_dollars:
        sys.exit(f"estimate ${est['dollars']:.2f} is over the ${max_dollars:.2f} cap; ask Marlon first")
    state = load_state()
    sent = {cid for b in state["batches"] for cid in b["ids"]}
    client = make_client()
    chunk, size, new = [], 0, []

    def send():
        nonlocal chunk, size
        if not chunk:
            return
        batch = client.messages.batches.create(requests=[{"custom_id": c, "params": p} for c, p in chunk])
        state["batches"].append(
            {"id": batch.id, "ids": [c for c, _ in chunk], "created": date.today().isoformat()}
        )
        save_state(state)
        new.append(batch.id)
        print(f"  batch {batch.id}: {len(chunk):,} requests")
        chunk, size = [], 0

    for r in rows:
        cid = custom_id(r["record_number"])
        if cid in sent:
            continue
        params = request_params(source_for(ROOT / r["path"]))
        n = len(params["messages"][0]["content"][0]["source"]["data"]) + 4000
        if size + n > BATCH_BYTES:
            send()
        chunk.append((cid, params))
        size += n
    send()
    return new


def clean_district(d: str | None) -> str | None:
    """Normalize spacing and hyphens: 'rt4' -> 'RT-4', 'B3 2' -> 'B3-2', 'PD1234' -> 'PD 1234'."""
    if not d:
        return None
    s = " ".join(d.upper().replace("–", "-").split())
    pd = re.match(r"^(?:.*PLANNED DEVELOPMENT|PD)\s*(?:NO\.?|#)?\s*(\d+)?\s*$", s)
    if pd:
        return f"PD {pd.group(1)}" if pd.group(1) else "PD"
    pmd = re.match(r"^PMD\s*(?:NO\.?)?\s*(\d+[A-Z]?)?$", s)
    if pmd:
        return f"PMD {pmd.group(1)}" if pmd.group(1) else "PMD"
    s = s.replace(" ", "-")
    s = re.sub(r"^([BCM])[LI](?=-?\d)", r"\g<1>1", s)  # OCR reads B1-1 as BL-1
    s = re.sub(r"^(RT|RM)-?(\d)\.S$", r"\1-\2.5", s)  # OCR reads RT-3.5 as RT3.S
    m = re.match(r"^(RS|RT|RM|DX|DC|DR|DS|POS)-?(\d+(?:\.\d)?)$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    m = re.match(r"^([BCM]\d)-?(\d)$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return s


# Every district code the Chicago Zoning Ordinance (Title 17) uses. A code outside this list is kept but
# flagged, so it gets checked by hand before it reaches a screen.
VALID = re.compile(
    r"^(?:RS-[123]|RT-3\.5|RT-4A?|RM-(?:4\.5|5|5\.5|6|6\.5)|[BC][123]-(?:1|1\.5|2|3|5)|M[123]-[123]"
    r"|PMD(?: \d+[A-Z]?)?|DC-1[26]|DX-(?:3|5|7|12|16)|DR-(?:3|5|7|10)|DS-[35]|PD(?: \d+)?|POS-[12]|T)$"
)


def valid_district(d: str | None) -> bool:
    return bool(d and VALID.match(d))


def collect() -> int:
    client = make_client()
    state = load_state()
    index = {custom_id(k): v for k, v in read_index().items()}
    rows = {}
    if OUT.exists():
        with OUT.open(newline="", encoding="utf-8") as f:
            rows = {r["record_number"]: r for r in csv.DictReader(f)}
    totals = {"in": 0, "out": 0, "cache_write": 0, "cache_read": 0, "ok": 0, "failed": 0}
    for b in state["batches"]:
        batch = client.messages.batches.retrieve(b["id"])
        if batch.processing_status != "ended":
            print(f"batch {b['id']} still {batch.processing_status}: {batch.request_counts}")
            continue
        for res in client.messages.batches.results(b["id"]):
            src = index.get(res.custom_id)
            if not src:
                continue
            if res.result.type != "succeeded":
                totals["failed"] += 1
                continue
            msg = res.result.message
            text = next((blk.text for blk in msg.content if blk.type == "text"), "")
            try:
                ans = json.loads(text)
            except json.JSONDecodeError:
                totals["failed"] += 1
                continue
            changes = [
                {"from": clean_district(c["from_district"]), "to": clean_district(c["to_district"])}
                for c in ans.get("changes") or []
            ]
            first, last = (changes[0], changes[-1]) if changes else ({}, {})
            kind, data = source_for(ROOT / src["path"])
            app_from, app_to = application_districts(data) if kind == "text" else (None, None)
            rows[src["record_number"]] = {
                "record_number": src["record_number"],
                "from_district": first.get("from"),
                "to_district": last.get("to"),
                "changes": json.dumps(changes) if changes else "",
                "pd_number": ans.get("pd_number") or "",
                "map_no": ans.get("map_no") or "",
                "readable": ans.get("readable"),
                "confidence": ans.get("confidence"),
                "codes_valid": bool(changes)
                and all(valid_district(c["from"]) and valid_district(c["to"]) for c in changes),
                "app_from_district": app_from or "",
                "app_to_district": app_to or "",
                "input_kind": kind,
                "note": ans.get("note") or "",
                "model": msg.model,
                "pdf_url": src["pdf_url"],
                "extracted_on": b["created"],
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
            }
            totals["in"] += msg.usage.input_tokens
            totals["out"] += msg.usage.output_tokens
            totals["cache_write"] += msg.usage.cache_creation_input_tokens or 0
            totals["cache_read"] += msg.usage.cache_read_input_tokens or 0
            totals["ok"] += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, OUT_COLUMNS)
        w.writeheader()
        w.writerows(sorted(rows.values(), key=lambda r: r["record_number"]))
    cost = totals["in"] / 1e6 * PRICE_IN + totals["out"] / 1e6 * PRICE_OUT
    print(f"collected {totals['ok']:,} ({totals['failed']:,} failed); tokens {totals['in']:,} in / "
          f"{totals['out']:,} out, cache {totals['cache_write']:,} written / {totals['cache_read']:,} read; about ${cost:.2f}; {len(rows):,} rows in {OUT.relative_to(ROOT)}")  # fmt: skip
    return len(rows)


def apply(url: str | None = None) -> int:
    from core.db import connect

    with OUT.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with connect(url) as conn:
        n = 0
        for r in rows:
            cur = conn.execute(
                "update rezoning set from_district = %s, to_district = %s, district_changes = %s::jsonb,"
                " district_confidence = %s, district_model = %s, district_source_url = %s,"
                " district_extracted_on = %s where record_number = %s",
                (r["from_district"] or None, r["to_district"] or None, r["changes"] or None,
                 r["confidence"] or None, r["model"], r["pdf_url"], r["extracted_on"], r["record_number"]),
            )  # fmt: skip
            n += cur.rowcount
    print(f"rezoning rows updated: {n:,}")
    return n


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["fetch", "estimate", "submit", "collect", "apply"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids")
    ap.add_argument("--max-dollars", type=float, default=float(os.environ.get("AI_RUN_MAX_DOLLARS", "5")))
    a = ap.parse_args(argv)
    ids = set(a.ids.split(",")) if a.ids else None
    if a.step == "fetch":
        fetch(a.limit, ids)
    elif a.step == "estimate":
        rows = selected(a.limit, ids)
        print(json.dumps(estimate(rows, measure=bool(api_key())), indent=2))
    elif a.step == "submit":
        submit(selected(a.limit, ids), a.max_dollars)
    elif a.step == "collect":
        collect()
    else:
        apply()


if __name__ == "__main__":
    main()
