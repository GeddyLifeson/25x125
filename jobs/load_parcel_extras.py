"""Load the free depth channels found in the October 30, 2026 channel audit.

- proximity: Assessor parcel proximity (ydue-e5u3), latest year, Chicago lots only once parcels are loaded.
- permits: Assessor permits (6yjf-dfxs) for the City of Chicago; ties city permits to PINs.
- exempt: Assessor tax-exempt parcels (vgzx-68gb), latest year.
- footprints: City of Chicago building footprints (syp8-uezg) with stories, units and year built.

Each source is replaced on every run.
Run: python -m jobs.load_parcel_extras [--source footprints]
"""

import argparse
import json
from collections.abc import Callable

from core.db import connect
from core.socrata import CHICAGO, COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, num, text, upsert


def year_value(v) -> int | None:
    """Assessor years after 2023 end in '.0'."""
    return integer(v)


def day(v, low: str = "1990-01-01", high: str = "2100-01-01") -> str | None:
    """ISO date, dropping the out-of-range dates some Assessor permit rows carry (e.g. year 2210)."""
    d = (text(v) or "")[:10]
    return d if low <= d < high else None


PROXIMITY_FIELDS = [
    "pin10", "year", "num_foreclosure_in_half_mile_past_5_years", "num_foreclosure_per_1000_pin_past_5_years",
    "num_pin_in_half_mile", "nearest_new_construction_pin10", "nearest_new_construction_dist_ft",
    "nearest_vacant_land_pin10", "nearest_vacant_land_dist_ft", "airport_dnl_total", "nearest_cta_stop_dist_ft",
    "nearest_metra_stop_dist_ft", "nearest_road_arterial_daily_traffic", "num_school_in_half_mile",
]  # fmt: skip
PROXIMITY_COLUMNS = [
    "pin10", "tax_year", "foreclosures_half_mile_5y", "foreclosures_per_1000_pins", "pins_half_mile",
    "nearest_new_construction_pin10", "nearest_new_construction_ft", "nearest_vacant_land_pin10",
    "nearest_vacant_land_ft", "airport_noise_dnl", "nearest_cta_stop_ft", "nearest_metra_stop_ft",
    "arterial_daily_traffic", "schools_half_mile", "source_pull_id",
]  # fmt: skip


def proximity_row(r: dict, pull_id: int) -> tuple | None:
    if not text(r.get("pin10")):
        return None
    return (
        text(r["pin10"]),
        year_value(r.get("year")),
        integer(r.get("num_foreclosure_in_half_mile_past_5_years")),
        num(r.get("num_foreclosure_per_1000_pin_past_5_years")),
        integer(r.get("num_pin_in_half_mile")),
        text(r.get("nearest_new_construction_pin10")),
        num(r.get("nearest_new_construction_dist_ft")),
        text(r.get("nearest_vacant_land_pin10")),
        num(r.get("nearest_vacant_land_dist_ft")),
        num(r.get("airport_dnl_total")),
        num(r.get("nearest_cta_stop_dist_ft")),
        num(r.get("nearest_metra_stop_dist_ft")),
        num(r.get("nearest_road_arterial_daily_traffic")),
        integer(r.get("num_school_in_half_mile")),
        pull_id,
    )


PERMIT_COLUMNS = [
    "row_id", "pin", "permit_number", "local_permit_number", "date_issued", "status", "assessable", "amount",
    "job_code", "work_description", "improvement_code", "source_pull_id",
]  # fmt: skip


def permit_row(r: dict, pull_id: int) -> tuple | None:
    if not text(r.get("row_id")) or not text(r.get("pin")):
        return None
    return (
        text(r["row_id"]),
        text(r["pin"]),
        text(r.get("permit_number")),
        text(r.get("local_permit_number")),
        day(r.get("date_issued")),
        text(r.get("status")),
        text(r.get("assessable")),
        num(r.get("amount")),
        text(r.get("job_code_primary")),
        text(r.get("work_description")),
        text(r.get("improvement_code_1")),
        pull_id,
    )


EXEMPT_COLUMNS = ["pin", "tax_year", "class", "owner_name", "owner_num", "address", "source_pull_id"]


def exempt_row(r: dict, pull_id: int) -> tuple | None:
    if not text(r.get("pin")):
        return None
    return (
        text(r["pin"]),
        year_value(r.get("year")),
        text(r.get("class")),
        text(r.get("owner_name")),
        text(r.get("owner_num")),
        text(r.get("property_address")),
        pull_id,
    )


