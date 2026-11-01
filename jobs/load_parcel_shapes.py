"""Load Chicago parcel polygons and compute lot area, frontage and depth.

Source: Cook County GIS, Parcel 2025 layer (the data catalog's newest polygons, 77tz-riq7, are from 2021
and miss lots divided since then).
Run: python -m jobs.load_parcel_shapes [--limit N]
"""

import argparse
import json

from core.arcgis import ArcGIS
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert

LAYER = "https://gis.cookcountyil.gov/traditional/rest/services/parcelHistorical/MapServer/2025"
DATASET = "parcelHistorical/2025"
VINTAGE = 2025
WHERE = "MUNICIPALITY = 'CITY OF CHICAGO'"
COLUMNS = ["pin10", "vintage", "the_geom", "source_pull_id"]
# A PIN split across pages: within one pull, add the new part to the stored shape; across pulls, replace it.
MERGE_PARTS = {
    "geom": "case when parcel_shape.source_pull_id = excluded.source_pull_id"
    " then st_multi(st_collectionextract(st_union(parcel_shape.geom, excluded.geom), 3)) else excluded.geom end"
}
GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}


def polygons(geom: dict) -> list:
    if geom.get("type") == "Polygon":
        return [geom["coordinates"]]
    return geom.get("coordinates", [])


def merge(page: list[dict]) -> dict[str, dict]:
    """A PIN can have several polygon features; combine them into one MultiPolygon."""
    out: dict[str, dict] = {}
    for f in page:
        pin10 = text((f.get("properties") or {}).get("PIN10"))
        if not pin10 or not f.get("geometry"):
            continue
        g = out.setdefault(pin10, {"type": "MultiPolygon", "coordinates": []})
        g["coordinates"].extend(polygons(f["geometry"]))
    return out


def to_rows(page: list[dict], pull_id: int):
    for pin10, geom in merge(page).items():
        yield (pin10, VINTAGE, json.dumps(geom), pull_id)


def run(limit: int | None = None, client: ArcGIS | None = None, url: str | None = None) -> int:
    client = client or ArcGIS(LAYER)
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, client.host, DATASET, WHERE)
        conn.commit()
        try:
            for page in client.features(WHERE, out_fields="PIN10", page_size=min(limit or 2000, 2000)):
                total += upsert(
                    conn,
                    "parcel_shape",
                    COLUMNS,
                    "pin10",
                    to_rows(page, pull_id),
                    GEOM,
                    on_conflict=MERGE_PARTS,
                )
                conn.commit()
                if limit:
                    break
            conn.execute(
                "update parcel_shape s set lot_sqft = round(m.area_sqft), frontage_ft = round(m.short_ft, 1),"
                " depth_ft = round(m.long_ft, 1) from parcel_shape t, lateral lot_measures(t.geom) m"
                " where s.pin10 = t.pin10 and s.source_pull_id = %s",
                (pull_id,),
            )
            if not limit:  # a full pull replaces the layer, so retired PINs drop out
                conn.execute("delete from parcel_shape where source_pull_id <> %s", (pull_id,))
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
