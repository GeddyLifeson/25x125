"""Load Chicago parcel polygons (77tz-riq7, 2021 vintage) and compute lot area, frontage and depth.

Run: python -m jobs.load_parcel_shapes [--limit N]
"""

import argparse
import json

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert

DATASET = "77tz-riq7"
VINTAGE = 2021
WHERE = "municipality = 'Chicago'"
COLUMNS = ["pin10", "vintage", "the_geom", "source_pull_id"]
GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}


def polygons(geom: dict) -> list:
    if geom.get("type") == "Polygon":
        return [geom["coordinates"]]
    return geom.get("coordinates", [])


def merge(page: list[dict]) -> dict[str, dict]:
    """A PIN can have several polygon rows; combine them into one MultiPolygon."""
    out: dict[str, dict] = {}
    for r in page:
        pin10 = text(r.get("pin10"))
        if not pin10 or not r.get("the_geom"):
            continue
        g = out.setdefault(pin10, {"type": "MultiPolygon", "coordinates": []})
        g["coordinates"].extend(polygons(r["the_geom"]))
    return out


def to_rows(page: list[dict], pull_id: int):
    for pin10, geom in merge(page).items():
        yield (pin10, VINTAGE, json.dumps(geom), pull_id)


def run(limit: int | None = None, client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(COOK)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, COOK, DATASET, WHERE)
        conn.commit()
        try:
            for page in client.pages(
                DATASET, order="pin10", select="pin10,the_geom", where=WHERE, page_size=limit or 50_000
            ):
                total += upsert(conn, "parcel_shape", COLUMNS, "pin10", to_rows(page, pull_id), GEOM)
                conn.commit()
                if limit:
                    break
            conn.execute(
                "update parcel_shape s set lot_sqft = round(m.area_sqft), frontage_ft = round(m.short_ft, 1),"
                " depth_ft = round(m.long_ft, 1) from parcel_shape t, lateral lot_measures(t.geom) m"
                " where s.pin10 = t.pin10 and s.source_pull_id = %s",
                (pull_id,),
            )
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    print(f"parcel shapes loaded: {run(ap.parse_args().limit):,}")
