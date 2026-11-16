"""Load Chicago properties in the next Cook County Annual Tax Sale from the Treasurer's free lists.

The Treasurer posts one report per Chicago ward before each sale (delinquenttaxes.aspx). Each report is a PDF:
PIN, property address, volume, tax year, tax due, total due with interest, classification. This job reads the
sale date and ward links from the index page, downloads each ward's PDF, parses its rows with pypdf, and checks
the row count against the report's own "Total Delinquent PINs" line. Owner names and mailing addresses are
dropped. The paid cooktaxsale.com list is never used.

Rows for a sale are replaced on each run, so PINs that were paid drop off. Lists for past sales stay as history.
Run: python -m jobs.load_tax_sale
"""

import html
import http.client
import io
import re
import time
import urllib.request
from collections.abc import Callable
from datetime import date

from pypdf import PdfReader

from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import upsert
from jobs.load_foreclosure_auctions import USER_AGENT

INDEX = "https://www.cookcountytreasurer.com/delinquenttaxes.aspx"
HOST = "www.cookcountytreasurer.com"
WARD_LINK = re.compile(
    r"<a href='(https://reportingservices\.cookcountytreasurer\.com/[^']*)'[^>]*>Ward (\d+)</a>"
)
SALE_DATE = re.compile(r"scheduled for ([A-Z][a-z]+ \d{1,2}, \d{4})")
TOTAL = re.compile(r"Total Delinquent PINs: (\d+)")
THROUGH = re.compile(r"through \w+, ([A-Z][a-z]+ \d{1,2}, \d{4})")
ROW = re.compile(
    r"^(?P<pre>.*?)\s{2,}(?P<vol>\d{3})\s+(?P<pin>\d{2}-\d{2}-\d{3}-\d{3}-\d{4})\s+(?P<tt>\d{2})\s+(?P<ty>\d{4})"
    r"\s+\$(?P<tax>[\d,]+\.\d\d)\s+\$(?P<due>[\d,]+\.\d\d)\s+(?P<twp>[A-Z ]+?)\s{2,}(?P<muni>\S+)"
    r"\s+(?P<cls>[A-Za-z/ ]*?)\s{2,}(?P<ward>\d+)\s"
)
COLUMNS = [
    "sale_date", "pin", "pin10", "ward", "property_address", "volume", "tax_type", "tax_year", "total_tax_due",
    "total_due", "classification", "listed_through", "source_url", "source_pull_id",
]  # fmt: skip


class ParseError(Exception):
    pass


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]  # fmt: skip


def long_date(v: str) -> str:
    """'December 15, 2026' -> '2026-12-15'."""
    month, day, year = v.replace(",", "").split()
    return date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()


def fetch(url: str, opener: Callable = urllib.request.urlopen, tries: int = 4, backoff: float = 2.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(tries):
        try:
            with opener(req, timeout=120) as resp:
                return resp.read()
        except (OSError, http.client.HTTPException):
            if attempt == tries - 1:
                raise
            time.sleep(backoff * 2**attempt)
    raise AssertionError("unreachable")


def index(page: str) -> tuple[str, dict[int, str]]:
    """Sale date and {ward: report url} from the Treasurer's index page."""
    m = SALE_DATE.search(page)
    if not m:
        raise ParseError("sale date not found on the index page")
    wards: dict[int, str] = {}
    for url, ward in WARD_LINK.findall(page):
        wards.setdefault(int(ward), html.unescape(url))
    return long_date(m[1]), wards


def pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(p.extract_text(extraction_mode="layout") for p in reader.pages)


def rows_from_report(text: str) -> tuple[list[dict], str | None]:
    """Parsed rows and the 'through' date; raises if the count disagrees with the report's total."""
    total = TOTAL.search(text)
    through = THROUGH.search(text)
    out = []
    for line in text.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        parts = re.split(r"\s{2,}", m["pre"].strip())
        pin = m["pin"].replace("-", "")
        out.append({
            "pin": pin, "pin10": pin[:10], "ward": int(m["ward"]),
            "property_address": parts[1] if len(parts) > 1 else None, "volume": m["vol"], "tax_type": m["tt"],
            "tax_year": int(m["ty"]), "total_tax_due": float(m["tax"].replace(",", "")),
            "total_due": float(m["due"].replace(",", "")), "classification": m["cls"].strip() or None,
        })  # fmt: skip
    if total and int(total[1]) != len(out):
        raise ParseError(f"parsed {len(out)} rows, report says {total[1]}")
    return out, long_date(through[1]) if through else None


def run(url: str | None = None, opener: Callable = urllib.request.urlopen, pause: float = 1.0) -> int:
    sale_date, wards = index(fetch(INDEX, opener).decode("utf-8", "ignore"))
    if len(wards) != 50:
        raise ParseError(f"found {len(wards)} ward links, expected 50")
    with connect(url) as conn:
        pull_id = start_pull(conn, HOST, "delinquenttaxes.aspx", f"wards 1-50, sale {sale_date}")
        conn.commit()
        try:
            rows = []
            for ward, link in sorted(wards.items()):
                parsed, through = rows_from_report(pdf_text(fetch(link, opener)))
                for r in parsed:
                    r.update(
                        sale_date=sale_date, listed_through=through, source_url=link, source_pull_id=pull_id
                    )
                rows += parsed
                time.sleep(pause)
            conn.execute("delete from tax_sale_list where sale_date = %s", (sale_date,))
            n = upsert(
                conn, "tax_sale_list", COLUMNS, "sale_date, pin", ([r[c] for c in COLUMNS] for r in rows)
            )
            finish_pull(conn, pull_id, n)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
            conn.commit()
            raise
    return n


if __name__ == "__main__":
    print(f"tax sale rows: {run():,}")
