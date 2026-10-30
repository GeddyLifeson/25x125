"""Step 3 acceptance check for sale values, and the refit of the sale range.

Three measurements (targets from docs/research/decisions-2026-10-30.md, decision 13):
1. Test set: each test building's first sale, estimated without its own sale or any comp within 0.02 mi.
   Target: 70% or more within 15%, reported with a 95% interval.
2. Out-of-time holdout: every pool sale from the holdout start on, estimated only from sales before it.
   Targets: 55% or more within 15%, median error 13% or less, COD 20 or less for buildings and 15 or less for
   condo units, PRB interval overlapping -0.10 to +0.10.
3. Range: the 10th and 90th percentile of leave-one-out errors on sales before the holdout start, by search
   ring and kind, then the share of holdout sales inside that range. Target 75-85%.
Writes the fitted range to data/rules/sale_band.json with --write.
Run: python -m jobs.check_comps [--write] [--holdout-start 2025-07-01]
"""

import argparse
import csv
import json
import math
import statistics as st
from datetime import date
from pathlib import Path

from core.db import connect
from engine.comps import Comp, Params, Target, estimate, index_from_db, miles, params_from_files, pool_from_db

ROOT = Path(__file__).resolve().parents[1]
TEST_PARCELS = ROOT / "data" / "reference" / "test_parcels.csv"
BAND_FILE = ROOT / "data" / "rules" / "sale_band.json"
UNIT_SQFT = {2: 1300, 3: 1200}


def test_targets(conn) -> list[dict]:
    out = []
    for t in csv.DictReader(TEST_PARCELS.open()):
        row = conn.execute(
            """select st_y(geom), st_x(geom), pins from permit
               where address = %s and permit_type = 'PERMIT - NEW CONSTRUCTION' and geom is not null
               order by issue_date desc limit 1""",
            (" ".join(t["addr"].upper().split()),),
        ).fetchone()
        if row:
            out.append({**t, "lat": row[0], "lon": row[1], "pin10s": {p[:10] for p in row[2] or []}})
    return out


def wilson(k: int, n: int) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def metrics(pairs: list[tuple[float, float]]) -> dict:
    """pairs of (estimate, actual)."""
    if not pairs:
        return {"n": 0}
    ratios = [e / a for e, a in pairs]
    errs = [abs(r - 1) for r in ratios]
    k = sum(x <= 0.15 for x in errs)
    med = st.median(ratios)
    cod = 100 * st.mean(abs(r - med) for r in ratios) / med
    # PRB (IAAO): regress (ratio - median) / median on log2 of a value proxy that mixes estimate and sale.
    xs = [math.log(0.5 * e / med + 0.5 * a) / math.log(2) for e, a in pairs]
    ys = [(r - med) / med for r in ratios]
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    prb = se = float("nan")
    if sxx > 0 and len(xs) > 2:
        prb = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
        resid = [y - my - prb * (x - mx) for x, y in zip(xs, ys, strict=True)]
        se = math.sqrt(sum(r * r for r in resid) / (len(xs) - 2) / sxx)
    lo, hi = wilson(k, len(pairs))
    return {
        "n": len(pairs), "within_15": k / len(pairs), "within_15_ci": (lo, hi), "mdape": st.median(errs),
        "median_ratio": med, "cod": cod, "prb": prb, "prb_ci": (prb - 1.96 * se, prb + 1.96 * se),
    }  # fmt: skip


def fmt(m: dict) -> str:
    if not m.get("n"):
        return "n 0"
    lo, hi = m["within_15_ci"]
    plo, phi = m["prb_ci"]
    return (
        f"n {m['n']:>5}  within 15% {m['within_15']:.0%} ({lo:.0%}-{hi:.0%})  median error {m['mdape']:.1%}"
        f"  median ratio {m['median_ratio']:.3f}  COD {m['cod']:.1f}  PRB {m['prb']:+.3f} ({plo:+.3f} to {phi:+.3f})"
    )


def run_test_set(pool, index, p: Params, targets) -> tuple[dict, list]:
    pairs, rows = [], []
    for t in targets:
        units, fs = int(t["units"]), date.fromisoformat(t["first_sale"])

        def ex(c, t=t, fs=fs):
            return (
                c.building_id[:10] in t["pin10s"]
                or miles(t["lat"], t["lon"], c.lat, c.lon) < 0.02
                or c.sale_date == fs
            )

        e = estimate(Target(t["lat"], t["lon"], units, fs, UNIT_SQFT.get(units, 1000)), pool, p, index, ex)
        actual = float(t["sale_per_unit"])
        if e:
            pairs.append((e.per_unit, actual))
            rows.append((t["addr"], units, actual, e))
    return metrics(pairs), rows


