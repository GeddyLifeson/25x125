"""Load Chicago street centerline segments with their address ranges (pr57-gg9e).

Each run replaces the table. Run: python -m jobs.load_streets
"""

import json

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, text, upsert

DATASET = "pr57-gg9e"
COLUMNS = ["trans_id", "pre_dir", "street_name", "street_type", "l_from", "l_to", "l_parity", "r_from", "r_to",
           "r_parity", "f_cross", "t_cross", "class", "the_geom", "source_pull_id"]  # fmt: skip
GEOM = {"geom": "st_multi(st_setsrid(st_geomfromgeojson(the_geom), 4326))"}


def to_row(r: dict, pull_id: int) -> tuple | None:
    if not text(r.get("trans_id")) or not r.get("the_geom"):
        return None
    return (
        text(r["trans_id"]), text(r.get("pre_dir")), text(r.get("street_nam")), text(r.get("street_typ")),
        integer(r.get("l_f_add")), integer(r.get("l_t_add")), text(r.get("l_parity")),
        integer(r.get("r_f_add")), integer(r.get("r_t_add")), text(r.get("r_parity")),
        text(r.get("f_cross")), text(r.get("t_cross")), text(r.get("class")),
        json.dumps(r["the_geom"]), pull_id,
    )  # fmt: skip


def run(client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(CHICAGO)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, CHICAGO, DATASET)
        conn.commit()
        try:
            conn.execute("truncate street_segment")
            for page in client.pages(DATASET, order=":id", page_size=20_000):
                rows = (row for r in page if (row := to_row(r, pull_id)))
                total += upsert(conn, "street_segment", COLUMNS, "trans_id", rows, GEOM)
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


if __name__ == "__main__":
    print(f"street segments: {run():,}")
