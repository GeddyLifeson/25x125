"""Map overlays for a region outside Chicago: flood zones, historic districts, ADU areas and the rest.

Each entry of region.json `overlay_layers` with a `url` loads into `overlay` under its `kind`, named by its
`name_field`. Optional: `where` (a filter on the layer) and `clip` (false to skip the region bounding box filter,
which keeps county-wide flood layers to the city). `jobs/build_region.py` then lists each lot's overlays in
parcel_site.overlays, and the engine turns the ones that limit building into flags.
"""

import json

from core import region
from core.arcgis import ArcGIS, ArcGISError
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert

COLUMNS = ["kind", "source_id", "name", "rating", "attrs", "the_geom", "source_pull_id"]
GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}


def to_rows(page: list[dict], layer: dict, key: str, prefix: str, pull_id: int):
    field = layer.get("name_field")
    for f in page:
        props = f.get("properties") or {}
        g = f.get("geometry")
        if not g or g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        name = text(props.get(field)) if field else None
        yield (layer["kind"], f"{prefix}{props.get(key)}", name or layer.get("label") or layer["kind"], None,
               json.dumps({"layer": layer["url"]}), json.dumps(g), pull_id)  # fmt: skip


def region_bbox(conn) -> str | None:
    row = conn.execute(
        "select st_xmin(e), st_ymin(e), st_xmax(e), st_ymax(e) from (select st_extent(geom) e from parcel) x"
    ).fetchone()
    return ",".join(f"{v:.5f}" for v in row) if row and row[0] is not None else None


def run(url: str | None = None, client_for=ArcGIS, only: str | None = None) -> dict:
    layers = [x for x in region.current().get("overlay_layers") or [] if x.get("url")]
    out = {}
    with connect(url) as conn:
        bbox = region_bbox(conn)
        kinds = {x["kind"] for x in layers if not only or x["kind"] == only}
        for kind in kinds:
            conn.execute("delete from overlay where kind = %s", (kind,))
        for i, layer in enumerate(layers):
            if only and layer["kind"] != only:
                continue
            client = client_for(layer["url"])
            where = layer.get("where", "1=1")
            extra = (
                {"geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": 4326,
                 "spatialRel": "esriSpatialRelIntersects"}
                if bbox and layer.get("clip", True) else None
            )  # fmt: skip
            pull_id = start_pull(conn, client.host, layer["url"].split("/rest/services/")[-1], where)
            n = 0
            try:
                key = layer.get("key") or client.object_id_field()
                for page in client.features(where, out_fields="*", key=key, page_size=layer.get("page_size", 1000),
                                            extra=extra):  # fmt: skip
                    n += upsert(
                        conn,
                        "overlay",
                        COLUMNS,
                        "kind, source_id",
                        to_rows(page, layer, key, f"{i}-", pull_id),
                        GEOM,
                    )
                finish_pull(conn, pull_id, n)
            except (ArcGISError, OSError) as e:
                finish_pull(conn, pull_id, n, status="failed", note=str(e)[:500])
                print(f"overlay {layer['kind']} failed: {e}")
            conn.commit()
            out[f"{layer['kind']} ({i})"] = n
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kind", help="load only this kind")
    for k, v in run(only=ap.parse_args().kind).items():
        print(f"{k:<40} {v:>8,}")
