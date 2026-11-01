"""Run the nightly loads in order, rebuild parcel_site, then print the load report.

Incremental sources (sales, permits) pull only what is new. Yearly sources reload the current tax year.
Run: python -m jobs.nightly [--year 2026] [--skip-yearly]
"""

import argparse
import sys
import traceback
from collections.abc import Callable

from jobs import (
    build_comps,
    build_cost_index,
    build_land_values,
    build_lot_use,
    build_parcel_site,
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
    load_transit,
    load_zoning,
    report,
    score_parcels,
    seed_rules,
)


def steps(year: int, skip_yearly: bool) -> list[tuple[str, Callable]]:
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
        ("cost index", lambda: build_cost_index.run()),
        ("land values", lambda: build_land_values.run()),
        ("rules", lambda: seed_rules.run()),
        ("development score", lambda: score_parcels.run()),
    ]
    return ([] if skip_yearly else yearly) + nightly + build


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--skip-yearly", action="store_true", help="skip the tax-year reloads")
    a = ap.parse_args(argv)
    failures = 0
    for name, step in steps(a.year, a.skip_yearly):
        try:
            print(f"{name}: {step()}", flush=True)
        except Exception:  # noqa: BLE001 - one failed source must not stop the others; the report lists it
            failures += 1
            print(f"{name}: FAILED", flush=True)
            traceback.print_exc()
    report.main()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
