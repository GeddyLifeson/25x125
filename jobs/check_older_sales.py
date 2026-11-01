"""Fit and check the older-sale fallback curve; writes data/rules/older_sale_fallback.json.

For each kept new-construction comp, the local older-building price (engine/older_sales.local_price, as of the
comp's sale date) is paired with the comp's price per unit. The curve ln(new) = a + b ln(older) is fit by least
squares on comps sold before the holdout date and checked on comps sold after it; the written curve is then
refit on all comps. Buildings and condo units each get their own curve.
Run: python -m jobs.check_older_sales [--holdout 2025-07-01] [--dry-run]
"""

import argparse
import json
import math
import statistics as st
from datetime import UTC, date, datetime

from core.db import connect
from engine.comps import index_from_db, pool_from_db
from engine.older_sales import RULES_FILE, local_price, sales_from_db


def fit(pts: list[tuple[float, float]]) -> tuple[float, float]:
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mx, my = st.mean(xs), st.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def quantile(vals: list[float], q: float) -> float:
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, round(q * (len(s) - 1))))]


def score(pts, a, b) -> dict:
    errs = [math.exp(y - (a + b * x)) - 1 for x, y in pts]
    ratios = [1 / (1 + e) for e in errs]  # estimate / sale
    return {
        "n": len(pts),
        "median_abs_error": round(st.median(abs(e) for e in errs), 3),
        "within_15pct": round(sum(abs(e) <= 0.15 for e in errs) / len(errs), 3),
        "median_ratio": round(st.median(ratios), 3),
        "cod": round(100 * st.mean(abs(r - st.median(ratios)) for r in ratios) / st.median(ratios), 1),
    }


def run(holdout: date, url: str | None = None, write: bool = True) -> dict:
    with connect(url) as conn:
        pool, sales, index = pool_from_db(conn), sales_from_db(conn), index_from_db(conn)
    out = {
        "source": "python -m jobs.check_older_sales: comps (comp table) against older 2-6 unit building sales"
        " (older_sale table) within 0.75 or 1.5 mi in the 3 years before each comp's sale",
        "verified_on": datetime.now(UTC).date().isoformat(),
        "holdout_from": holdout.isoformat(),
        "extrapolation_widen": 0.15,
        "curves": {},
    }
    for kind in ("building", "condo"):
        pts, dates = [], []
        for c in pool:
            if c.kind != kind:
                continue
            local = local_price(sales, c.lat, c.lon, c.sale_date, index)
            if local:
                pts.append((math.log(local[0]), math.log(c.price_per_unit)))
                dates.append(c.sale_date)
        train = [p for p, d in zip(pts, dates, strict=True) if d < holdout]
        test = [p for p, d in zip(pts, dates, strict=True) if d >= holdout]
        a_t, b_t = fit(train)
        a, b = fit(pts)
        res = [y - (a + b * x) for x, y in pts]
        out["curves"][kind] = {
            "a": round(a, 4),
            "b": round(b, 4),
            "n": len(pts),
            "band": [round(math.exp(quantile(res, 0.10)), 3), round(math.exp(quantile(res, 0.90)), 3)],
            "fit_range": [round(math.exp(min(x for x, _ in pts))), round(math.exp(max(x for x, _ in pts)))],
            "holdout": {"fit_before": {"a": round(a_t, 4), "b": round(b_t, 4), "n": len(train)},
                        **score(test, a_t, b_t)},
        }  # fmt: skip
    if write:
        RULES_FILE.write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", default="2025-07-01")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(date.fromisoformat(a.holdout), write=not a.dry_run), indent=2))
