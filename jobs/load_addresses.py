"""Load Chicago property addresses and mailing names for one tax year (3723-97qp).

Run: python -m jobs.load_addresses [--year 2026] [--limit N]
"""

import argparse

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, text, upsert

DATASET = "3723-97qp"
COLUMNS = ["pin", "tax_year", "address", "zip", "mail_name", "mail_address", "owner_name", "owner_address",
           "source_pull_id"]  # fmt: skip


def where(year: int) -> str:
    return f"year = '{year}' and prop_address_city_name = 'CHICAGO'"


def to_row(r: dict, pull_id: int) -> tuple:
    return (
        text(r.get("pin")),
        integer(r.get("year")),
        text(r.get("prop_address_full")),
        text(r.get("prop_address_zipcode_1")),
        text(r.get("mail_address_name")),
        text(r.get("mail_address_full")),
        text(r.get("owner_address_name")),
        text(r.get("owner_address_full")),
        pull_id,
    )


def run(year: int, limit: int | None = None, client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(COOK)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, COOK, DATASET, where(year))
        conn.commit()
        try:
            for page in client.pages(DATASET, order="row_id", where=where(year), page_size=limit or 50_000):
                total += upsert(conn, "parcel_address", COLUMNS, "pin", (to_row(r, pull_id) for r in page))
                conn.commit()
                if limit:
                    break
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    print(f"addresses loaded: {run(a.year, a.limit):,}")
