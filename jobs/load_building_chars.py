"""Load Assessor residential characteristics (x54s-btds) for Chicago townships, one tax year at a time.

Assessor year values after 2023 are stored as '2026.0'; both forms are accepted.
Run: python -m jobs.load_building_chars [--year 2026] [--limit N]
"""

import argparse

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, text, upsert
from jobs.load_sales import CHICAGO_TOWNSHIPS

DATASET = "x54s-btds"
COLUMNS = [
    "row_id", "pin", "tax_year", "card", "class", "apartments", "building_sqft", "land_sqft", "year_built",
    "rooms", "beds", "full_baths", "half_baths", "basement", "ext_wall", "source_pull_id",
]  # fmt: skip
APTS = {"none": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def apartments(v) -> int | None:
    v = text(v)
    if v is None:
        return None
    return APTS.get(v.lower(), integer(v) if v.replace(".", "").isdigit() else None)


def where(year: int) -> str:
    towns = ", ".join(f"'{t}'" for t in CHICAGO_TOWNSHIPS)
    return f"(year = '{year}' or year = '{year}.0') and township_code in ({towns})"


def to_row(r: dict, pull_id: int) -> tuple:
    return (
        text(r.get("row_id")),
        text(r.get("pin")),
        integer(r.get("year")),
        integer(r.get("card")),
        text(r.get("class")),
        apartments(r.get("char_apts")),
        integer(r.get("char_bldg_sf")),
        integer(r.get("char_land_sf")),
        integer(r.get("char_yrblt")),
        integer(r.get("char_rooms")),
        integer(r.get("char_beds")),
        integer(r.get("char_fbath")),
        integer(r.get("char_hbath")),
        text(r.get("char_bsmt")),
        text(r.get("char_ext_wall")),
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
                total += upsert(conn, "building_char", COLUMNS, "row_id", (to_row(r, pull_id) for r in page))
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
    print(f"building characteristics loaded: {run(a.year, a.limit):,}")