FOOTPRINT_COLUMNS = [
    "bldg_id", "status", "stories", "units", "year_built", "building_sqft", "footprint_sqft", "address",
    "the_geom", "source_pull_id",
]  # fmt: skip
FOOTPRINT_GEOM = {"geom": "st_multi(st_makevalid(st_setsrid(st_geomfromgeojson(the_geom), 4326)))"}


def footprint_address(r: dict) -> str | None:
    parts = [text(r.get(k)) for k in ("f_add1", "pre_dir1", "st_name1", "st_type1")]
    if parts[0] in (None, "0"):
        return None
    return " ".join(p for p in parts if p)


def footprint_row(r: dict, pull_id: int) -> tuple | None:
    if not text(r.get("bldg_id")) or not r.get("the_geom"):
        return None
    year_built = integer(r.get("year_built"))
    return (
        text(r["bldg_id"]),
        text(r.get("bldg_statu")),
        integer(r.get("stories")) or None,
        integer(r.get("no_of_unit")) or None,
        year_built if year_built and year_built > 1800 else None,
        num(r.get("bldg_sq_fo")) or None,
        num(r.get("shape_area")),
        footprint_address(r),
        json.dumps(r["the_geom"]),
        pull_id,
    )


def latest_year(client: Socrata, dataset: str) -> str:
    """The newest year value exactly as the portal stores it (e.g. '2026.0')."""
    rows = client.get(dataset, {"$select": "max(year) as y"})
    return rows[0]["y"]


SOURCES: dict[str, dict] = {
    "proximity": {
        "host": COOK, "dataset": "ydue-e5u3", "table": "parcel_proximity", "key": "pin10", "order": "pin10",
        "columns": PROXIMITY_COLUMNS, "to_row": proximity_row, "select": ",".join(PROXIMITY_FIELDS),
        "where": lambda c: f"year = '{latest_year(c, 'ydue-e5u3')}'",
    },
    "permits": {
        "host": COOK, "dataset": "6yjf-dfxs", "table": "assessor_permit", "key": "row_id", "order": "row_id",
        "columns": PERMIT_COLUMNS, "to_row": permit_row, "where": lambda c: "municipality = 'CITY OF CHICAGO'",
    },
    "exempt": {
        "host": COOK, "dataset": "vgzx-68gb", "table": "exempt_parcel", "key": "pin", "order": "pin",
        "columns": EXEMPT_COLUMNS, "to_row": exempt_row,
        "where": lambda c: f"year = '{latest_year(c, 'vgzx-68gb')}' and township_code between '70' and '77'",
    },
    "footprints": {
        "host": CHICAGO, "dataset": "syp8-uezg", "table": "building_footprint", "key": "bldg_id",
        "order": "bldg_id", "columns": FOOTPRINT_COLUMNS, "to_row": footprint_row, "geom": FOOTPRINT_GEOM,
        "where": lambda c: "bldg_statu in ('ACTIVE', 'PROPOSED')", "page_size": 20_000,
    },
}  # fmt: skip

# After each load: keep Chicago lots only (when parcels are loaded) and tie footprints to lots.
AFTER = {
    "proximity": "delete from parcel_proximity x where exists (select 1 from parcel limit 1)"
    " and not exists (select 1 from parcel p where p.pin10 = x.pin10)",
    "footprints": "update building_footprint f set pin10 ="
    " (select s.pin10 from parcel_shape s where st_contains(s.geom, st_pointonsurface(f.geom)) limit 1)",
}


def run_source(name: str, client: Socrata | None = None, url: str | None = None) -> int:
    s = SOURCES[name]
    client = client or Socrata(s["host"])
    to_row: Callable = s["to_row"]
    total = 0
    with connect(url) as conn:
        where = s["where"](client)
        pull_id = start_pull(conn, s["host"], s["dataset"], where)
        conn.commit()
        try:
            conn.execute(f"delete from {s['table']}")
            for page in client.pages(
                s["dataset"], order=s["order"], select=s.get("select"), where=where,
                page_size=s.get("page_size", 50_000),
            ):  # fmt: skip
                rows = (row for r in page if (row := to_row(r, pull_id)))
                total += upsert(conn, s["table"], s["columns"], s["key"], rows, s.get("geom"))
            if name in AFTER:
                conn.execute(AFTER[name])
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


def run(url: str | None = None) -> dict[str, int]:
    return {name: run_source(name, url=url) for name in SOURCES}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=list(SOURCES))
    a = ap.parse_args()
    for name in [a.source] if a.source else SOURCES:
        print(f"{name}: {run_source(name):,}", flush=True)
