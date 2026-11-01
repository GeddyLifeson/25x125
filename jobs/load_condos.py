"""Load condo unit characteristics for Chicago townships (3r7i-mrz4), one tax year at a time.

Units of one building share the first 10 digits of their PINs; tieback_key_pin also links them.
Run: python -m jobs.load_condos [--year 2026] [--limit N]
"""

import argparse

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import boolean, integer, text, upsert
from jobs.load_sales import CHICAGO_TOWNSHIPS

DATASET = "3r7i-mrz4"
COLUMNS = [
    "row_id", "pin", "pin10", "tax_year", "unit_sqft", "building_sqft", "building_pins", "bedrooms", "year_built",
    "is_parking_space", "is_common_area", "building_is_mixed_use", "tieback_key_pin", "source_pull_id",
]  # fmt: skip


def where(year: int) -> str:
    towns = ", ".join(f"'{t}'" for t in CHICAGO_TOWNSHIPS)
    return f"(year = '{year}' or year = '{year}.0') and township_code in ({towns})"


def to_row(r: dict, pull_id: int) -> tuple:
    return (
        text(r.get("row_id")),
        text(r.get("pin")),
        text(r.get("pin10")),
        integer(r.get("year")),
        integer(r.get("char_unit_sf")),
        integer(r.get("char_building_sf")),
        integer(r.get("char_building_pins")),
        integer(r.get("char_bedrooms")),
        integer(r.get("char_yrblt")),
        boolean(r.get("is_parking_space")),
        boolean(r.get("is_common_area")),
        boolean(r.get("bldg_is_mixed_use")),
        text(r.get("tieback_key_pin")),
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
                total += upsert(conn, "condo_char", COLUMNS, "row_id", (to_row(r, pull_id) for r in page))
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
    print(f"condo units loaded: {run(a.year, a.limit):,}")
