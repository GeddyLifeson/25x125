"""Load a region's zoning districts from the free ArcGIS layer named in its region.json (zoning_layer).

zoning_layer: url (a layer, or a list of layers under `urls`), zone_field, optional `where`, `key` and
`subdivide` (true cuts very large polygons, such as a city limit, into small parts).
Replaces the whole layer each run. Run: python -m jobs.load_zoning_layer
"""

import json

from core import region
from core.arcgis import ArcGIS
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert

COLUMNS = ["objectid", "zone_class", "the_geom", "source_pull_id"]
GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}


def to_rows(page: list[dict], field: str, key: str, prefix: str, pull_id: int):
    for f in page:
        props = f.get("properties") or {}
        zone = text(props.get(field))
        g = f.get("geometry")
        if not zone or not g or g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        yield (f"{prefix}{props.get(key)}", zone, json.dumps(g), pull_id)


def run(url: str | None = None, client_for=ArcGIS, limit: int | None = None) -> int:
    layer = region.current()["zoning_layer"]
    urls = layer.get("urls") or [layer["url"]]
    field, key, where = layer["zone_field"], layer.get("key", "OBJECTID"), layer.get("where", "1=1")
    total = 0
    with connect(url) as conn:
        conn.execute("delete from zoning_district_area")
        for i, layer_url in enumerate(urls):
            client = client_for(layer_url)
            pull_id = start_pull(conn, client.host, layer_url.split("/rest/services/")[-1], where)
            try:
                for page in client.features(
                    where, out_fields=field, key=key, page_size=layer.get("page_size", 1000)
                ):
                    total += upsert(conn, "zoning_district_area", COLUMNS, "objectid",
                                    to_rows(page, field, key, f"{i}-" if len(urls) > 1 else "", pull_id), GEOM)  # fmt: skip
                    if limit and total >= limit:
                        break
                if layer.get("subdivide"):
                    # A few very large polygons (a city limit) make every lot test slow; cut them into parts.
                    conn.execute(
                        "create temp table zparts on commit drop as select objectid, zone_class,"
                        " st_subdivide(geom, 256) as g from zoning_district_area where source_pull_id = %s",
                        (pull_id,),
                    )
                    conn.execute("delete from zoning_district_area where source_pull_id = %s", (pull_id,))
                    conn.execute(
                        "insert into zoning_district_area (objectid, zone_class, geom, source_pull_id)"
                        " select objectid || '.' || row_number() over (), zone_class,"
                        " st_multi(st_collectionextract(g, 3)), %s from zparts where st_dimension(g) = 2",
                        (pull_id,),
                    )
                    conn.execute("drop table zparts")
                finish_pull(conn, pull_id, total)
            except Exception as e:
                conn.rollback()
                finish_pull(conn, pull_id, total, "failed", str(e)[:500])
                conn.commit()
                raise
    return total


if __name__ == "__main__":
    print(f"zoning districts loaded: {run():,}")
