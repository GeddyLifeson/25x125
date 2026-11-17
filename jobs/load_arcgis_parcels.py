"""Load a region's parcels from a free county or city ArcGIS parcel layer that carries appraisal values.

Used where the appraisal district publishes its roll through a map service: Houston (City of Houston copy of
the Harris Central Appraisal District roll), San Antonio (Bexar County), Atlanta (Fulton County). The layer and
its field names come from `parcel_layer` in region.json:

  url, where, key (default OBJECTID), page_size, tax_year,
  fields: id, address, zip, use_code, market_value, land_value, year_built, living_sqft, units, land_sqft,
          land_acres, nbhd, owner (each a field name in the layer; leave out what the layer lacks)
  use_groups: {use code or its prefix: vacant | single | multi | condo | other}
  units_by_use: {use code: units}  (Texas state class B2 is a two-family building, and so on)
  use_from_units: true where the use code does not separate houses from lots (Atlanta): a residential class
    with 0 living units is vacant, 1 is a house, 2 or more is multi-unit

Each parcel's polygon gives the lot shape and measures. Texas rolls have no sale prices (Government Code
552.148), so `sale` stays empty and comps come from appraised values (jobs/build_region.py).
Run: python -m jobs.load_arcgis_parcels [--limit N]
"""

import argparse
import json
import re

from core import region
from core.arcgis import ArcGIS
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import integer, num, text, upsert

GEOM = {
    "geom": "st_multi(st_collectionextract(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)), 3))"
}
MERGE = {
    "geom": "case when parcel_shape.source_pull_id = excluded.source_pull_id"
    " then st_multi(st_collectionextract(st_union(parcel_shape.geom, excluded.geom), 3)) else excluded.geom end"
}


def group_for(code: str | None, groups: dict) -> str:
    """Longest matching prefix wins: {'A': 'single', 'A3': 'condo'} sends A3 to condo."""
    code = (code or "").strip().upper()
    for n in range(len(code), 0, -1):
        if code[:n] in groups:
            return groups[code[:n]]
    return "other"


def clean_id(v) -> str | None:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return text(v)


def rows_of(page: list[dict], layer: dict, r: dict, pull_id: int) -> dict[str, list]:
    f = layer["fields"]
    groups, units_by_use = layer.get("use_groups") or {}, layer.get("units_by_use") or {}
    year = int(layer.get("tax_year") or 0)
    out: dict[str, list] = {"parcel": [], "address": [], "building": [], "value": [], "shape": []}
    seen = set()
    for feat in page:
        p = feat.get("properties") or {}
        pin = clean_id(p.get(f["id"]))
        if not pin:
            continue
        g = feat.get("geometry")
        if g and g.get("type") in ("Polygon", "MultiPolygon"):
            out["shape"].append((pin, year, json.dumps(g), pull_id))
        if pin in seen:
            continue
        seen.add(pin)

        def get(name, p=p):
            return p.get(f[name]) if f.get(name) else None

        use = (text(get("use_code")) or "").upper()
        group = group_for(use, groups)
        address = " ".join((text(get("address")) or "").upper().split()) or None
        zip5 = (text(get("zip")) or "")[:5] or None
        if not zip5 and address and (m := re.search(r"\b(\d{5})(?:-\d{4})?$", address)):
            zip5 = m.group(1)
        if address and layer.get("address_strip_city"):
            address = re.sub(r",?\s+[A-Z .]+,?\s+[A-Z]{2}\s+\d{5}(-\d{4})?$", "", address).strip() or address
        if layer.get("use_from_units"):
            # No use code that separates houses from lots: residential class with 0 living units is a vacant lot.
            n = integer(num_or_none(get("units")))
            residential = use.startswith(tuple(layer.get("residential_prefixes") or ["R"]))
            group = "other" if not residential else "vacant" if not n else "single" if n == 1 else "multi"
        nbhd = text(get("nbhd"))
        tax_year = integer(get("tax_year")) or year
        out["parcel"].append((pin, pin, tax_year, r["id"], use or None, nbhd, zip5,
                              int(zip5) if zip5 and zip5.isdigit() else None, zip5, group, pull_id))  # fmt: skip
        out["address"].append((pin, tax_year, address, zip5, text(get("owner")), pull_id))
        living = integer(num_or_none(get("living_sqft")))
        built = integer(num_or_none(get("year_built")))
        units = integer(num_or_none(get("units"))) or units_by_use.get(use)
        land_sqft = num_or_none(get("land_sqft"))
        if land_sqft is None and (acres := num_or_none(get("land_acres"))):
            land_sqft = acres * 43560
        if living or (built and built > 1700) or (units and layer.get("use_from_units") and group != "other"):
            out["building"].append((pin, pin, tax_year, 1, use or None, units, living,
                                    round(land_sqft) if land_sqft else None,
                                    built if built and built > 1700 else None, pull_id))  # fmt: skip
        market, land = num_or_none(get("market_value")), num_or_none(get("land_value"))
        if market or land:
            out["value"].append((pin, pin, tax_year, use or None, nbhd, "certified", market, land, pull_id))
    return out


