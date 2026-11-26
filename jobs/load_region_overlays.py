"""Map overlays for a region outside Chicago: flood zones, historic districts, ADU areas and the rest.

Each entry of region.json `overlay_layers` with a `url` loads into `overlay` under its `kind`, named by its
`name_field`. Optional: `where` (a filter on the layer) and `clip` (false to skip the region bounding box filter,
which keeps county-wide flood layers to the city). `jobs/build_region.py` then lists each lot's overlays in
parcel_site.overlays, and the engine turns the ones that limit building into flags.
"""

import json
import math

from core import region
from core.arcgis import ArcGIS, ArcGISError
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert

POINT_HALF_DEG = 0.00003  # about 3 m each side of the point
FT_PER_DEG_LAT = 364_000  # about 111 km
COLUMNS = ["kind", "source_id", "name", "rating", "attrs", "the_geom", "source_pull_id"]
LINE_BUFFER_M = 15  # street lines: reaches the front of the lots on both sides of a 50 to 60 ft right of way
_G = "st_setsrid(st_geomfromgeojson(the_geom), 4326)"
GEOM = {
    "geom": f"st_multi(st_collectionextract(st_makevalid(case when geometrytype({_G}) like '%LINESTRING' "
    f"then st_buffer({_G}::geography, {LINE_BUFFER_M})::geometry else {_G} end), 3))"
}


def circle(x: float, y: float, radius_ft: float, sides: int = 48) -> dict:
    """A GeoJSON polygon approximating a circle of `radius_ft` around lon/lat (x, y)."""
    dy = radius_ft / FT_PER_DEG_LAT
    dx = dy / math.cos(math.radians(y))
    ring = [[x + dx * math.cos(2 * math.pi * i / sides), y + dy * math.sin(2 * math.pi * i / sides)]
            for i in range(sides)]  # fmt: skip
    return {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}


def to_rows(page: list[dict], layer: dict, key: str, prefix: str, pull_id: int):
    field = layer.get("name_field")
    for f in page:
        props = f.get("properties") or {}
        g = f.get("geometry")
        attrs = {"layer": layer["url"]}
        if g and g.get("type") == "Point" and layer.get("radius_ft"):
            # A stop with a reach (Atlanta: no parking within 2,640 ft of a MARTA rail station): a circle of that
            # radius, matched to the lots whose point it contains, like any polygon.
            x, y = g["coordinates"][:2]
            g = circle(x, y, layer["radius_ft"])
            attrs["radius_ft"] = layer["radius_ft"]
        elif g and g.get("type") == "Point":
            # Point layers (Austin's 689 city landmarks): store a 6 m square; build_region matches it to the lot
            # whose outline it touches.
            x, y = g["coordinates"][:2]
            d = POINT_HALF_DEG
            g = {"type": "Polygon", "coordinates": [[[x - d, y - d], [x + d, y - d], [x + d, y + d], [x - d, y + d],
                                                      [x - d, y - d]]]}  # fmt: skip
            attrs["point"] = True
        if g and g.get("type") in ("LineString", "MultiLineString"):
            # Street layers (Houston's restricted driveway access streets): GEOM buffers the line, and
            # build_region matches it to the lots whose outlines it touches.
            attrs["line"] = True
        elif not g or g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        if isinstance(field, list):  # several fields: join the ones that hold a value ("NA" counts as none)
            name = (
                ", ".join(v for v in (text(props.get(f)) for f in field) if v and v.upper() != "NA") or None
            )
        else:
            name = text(props.get(field)) if field else None
        yield (layer["kind"], f"{prefix}{props.get(key)}", name or layer.get("label") or layer["kind"], None,
               json.dumps(attrs), json.dumps(g), pull_id)  # fmt: skip


def region_bbox(conn) -> str | None:
    row = conn.execute(
        "select st_xmin(e), st_ymin(e), st_xmax(e), st_ymax(e) from (select st_extent(geom) e from parcel) x"
    ).fetchone()
    return ",".join(f"{v:.5f}" for v in row) if row and row[0] is not None else None


def run(url: str | None = None, client_for=ArcGIS, only: str | None = None) -> dict:
    layers = [x for x in region.current().get("overlay_layers") or [] if x.get("url") and not x.get("skip")]
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
