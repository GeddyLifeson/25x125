"""Calibrate and check a region's sale values against its own comp pool.

Leave-one-out: each kept comp is estimated from the others (never from a comp within 0.02 mi), with prices
moved to the newest sale's year by the FHFA index. Reports the median error and the share within 15%, picks
the size elasticity with the lowest median error, fits the 80% range (10th and 90th percentile errors by
search ring), measures how the county appraiser's land value compares with vacant-lot sale prices, and what
the new-build sales imply about construction cost. Also draws a fixed test set of 35 sales.

--write saves the fitted values to data/regions/<id>/rules/ (sale_band.json, feasibility_defaults.json) and
the test set to data/regions/<id>/reference/test_parcels.csv.
Run: python -m jobs.check_region [--write] [--sample 800]
"""

import argparse
import csv
import hashlib
import json
import statistics as st
from dataclasses import replace
from datetime import date, timedelta

from core import region
from core.db import connect
from engine.comps import Target, estimate, index_from_db, miles, params_from_files, pool_from_db

GRID = (0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def _key(c) -> str:
    return hashlib.md5(c.id.encode()).hexdigest()


def loo(pool, index, params, targets, as_of: date) -> list[tuple]:
    """(comp, estimate, actual moved to as_of) for each target that could be estimated."""
    out = []
    for c in targets:
        t = Target(c.lat, c.lon, min(c.units, 6), as_of, c.sqft_per_unit, tract=c.tract, zip=c.zip)
        est = estimate(t, pool, params, index,
                       exclude=lambda o, c=c: o.pin == c.pin or miles(c.lat, c.lon, o.lat, o.lon) < 0.02)  # fmt: skip
        if est is None:
            continue
        f = index.factor(c, as_of.year, params.index_levels)[0] if index else 1.0
        out.append((c, est, c.price_per_unit * f))
    return out


def summary(results) -> dict:
    if not results:
        return {"n": 0}
    err = [abs(e.per_unit / a - 1) for _, e, a in results]
    return {"n": len(err), "median_abs_error": round(st.median(err), 4),
            "within_15pct": round(sum(x <= 0.15 for x in err) / len(err), 3)}  # fmt: skip


def fit_band(results, min_n: int = 30) -> dict:
    groups: dict[str, list[float]] = {}
    for _, e, a in results:
        for k in (f"{e.ring}|building", f"{e.ring}|any", "any|building", "any|any"):
            groups.setdefault(k, []).append(a / e.per_unit - 1)
    band = {}
    for k, v in groups.items():
        if len(v) >= min_n:
            q = st.quantiles(v, n=10)
            band[k] = [round(q[0], 3), round(q[-1], 3), len(v)]
    return band


def land_ratio(conn) -> dict | None:
    row = conn.execute(
        """select count(*), percentile_cont(0.5) within group (order by v.land_market_value / l.price)
           from land_sale l join parcel p on p.pin = l.pin and p.use_group = 'vacant'
           join lateral (select land_market_value from assessed_value v where v.pin = l.pin
                         and v.land_market_value > 0 order by tax_year desc limit 1) v on true"""
    ).fetchone()
    return (
        {"sales": row[0], "appraiser_land_over_sale_price": round(float(row[1]), 3)} if row[0] >= 30 else None
    )


def implied_cost(conn) -> dict | None:
    """What new-house sales leave for construction per sq ft after land and the builder's other costs, using
    the NAHB 2024 shares of price: profit 11.0%, overhead 5.7%, commission 2.8%, financing 1.5%, marketing 0.8%."""
    row = conn.execute(
        """select count(*), percentile_cont(array[0.25, 0.5, 0.75]) within group (
                    order by (c.price * (1 - 0.218) - v.land_market_value / %s) / c.sqft),
                  percentile_cont(0.5) within group (order by c.sqft)
           from comp c join lateral (select land_market_value from assessed_value v where v.pin = c.pin
                                     and v.land_market_value > 0 order by tax_year desc limit 1) v on true
           where c.excluded is null and c.units = 1 and c.sqft between 1000 and 3500""",
        ((land_ratio(conn) or {}).get("appraiser_land_over_sale_price") or 1.0,),
    ).fetchone()
    if not row[0]:
        return None
    return {"sales": row[0], "per_sqft_p25": round(row[1][0]), "per_sqft_median": round(row[1][1]),
            "per_sqft_p75": round(row[1][2]), "median_house_sqft": round(row[2])}  # fmt: skip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--sample", type=int, default=800)
    a = ap.parse_args(argv)
    r = region.current()
    with connect() as conn:
        pool, index = pool_from_db(conn), index_from_db(conn)
        land, cost = land_ratio(conn), implied_cost(conn)
    if len(pool) < 40:
        print(f"{r['name']}: only {len(pool)} comps; nothing fitted")
        return 1
    params = replace(params_from_files(), band={})
    as_of = max(c.sale_date for c in pool) + timedelta(days=1)
    ordered = sorted(pool, key=_key)
    test, targets = ordered[:35], ordered[: a.sample]
    by_e = {}
    for e in GRID:
        p = replace(params, size_elasticity={**params.size_elasticity, "building": e})
        by_e[e] = summary(loo(pool, index, p, targets, as_of))
        print(f"size elasticity {e:.1f}: {by_e[e]}")
    best = min(by_e, key=lambda e: by_e[e]["median_abs_error"])
    params = replace(params, size_elasticity={**params.size_elasticity, "building": best})
    results = loo(pool, index, params, targets, as_of)
    band = fit_band(results)
    params = replace(params, band={k: v[:2] for k, v in band.items()})
    test_results = loo(pool, index, params, test, as_of)
    inside = [e.low <= act <= e.high for _, e, act in test_results if e.low]
    report = {
        "region": r["id"], "computed_on": date.today().isoformat(), "comps": len(pool),
        "sales_from": min(c.sale_date for c in pool).isoformat(), "sales_to": max(c.sale_date for c in pool).isoformat(),
        "size_elasticity": best, "leave_one_out": by_e[best], "test_set": summary(test_results),
        "test_set_inside_range": round(sum(inside) / len(inside), 3) if inside else None,
        "appraiser_land": land, "implied_construction_cost": cost,
    }  # fmt: skip
    print(json.dumps(report, indent=2))
    if a.write:
        rules = region.rules_dir()
        rules.mkdir(parents=True, exist_ok=True)
        (rules / "sale_band.json").write_text(json.dumps({
            "source": "python -m jobs.check_region: 10th and 90th percentile leave-one-out errors, actual / estimate - 1",
            "verified_on": date.today().isoformat(), "fit_on": f"{len(results)} of {len(pool)} comps",
            "rings": "0: 0.75 mi same size group, 1: 1.5 mi same group, 2: 1.5 mi any, 3: 3 mi any, 4: citywide",
            "band": band}, indent=2) + "\n")  # fmt: skip
        own = rules / "feasibility_defaults.json"
        d = json.loads(own.read_text()) if own.exists() else {"extends": True}
        d.setdefault("sale_comps", {}).setdefault("method", {})["size_elasticity"] = {
            "building": best,
            "condo": 0.5,
        }
        d["calibration"] = report
        if land:
            d["appraiser_land"] = {
                "ratio_to_sale_price": land["appraiser_land_over_sale_price"], "sales": land["sales"],
                "rule": "where no vacant-lot sales are nearby, land = the appraiser's land value / this ratio",
                "source": "python -m jobs.check_region", "verified_on": date.today().isoformat()}  # fmt: skip
        own.write_text(json.dumps(d, indent=2) + "\n")
        ref = region.REGIONS_DIR / r["id"] / "reference"
        ref.mkdir(exist_ok=True)
        with (ref / "test_parcels.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(
                ["parcel_id", "sale_date", "sale_price", "units", "sqft", "estimate_per_unit", "error"]
            )
            for c, e, act in test_results:
                w.writerow([c.pin, c.sale_date, round(c.price_per_unit * c.units), c.units,
                            round((c.sqft_per_unit or 0) * c.units), round(e.per_unit), round(e.per_unit / act - 1, 3)])  # fmt: skip
        print(f"wrote {rules}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