def num_or_none(v) -> float | None:
    try:
        return num(v)
    except (TypeError, ValueError):
        return None


def save(conn, rows: dict[str, list]) -> None:
    upsert(conn, "parcel", ["pin", "pin10", "tax_year", "municipality_id", "class", "nbhd_code", "zip",
                            "community_area_num", "community_area_name", "use_group", "source_pull_id"], "pin", rows["parcel"])  # fmt: skip
    upsert(conn, "parcel_address", ["pin", "tax_year", "address", "zip", "owner_name", "source_pull_id"], "pin",
           rows["address"])  # fmt: skip
    upsert(conn, "building_char", ["row_id", "pin", "tax_year", "card", "class", "apartments", "building_sqft",
                                   "land_sqft", "year_built", "source_pull_id"], "row_id", rows["building"])  # fmt: skip
    upsert(conn, "assessed_value", ["pin", "pin10", "tax_year", "class", "nbhd", "stage", "market_value",
                                    "land_market_value", "source_pull_id"], "pin, tax_year", rows["value"])  # fmt: skip
    upsert(conn, "parcel_shape", ["pin10", "vintage", "the_geom", "source_pull_id"], "pin10", rows["shape"], GEOM,
           on_conflict=MERGE)  # fmt: skip


def run(limit: int | None = None, url: str | None = None, client: ArcGIS | None = None) -> int:
    r = region.current()
    layer = r["parcel_layer"]
    client = client or ArcGIS(layer["url"], timeout=180)
    f = layer["fields"]
    where = layer.get("where", "1=1")
    total = 0
    with connect(url) as conn:
        region.ensure_rows(conn)
        pull_id = start_pull(conn, client.host, layer["url"].split("/rest/services/")[-1], where)
        conn.commit()
        try:
            fields = ",".join(sorted({v for v in f.values() if v}))
            for page in client.features(where, out_fields=fields, key=layer.get("key", "OBJECTID"),
                                        page_size=min(limit or 10**9, layer.get("page_size", 1000))):  # fmt: skip
                rows = rows_of(page, layer, r, pull_id)
                save(conn, rows)
                conn.commit()
                total += len(rows["parcel"])
                if limit and total >= limit:
                    break
            conn.execute(
                "update parcel_shape s set lot_sqft = round(m.area_sqft), frontage_ft = round(m.short_ft, 1),"
                " depth_ft = round(m.long_ft, 1) from parcel_shape t, lateral lot_measures(t.geom) m"
                " where s.pin10 = t.pin10 and s.source_pull_id = %s",
                (pull_id,),
            )
            conn.execute(
                "update parcel p set geom = st_pointonsurface(s.geom) from parcel_shape s"
                " where s.pin10 = p.pin10 and s.source_pull_id = %s",
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
    print(f"parcels loaded: {run(ap.parse_args().limit):,}")
