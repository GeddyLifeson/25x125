"""Load boundaries: community areas, wards, 2020 census tracts (City of Chicago) and Assessor
neighborhoods (Cook County, Chicago townships only).

Each run replaces each kind. Run: python -m jobs.load_boundaries
"""

import json

from core.db import connect
from core.socrata import CHICAGO, COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert
from jobs.load_sales import CHICAGO_TOWNSHIPS

COLUMNS = ["kind", "code", "name", "the_geom", "source_pull_id"]
GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}

# kind -> (host, dataset, geometry field, code field, name field, where)
KINDS = {
    "community_area": (CHICAGO, "igwz-8jzy", "the_geom", "area_numbe", "community", None),
    "ward": (CHICAGO, "p293-wvbd", "the_geom", "ward", None, None),
    "tract_2020": (CHICAGO, "7qjk-677h", "the_geom", "tract_full", "community_area", None),
    "assessor_nbhd": (
        COOK,
        "pcdw-pxtg",
        "multipolygon",
        "town_nbhd",
        "township_name",
        "township_code in (" + ", ".join(f"'{t}'" for t in CHICAGO_TOWNSHIPS) + ")",
    ),
}


def to_row(kind: str, r: dict, pull_id: int) -> tuple | None:
    _, _, geom_field, code_field, name_field, _ = KINDS[kind]
    code = text(r.get(code_field))
    if not code or not r.get(geom_field):
        return None
    return (kind, code, text(r.get(name_field)) if name_field else None, json.dumps(r[geom_field]), pull_id)


def run_kind(kind: str, client: Socrata | None = None, url: str | None = None) -> int:
    host, dataset, *_, where = KINDS[kind]
    client = client or Socrata(host)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, host, dataset, where or "")
        conn.commit()
        try:
            conn.execute("delete from boundary where kind = %s", (kind,))
            for page in client.pages(dataset, order=":id", where=where, page_size=1_000):
                rows = (row for r in page if (row := to_row(kind, r, pull_id)))
                total += upsert(conn, "boundary", COLUMNS, "kind, code", rows, GEOM)
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


def run(url: str | None = None) -> dict[str, int]:
    return {kind: run_kind(kind, url=url) for kind in KINDS}


if __name__ == "__main__":
    for kind, n in run().items():
        print(f"{kind}: {n:,}")
