"""Run the nightly loads in order, rebuild parcel_site, then print the load report.

Incremental sources (sales, permits) pull only what is new. Yearly sources reload the current tax year.
Run: python -m jobs.nightly [--year 2026] [--skip-yearly]
"""

import argparse
import sys
import traceback
from collections.abc import Callable

import psycopg

from core import errors, region
from core.settings import settings
from jobs import (
    build_comps,
    build_cost_index,
    build_land_values,
    build_lot_use,
    build_older_sales,
    build_parcel_site,
    extract_rezoning_districts,
    load_addresses,
    load_assessed_values,
    load_boundaries,
    load_building_chars,
    load_city_layers,
    load_condos,
    load_cost_escalation,
    load_foreclosure_auctions,
    load_hpi,
    load_lots_for_sale,
    load_overlays,
    load_parcel_extras,
    load_parcel_shapes,
    load_parcels,
    load_permits,
    load_rents,
    load_rezonings,
    load_sales,
    load_signals,
    load_streets,
    load_tax_sale,
    load_transit,
    load_zoning,
    report,
    score_parcels,
    seed_rules,
)


def region_steps(skip_yearly: bool) -> list[tuple[str, Callable]]:
    """A region outside Chicago: its parcel loader, its zoning layer, then the shared builders."""
    from jobs import build_region, load_arcgis_parcels, load_dcad, load_fl_dor, load_tcad, load_zoning_layer

    r = region.current()
    loaders = {
        "fl_dor": load_fl_dor.run,
        "arcgis_parcels": load_arcgis_parcels.run,
        "dcad": load_dcad.run,
        "tcad": load_tcad.run,
    }
    loader = loaders.get(r.get("parcel_loader"))
    if loader is None:
        raise SystemExit(f"region {r['id']}: no parcel loader yet (parcel_loader in region.json)")
    yearly = [
        ("parcels, values, sales and lot shapes", lambda: loader()),
        ("house price index", lambda: load_hpi.run()),
    ]
    return ([] if skip_yearly else yearly) + [
        ("zoning", lambda: load_zoning_layer.run()),
        ("cost escalation", lambda: load_cost_escalation.run()),
        ("rules", lambda: seed_rules.run()),
        ("parcel sites", lambda: build_parcel_site.run()),
        ("lot use, comps and land values", lambda: build_region.run()),
        ("development score", lambda: score_parcels.run()),
    ]


def steps(year: int, skip_yearly: bool) -> list[tuple[str, Callable]]:
    if not region.is_chicago():
        return region_steps(skip_yearly)
    nightly = [
        ("sales", lambda: load_sales.run()),
        ("permits", lambda: load_permits.run()),
        ("zoning", lambda: load_zoning.run()),
        ("overlays", lambda: load_overlays.run()),
        ("transit", lambda: load_transit.run()),
        ("signals", lambda: load_signals.run()),
        ("assessor permits", lambda: load_parcel_extras.run_source("permits")),
        ("city layers", lambda: load_city_layers.run()),
        ("cost escalation", lambda: load_cost_escalation.run()),
        ("lots for sale", lambda: load_lots_for_sale.run()),
        ("foreclosure auctions", lambda: load_foreclosure_auctions.run()),
        ("rezonings", lambda: load_rezonings.run()),
        ("tax sale list", lambda: load_tax_sale.run()),
        # reload wipes the districts read from the ordinance scans; copy them back from the repo CSVs (free)
        ("rezoning districts", lambda: extract_rezoning_districts.apply()),
    ]
    yearly = [
        ("parcels", lambda: load_parcels.run(year)),
        ("parcel shapes", lambda: load_parcel_shapes.run()),
        ("addresses", lambda: load_addresses.run(year)),
        ("building characteristics", lambda: load_building_chars.run(year)),
        ("condos", lambda: load_condos.run(year)),
        ("boundaries", lambda: load_boundaries.run()),
        ("street segments", lambda: load_streets.run()),
        ("house price index", lambda: load_hpi.run()),
        ("rents", lambda: load_rents.run()),
        ("parcel proximity", lambda: load_parcel_extras.run_source("proximity")),
        ("tax-exempt parcels", lambda: load_parcel_extras.run_source("exempt")),
        ("building footprints", lambda: load_parcel_extras.run_source("footprints")),
        ("assessed values", lambda: load_assessed_values.run()),
    ]
    build = [
        ("parcel sites", lambda: build_parcel_site.run()),
        ("lot use and block faces", lambda: build_lot_use.run()),
        ("comps", lambda: build_comps.run()),
        ("older sales", lambda: build_older_sales.run()),
        ("cost index", lambda: build_cost_index.run()),
        ("land values", lambda: build_land_values.run()),
        ("rules", lambda: seed_rules.run()),
        ("development score", lambda: score_parcels.run()),
    ]
    return ([] if skip_yearly else yearly) + nightly + build


# One run at a time: the scheduled nightly Machine and a manual or first full load must not overlap
# (docs/deploy.md). A Postgres session lock, released when the connection closes.
LOCK_KEY = 25125


def _lock() -> tuple[bool, psycopg.Connection | None]:
    """(go ahead, connection holding the lock). No database: go ahead without a lock; the steps report it."""
    try:
        conn = psycopg.connect(settings.database_url, autocommit=True, connect_timeout=10)
    except psycopg.OperationalError:
        return True, None
    if conn.execute("select pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]:
        return True, conn
    conn.close()
    return False, None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--skip-yearly", action="store_true", help="skip the tax-year reloads")
    a = ap.parse_args(argv)
    go, lock = _lock()
    if not go:
        print("another nightly run is in progress; this one stops without loading anything", flush=True)
        return 0
    try:
        return _run(a)
    finally:
        if lock is not None:
            lock.close()


def _run(a: argparse.Namespace) -> int:
    failures = 0
    todo = steps(a.year, a.skip_yearly)
    for i, (name, step) in enumerate(todo, 1):
        # A start line per step, so a watcher (the desktop program's status window) sees the long ones begin.
        print(f"[{i}/{len(todo)}] {name}: starting", flush=True)
        try:
            print(f"{name}: {step()}", flush=True)
        except Exception as e:  # noqa: BLE001 - one failed source must not stop the others; the report lists it
            failures += 1
            print(f"{name}: FAILED", flush=True)
            traceback.print_exc()
            errors.report(e, {"job": "nightly", "step": name}, wait=True)  # no-op without SENTRY_DSN
    report.main()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
