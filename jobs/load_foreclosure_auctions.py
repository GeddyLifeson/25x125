"""Load Cook County foreclosure auctions in Chicago into parcel_signal (kind 'foreclosure_auction').

Two sale officers publish their lists free on the web:
- The Judicial Sales Corporation (most Cook County sales): upcoming, completed and cancelled sales, about
  three months each way. https://www.tjsc.com/Sales/UpcomingSales
- Cook County Sheriff: past sales with final bids (paged, back to 2019) and upcoming sales.
  https://foreclosure.ccsheriff.org/previoussale

The lists only reach a few months back, so rows are kept between runs (one row per sale file, updated
with its latest date and result); history builds up from the first run. build_parcel_site ties each
sale to a lot by address. Run: python -m jobs.load_foreclosure_auctions [--sheriff-pages 50]
"""

import argparse
import json
import re
import urllib.request
from collections.abc import Callable, Iterator
from datetime import datetime
from html.parser import HTMLParser

from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import upsert
from jobs.load_signals import COLUMNS, GEOM

KIND = "foreclosure_auction"
TJSC = {
    "upcoming": "https://www.tjsc.com/Sales/UpcomingSales",
    "completed": "https://www.tjsc.com/Sales/CompletedSales",
    "cancelled": "https://www.tjsc.com/Sales/CancelledSales",
}
SHERIFF_PAST = "https://foreclosure.ccsheriff.org/previoussale"
USER_AGENT = "25x125-data-loader/1.0 (+https://github.com/GeddyLifeson/25x125)"

# Spell addresses the way the Assessor's address file does, so build_parcel_site can match them.
WORDS = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "AVENUE": "AVE", "STREET": "ST", "BOULEVARD": "BLVD",
    "ROAD": "RD", "DRIVE": "DR", "PLACE": "PL", "COURT": "CT", "PARKWAY": "PKWY", "TERRACE": "TER",
    "LANE": "LN", "AV": "AVE", "STR": "ST",
}  # fmt: skip
UNIT = re.compile(r"\s+(#|UNIT|APT|STE|SUITE|FL|FLOOR|GARAGE|PARKING|P-?\d)\b.*$")


class Table(HTMLParser):
    """Rows of every table on a page, cell text only."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join(self.cell.split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data


def records(html: str) -> list[dict]:
    """Table rows as dicts keyed by the header row, headers lowercased with spaces removed."""
    p = Table()
    p.feed(html)
    out, header = [], None
    for r in p.rows:
        if r and r[0].replace(" ", "").lower() in ("saledate", "casenumber"):
            header = [h.replace(" ", "").lower() for h in r]
        elif header and len(r) == len(header):
            out.append(dict(zip(header, r, strict=True)))
    return out


def clean_address(v: str) -> str | None:
    a = re.sub(r"[.,]", " ", (v or "").upper())
    a = UNIT.sub("", a)
    words = [WORDS.get(w, w) for w in a.split()]
    return " ".join(words) or None


def money(v: str) -> float | None:
    d = re.sub(r"[^0-9.]", "", v or "")
    return float(d) if d and float(d) > 0 else None


def day(v: str) -> str | None:
    try:
        return datetime.strptime(v.strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def tjsc_row(r: dict, status: str, pull_id: int) -> tuple | None:
    if (
        r.get("county", "").upper() != "COOK"
        or r.get("city", "").upper() != "CHICAGO"
        or not r.get("filenumber")
    ):
        return None
    attrs = {"officer": "tjsc", "firm": r.get("firmname"), "opening_bid": money(r.get("openingbid")),
             "sale_amount": money(r.get("saleamount")), "sold_to": r.get("soldto") or None,
             "continuance": r.get("continuance") or None, "zip": r.get("zipcode")}  # fmt: skip
    return (
        KIND, f"tjsc:{r['filenumber']}", day(r.get("saledate", "")), status, r.get("casenumber"),
        clean_address(r.get("address", "")), None, json.dumps({k: v for k, v in attrs.items() if v}),
        None, None, pull_id,
    )  # fmt: skip


def sheriff_row(r: dict, pull_id: int) -> tuple | None:
    if r.get("propertycity", "").upper() != "CHICAGO" or not r.get("sheriffnumber"):
        return None
    status = {"completed": "completed", "cancelled": "cancelled"}.get(
        r.get("casestatus", "").lower(), "upcoming"
    )
    attrs = {"officer": "sheriff", "firm": r.get("firmname"), "opening_bid": money(r.get("openingbid")),
             "sale_amount": money(r.get("finalbid")), "sold_to": r.get("soldto") or None,
             "zip": r.get("propertyzipcode")}  # fmt: skip
    return (
        KIND, f"sheriff:{r['sheriffnumber']}", day(r.get("saledate", "")), status, r.get("casenumber"),
        clean_address(r.get("propertyaddress", "")), None, json.dumps({k: v for k, v in attrs.items() if v}),
        None, None, pull_id,
    )  # fmt: skip


def get(opener: Callable, url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener(req, timeout=120) as resp:
        return resp.read().decode("utf-8", errors="replace")


def all_rows(opener: Callable, pull_id: int, sheriff_pages: int) -> Iterator[tuple]:
    for status, url in TJSC.items():
        for r in records(get(opener, url)):
            if row := tjsc_row(r, status, pull_id):
                yield row
    for page in range(1, sheriff_pages + 1):
        recs = records(get(opener, f"{SHERIFF_PAST}?page={page}"))
        if not recs:
            break
        for r in recs:
            if row := sheriff_row(r, pull_id):
                yield row


def run(opener: Callable = urllib.request.urlopen, url: str | None = None, sheriff_pages: int = 3) -> int:
    """Nightly: the three TJSC lists and the newest Sheriff pages. Use more pages once to backfill."""
    with connect(url) as conn:
        pull_id = start_pull(conn, "www.tjsc.com", "foreclosure auctions", f"sheriff pages {sheriff_pages}")
        conn.commit()
        try:
            rows = {r[1]: r for r in all_rows(opener, pull_id, sheriff_pages)}  # a file can show on two lists
            n = upsert(conn, "parcel_signal", COLUMNS, "kind, source_id", rows.values(), GEOM)
            finish_pull(conn, pull_id, n)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
            conn.commit()
            raise
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheriff-pages", type=int, default=3)
    print(f"auction rows: {run(sheriff_pages=ap.parse_args().sheriff_pages):,}")
