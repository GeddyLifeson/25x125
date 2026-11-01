"""Load zoning map amendments from the Chicago City Clerk's eLMS public API (free, no key, 2010 on).

Each matter's title gives the map number, address and application number, e.g.
"Zoning Reclassification Map No. 93-B at 1828 W Race Ave - App No. 23178T1". The ordinance PDF holds the
old and new districts but is a scan; reading it is a separate step. Rows also go to parcel_signal (kind
'rezoning') so build_parcel_site ties them to lots by address.
https://api.chicityclerkelms.chicago.gov/search?search=Zoning%20Reclassification
Each run replaces the table. Run: python -m jobs.load_rezonings
"""

import json
import re
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator

from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import upsert
from jobs.load_foreclosure_auctions import USER_AGENT, clean_address
from jobs.load_signals import COLUMNS as SIGNAL_COLUMNS
from jobs.load_signals import GEOM

HOST = "api.chicityclerkelms.chicago.gov"
SEARCH = "https://api.chicityclerkelms.chicago.gov/search?search={q}&size=100&skip={skip}"
QUERY = "Zoning Reclassification"
COLUMNS = [
    "record_number", "matter_id", "title", "map_no", "app_no", "type1", "alderman_filed", "address", "addresses",
    "intro_date", "final_date", "status", "sub_status", "source_pull_id",
]  # fmt: skip
TITLE = re.compile(r"^\s*zon+ing\s+reclassification", re.IGNORECASE)
MAP = re.compile(r"Map\s+Nos?\.?\s*(\d+-?\s?[A-Z0-9](?:\s*(?:,|and)\s*\d+-[A-Z0-9])*)", re.IGNORECASE)
APP = re.compile(r"App(?:lication)?\s*No\.?\s*((?:A-)?\d{4,5}(?:T1)?)\b|\b(A-\d{4,5})\s*$", re.IGNORECASE)
AT = re.compile(r"\bat\s+(\d.*)$", re.IGNORECASE)
CUT = re.compile(r"\s+-\s+|\s+App(?:lication)?\s*No|\s+a\.?k\.?a\.?\s|\s+A-\d", re.IGNORECASE)
NUMBER_RANGE = re.compile(r"^(\d+)\s*-\s*\d+\b")


def parse_title(title: str) -> dict:
    t = " ".join(title.split())
    m, a = MAP.search(t), APP.search(t)
    at = AT.search(t)
    places = CUT.split(at.group(1))[0] if at else ""
    addresses = [p.strip() for p in re.split(r",\s*|\s+and\s+|/", places) if re.match(r"\d", p.strip())]
    first = NUMBER_RANGE.sub(r"\1", addresses[0]) if addresses else None
    app = (a.group(1) or a.group(2)).upper() if a else None
    maps = re.findall(r"\d+-\s?[A-Z0-9]", m.group(1), re.IGNORECASE) if m else []
    return {
        "map_no": ", ".join(x.replace(" ", "").upper() for x in maps) or None,
        "app_no": app,
        "type1": bool(app and app.endswith("T1")),
        "alderman_filed": bool(app and app.startswith("A-")),
        "address": clean_address(first) if first else None,
        "addresses": "; ".join(addresses) or None,
    }


def day(v) -> str | None:
    return v[:10] if v else None


def matters(opener: Callable) -> Iterator[dict]:
    skip = 0
    while True:
        url = SEARCH.format(q=urllib.parse.quote(QUERY), skip=skip)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with opener(req, timeout=120) as resp:
            data = json.load(resp)
        rows = data.get("data") or []
        yield from rows
        skip += len(rows)
        if not rows or skip >= data.get("meta", {}).get("count", 0):
            break


def run(opener: Callable = urllib.request.urlopen, url: str | None = None) -> int:
    with connect(url) as conn:
        pull_id = start_pull(conn, HOST, "search", QUERY)
        conn.commit()
        try:
            rows, signals = {}, {}
            for m in matters(opener):
                if not TITLE.match(m.get("title") or "") or not m.get("recordNumber"):
                    continue
                p = parse_title(m["title"])
                rec = m["recordNumber"]
                rows[rec] = (
                    rec, m["matterId"], " ".join(m["title"].split()), p["map_no"], p["app_no"], p["type1"],
                    p["alderman_filed"], p["address"], p["addresses"], day(m.get("introductionDate")),
                    day(m.get("finalActionDate")), m.get("status"), m.get("subStatus"), pull_id,
                )  # fmt: skip
                attrs = {
                    "map_no": p["map_no"],
                    "app_no": p["app_no"],
                    "final_date": day(m.get("finalActionDate")),
                }
                signals[rec] = (
                    "rezoning", rec, day(m.get("introductionDate")), m.get("status"), " ".join(m["title"].split()),
                    p["address"], None, json.dumps({k: v for k, v in attrs.items() if v}), None, None, pull_id,
                )  # fmt: skip
            conn.execute("delete from rezoning")
            conn.execute("delete from parcel_signal where kind = 'rezoning'")
            n = upsert(conn, "rezoning", COLUMNS, "record_number", rows.values())
            upsert(conn, "parcel_signal", SIGNAL_COLUMNS, "kind, source_id", signals.values(), GEOM)
            finish_pull(conn, pull_id, n)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
            conn.commit()
            raise
    return n


if __name__ == "__main__":
    print(f"rezonings: {run():,}")
