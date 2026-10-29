"""Load Chicago zoning districts (dj47-wfun). Replaces the whole layer each run.

Run: python -m jobs.load_zoning
"""

import json

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, text, upsert

DATASET = "dj47-wfun"
COLUMNS = ["objectid", "zone_class", "zone_type", "pd_num", "edit_date", "the_geom", "source_pull_id"]
GEOM = {"geom": "st_multi(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)))"}


def to_row(r: dict, pull_id: int) -> tuple | None:
    if not r.get("the_geom") or not text(r.get("zone_class")):
        return None
    return (
        text(r.get("objectid")),
        text(r.get("zone_class")),
        integer(r.get("zone_type")),
        integer(r.get("pd_num")) or None,
        (text(r.get("edit_date")) or "")[:10] or None,
        json.dumps(r["the_geom"]),
        pull_id,
    )


def run(client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(CHICAGO)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, CHICAGO, DATASET)
        conn.commit()
        try:
            conn.execute("delete from zoning_district_area")
            for page in client.pages(DATASET, order="objectid", page_size=5_000):
                rows = (row for r in page if (row := to_row(r, pull_id)))
                total += upsert(conn, "zoning_district_area", COLUMNS, "objectid", rows, GEOM)
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


if __name__ == "__main__":
    print(f"zoning districts loaded: {run():,}")
