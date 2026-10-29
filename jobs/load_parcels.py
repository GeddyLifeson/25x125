"""Load the Chicago parcel universe for one tax year from the Assessor (pabr-t5kh).

Run: python -m jobs.load_parcels [--year 2026] [--limit N]
"""

import argparse

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import boolean, integer, text, upsert

DATASET = "pabr-t5kh"
FIELDS = [
    "pin", "pin10", "year", "class", "township_code", "nbhd_code", "ward_num",
    "chicago_community_area_num", "chicago_community_area_name", "census_tract_geoid", "zip_code",
    "tax_tif_district_num", "tax_tif_district_name", "tax_special_service_area_name",
    "env_flood_fema_sfha", "lon", "lat",
]  # fmt: skip
COLUMNS = [
    "pin", "pin10", "tax_year", "municipality_id", "class", "township_code", "nbhd_code", "ward",
    "community_area_num", "community_area_name", "tract_geoid", "zip", "tif_district_num",
    "tif_district_name", "ssa_name", "flood_fema_sfha", "lon", "lat", "source_pull_id",
]  # fmt: skip
GEOM = {
    "geom": "case when lon is not null and lat is not null"
    " then st_setsrid(st_makepoint(lon::float8, lat::float8), 4326) end"
}


def where(year: int) -> str:
    return f"year = '{year}' and cook_municipality_name = 'CITY OF CHICAGO'"


def to_row(r: dict, pull_id: int) -> tuple:
    return (
        text(r.get("pin")),
        text(r.get("pin10")),
        integer(r.get("year")),
        "chicago",
        text(r.get("class")),
        text(r.get("township_code")),
        text(r.get("nbhd_code")),
        integer(r.get("ward_num")),
        integer(r.get("chicago_community_area_num")),
        text(r.get("chicago_community_area_name")),
        text(r.get("census_tract_geoid")),
        text(r.get("zip_code")),
        text(r.get("tax_tif_district_num")),
        text(r.get("tax_tif_district_name")),
        text(r.get("tax_special_service_area_name")),
        boolean(r.get("env_flood_fema_sfha")),
        text(r.get("lon")),
        text(r.get("lat")),
        pull_id,
    )


def run(year: int, limit: int | None = None, client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(COOK)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, COOK, DATASET, where(year))
        conn.commit()
        try:
            for page in client.pages(
                DATASET, order="pin", select=",".join(FIELDS), where=where(year), page_size=limit or 50_000
            ):
                total += upsert(conn, "parcel", COLUMNS, "pin", (to_row(r, pull_id) for r in page), GEOM)
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
    print(f"parcels loaded: {run(a.year, a.limit):,}")
