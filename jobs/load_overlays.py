"""Load City of Chicago overlay layers: TIF districts, historic survey ratings and landmarks.

Each run replaces the layer. Run: python -m jobs.load_overlays
"""

import json

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert

COLUMNS = ["kind", "source_id", "name", "rating", "attrs", "the_geom", "source_pull_id"]
GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}

# kind -> (dataset, id field, name field, rating field)
LAYERS = {
    "tif": ("eejr-xtfb", "objectid", "name", None),
    "historic_survey": ("2u8t-236p", "objectid", "landmarkna", "color"),
    "landmark": ("uct4-hrvh", "id", "name", None),
}


def to_row(kind: str, r: dict, pull_id: int) -> tuple | None:
    _, id_field, name_field, rating_field = LAYERS[kind]
    if not r.get("the_geom") or not text(r.get(id_field)):
        return None
    attrs = {k: v for k, v in r.items() if k != "the_geom" and not k.startswith(":@")}
    return (
        kind,
        text(r[id_field]),
        text(r.get(name_field)),
        text(r.get(rating_field)) if rating_field else None,
        json.dumps(attrs),
        json.dumps(r["the_geom"]),
        pull_id,
    )


def run_layer(kind: str, client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(CHICAGO)
    dataset = LAYERS[kind][0]
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, CHICAGO, dataset)
        conn.commit()
        try:
            conn.execute("delete from overlay where kind = %s", (kind,))
            for page in client.pages(dataset, order=":id", page_size=5_000):
                rows = (row for r in page if (row := to_row(kind, r, pull_id)))
                total += upsert(conn, "overlay", COLUMNS, "kind, source_id", rows, GEOM)
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


def run(url: str | None = None) -> dict[str, int]:
    return {kind: run_layer(kind, url=url) for kind in LAYERS}


if __name__ == "__main__":
    for kind, n in run().items():
        print(f"{kind}: {n:,}")
