"""Load map layers the data portals don't carry: transit-served areas, bus corridors, ADU areas, special
districts (606, Pilsen), ARO areas, pedestrian streets and Enterprise Zones from the City of Chicago GIS
map services, the 2018 Opportunity Zone tracts from the U.S. DOT copy of the Treasury list, and the fire
limits from the Municipal Code text (data/rules/fire_limits.geojson).

Each run replaces each layer in `overlay`. Run: python -m jobs.load_city_layers [--kind adu_area]
"""

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from core.arcgis import ArcGIS
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import text, upsert
from jobs.load_overlays import COLUMNS, GEOM

CITY = "https://gisapps.chicago.gov/arcgis/rest/services/ExternalApps"
FIRE_LIMITS = Path(__file__).resolve().parent.parent / "data" / "rules" / "fire_limits.geojson"


@dataclass(frozen=True)
class Layer:
    url: str
    name_field: str | None = None
    rating_field: str | None = None
    where: str = "1=1"
    key: str = "OBJECTID"


LAYERS = {
    # Transit-served location (Chicago Zoning Ordinance 17-10-0102-B): the city's own buffers.
    "tsl_cta_station": Layer(f"{CITY}/Zoning/MapServer/13"),
    "tsl_metra_station": Layer(f"{CITY}/Zoning/MapServer/24"),
    "tsl_bus_corridor": Layer(f"{CITY}/Zoning/MapServer/14", "STREET_NAM", "SERVED_BY_"),
    # ADU zones: ADU_AREA codes 1 = annual limits, 2 = owner occupancy limits, 3 = administrative adjustment.
    "adu_area": Layer(f"{CITY}/Zoning/MapServer/17", "ZONE", "ADU_AREA"),
    "special_district": Layer(f"{CITY}/Zoning/MapServer/9", "SD_NAME"),
    "aro_area": Layer(f"{CITY}/Zoning/MapServer/20", None, "STATUS"),
    "pedestrian_street": Layer(f"{CITY}/Zoning/MapServer/4", "NAME"),
    "enterprise_zone": Layer(f"{CITY}/operational/MapServer/73", "NAME"),
    "opportunity_zone_2018": Layer(
        "https://geo.dot.gov/server/rest/services/hosted/OZ_Opportunity_Zones/FeatureServer/0",
        "geoid10",
        where="statefp = '17' and countyfp = '031'",
        key="objectid_12_13_14_15",
    ),
}


def to_row(kind: str, f: dict, pull_id: int, key: str, name_field: str | None, rating_field: str | None):
    props = f.get("properties") or {}
    sid = text(props.get(key)) or text(f.get("id"))
    if not f.get("geometry") or not sid:
        return None
    attrs = {k: v for k, v in props.items() if v is not None and not k.upper().startswith("SHAPE")}
    return (
        kind,
        sid,
        text(props.get(name_field)) if name_field else None,
        text(props.get(rating_field)) if rating_field else None,
        json.dumps(attrs),
        json.dumps(f["geometry"]),
        pull_id,
    )


def _replace(conn, kind: str, host: str, dataset: str, query: str, pages, layer: Layer) -> int:
    total = 0
    pull_id = start_pull(conn, host, dataset, query)
    conn.commit()
    try:
        conn.execute("delete from overlay where kind = %s", (kind,))
        for page in pages:
            rows = (
                row
                for f in page
                if (row := to_row(kind, f, pull_id, layer.key, layer.name_field, layer.rating_field))
            )
            total += upsert(conn, "overlay", COLUMNS, "kind, source_id", rows, GEOM)
        finish_pull(conn, pull_id, total)
        conn.commit()
    except Exception as e:
        conn.rollback()
        finish_pull(conn, pull_id, total, "failed", str(e)[:500])
        conn.commit()
        raise
    return total


def run_kind(kind: str, client: ArcGIS | None = None, url: str | None = None) -> int:
    with connect(url) as conn:
        if kind == "fire_limits":
            fc = json.loads(FIRE_LIMITS.read_text())
            layer = Layer("", "name", key="id")
            return _replace(conn, kind, "data/rules", "fire_limits.geojson", "", [fc["features"]], layer)
        layer = LAYERS[kind]
        client = client or ArcGIS(layer.url)
        dataset = layer.url.split("/services/", 1)[-1]
        pages = client.features(layer.where, out_fields="*", key=layer.key)
        return _replace(conn, kind, client.host, dataset, layer.where, pages, layer)


def run(url: str | None = None) -> dict[str, int]:
    return {kind: run_kind(kind, url=url) for kind in [*LAYERS, "fire_limits"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=[*LAYERS, "fire_limits"])
    a = ap.parse_args()
    for kind in [a.kind] if a.kind else [*LAYERS, "fire_limits"]:
        print(f"{kind}: {run_kind(kind):,}", flush=True)