def run_pool(pool, index, p: Params, targets: list[Comp], same_kind: bool | str) -> list[tuple[Comp, object]]:
    out = []
    for c in targets:

        def ex(z, c=c):
            return z.building_id == c.building_id or z.sale_date >= c.sale_date

        kind = c.kind if same_kind == "all" or (same_kind and c.kind == "condo") else None
        t = Target(c.lat, c.lon, c.units, c.sale_date, c.sqft_per_unit, kind)
        e = estimate(t, pool, p, index, ex)
        if e:
            out.append((c, e))
    return out


def fit_band(results, min_n: int = 30) -> dict:
    errs: dict[str, list[float]] = {}
    for c, e in results:
        r = c.price_per_unit / e.per_unit - 1
        for key in (f"{e.ring}|{c.kind}", f"{e.ring}|any", f"any|{c.kind}", "any|any"):
            errs.setdefault(key, []).append(r)
    band = {}
    for key, v in errs.items():
        if len(v) >= min_n:
            q = st.quantiles(v, n=10)
            band[key] = [round(q[0], 3), round(q[-1], 3), len(v)]
    return band


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write", action="store_true", help="write the fitted range to data/rules/sale_band.json"
    )
    ap.add_argument("--holdout-start", default="2025-07-01")
    a = ap.parse_args(argv)
    start = date.fromisoformat(a.holdout_start)
    with connect() as conn:
        pool, index, targets = pool_from_db(conn), index_from_db(conn), test_targets(conn)
    print(
        f"pool: {len(pool):,} comps ({sum(c.kind == 'building' for c in pool)} buildings); test buildings {len(targets)}"
    )

    chosen = params_from_files()
    chosen.band = {}
    old = Params(max_age_years=4, size_elasticity={})
    variants = [
        ("2026-10-29 method: rings, 4 years, no adjustments", old, None, False),
        ("chosen: rings, 3 years, metro index, condo size", chosen, index, True),
    ]
    print("\nTest set (target: 70% within 15%)")
    for name, p, idx, _ in variants:
        m, _ = run_test_set(pool, idx, p, targets)
        print(f"  {name:50} {fmt(m)}")

    before = [c for c in pool if c.sale_date < start]
    hold = [c for c in pool if c.sale_date >= start]
    print(f"\nOut-of-time holdout: {len(hold)} sales from {start} (targets: 55% within 15%, median error 13%,"
          " COD 20 buildings / 15 condo, PRB interval overlapping +/-0.10)")  # fmt: skip
    for name, p, idx, sk in variants:
        res = run_pool(pool, idx, p, hold, sk)
        print(f"  {name:50} all      {fmt(metrics([(e.per_unit, c.price_per_unit) for c, e in res]))}")
        for kind in ("building", "condo"):
            sub = [(e.per_unit, c.price_per_unit) for c, e in res if c.kind == kind]
            print(f"  {'':50} {kind:8} {fmt(metrics(sub))}")

    name, p, idx, same_kind = variants[-1]
    print(f"\nRange fit on sales before {start} with the chosen method")
    band = fit_band(run_pool(pool, idx, p, before, same_kind))
    for k, v in sorted(band.items()):
        print(f"  ring|kind {k:12} x{1 + v[0]:.2f} to x{1 + v[1]:.2f}  (n {v[2]})")
    p.band = {k: v[:2] for k, v in band.items()}
    res = run_pool(pool, idx, p, hold, same_kind)
    inside = sum(e.low <= c.price_per_unit <= e.high for c, e in res if e.low)
    print(
        f"  holdout sales inside the 80% range: {inside} of {len(res)} ({inside / max(len(res), 1):.0%}); target 75-85%"
    )

    if a.write:
        BAND_FILE.write_text(json.dumps({
            "source": "python -m jobs.check_comps: 10th and 90th percentile leave-one-out errors, actual / estimate - 1",
            "verified_on": date.today().isoformat(),
            "fit_on": f"pool sales before {start}",
            "method": name,
            "holdout_coverage": round(inside / max(len(res), 1), 3),
            "rings": "0: 0.75 mi same size group, 1: 1.5 mi same group, 2: 1.5 mi any, 3: 3 mi any, 4: citywide",
            "band": band,
        }, indent=2) + "\n")  # fmt: skip
        print(f"wrote {BAND_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
