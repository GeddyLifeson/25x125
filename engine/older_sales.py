"""Sale value where no new-construction comps sit within 3 miles (the comp engine's citywide ring).

Method (docs/research/older-sale-fallback-2026-11-01.md; curve in data/rules/older_sale_fallback.json, refit by
`python -m jobs.check_older_sales`):
1. Local older-building price: inverse-distance weighted median price per unit of older 2-6 unit building sales
   (older_sale table) within 0.75 mi, else 1.5 mi, in the 3 years before the estimate date, each moved to the
   estimate year with the FHFA metro index. At least 10 sales.
2. New-construction price per unit = exp(a + b x ln(local older price)), with a and b fit on new-construction
   comps against the older sales around each one. b is under 1: new buildings cost about the same to build
   everywhere, so their prices vary less across the city than older buildings do.
3. Range: central x the 10th and 90th percentile fit errors. When the local older price is outside the range
   the curve was fit on, the estimate is marked as an extrapolation and the range is widened.
"""

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from engine.comps import METRO, Comp, Index, miles, weighted_quantile

RULES_FILE = Path(__file__).resolve().parents[1] / "data" / "rules" / "older_sale_fallback.json"
RADII = (0.75, 1.5)
YEARS = 3
MIN_SALES = 10


@dataclass(frozen=True)
class OlderSale:
    sale_date: date
    price_per_unit: float
    lat: float
    lon: float


def _metro_factor(index: Index | None, sale_date: date, to_year: int) -> float:
    if index is None:
        return 1.0
    probe = Comp("", "", "building", "", sale_date, 0.0, 0, None, 0.0, 0.0)
    return index.factor(probe, to_year, ("metro",))[0]


def local_price(
    sales: list[OlderSale], lat: float, lon: float, as_of: date, index: Index | None = None
) -> tuple[float, int, float] | None:
    """(weighted median price per unit, sales used, radius in miles), or None when too few sales nearby."""
    start = date(as_of.year - YEARS, as_of.month, min(as_of.day, 28))
    recent = [s for s in sales if start <= s.sale_date < as_of]
    for radius in RADII:
        near = [(s, d) for s in recent if (d := miles(lat, lon, s.lat, s.lon)) <= radius]
        if len(near) >= MIN_SALES:
            vals = [
                (s.price_per_unit * _metro_factor(index, s.sale_date, as_of.year), 1 / (0.2 + d))
                for s, d in near
            ]
            return weighted_quantile(vals, 0.5), len(near), radius
    return None


def load_curve(path: Path = RULES_FILE) -> dict:
    return json.loads(path.read_text())


def estimate(
    sales: list[OlderSale],
    lat: float,
    lon: float,
    as_of: date,
    kind: str = "building",
    curve: dict | None = None,
    index: Index | None = None,
) -> dict | None:
    curve = curve or load_curve()
    c = curve["curves"][kind]
    local = local_price(sales, lat, lon, as_of, index)
    if local is None:
        return None
    price, n, radius = local
    central = math.exp(c["a"] + c["b"] * math.log(price))
    low, high = c["band"]
    extrapolated = not (c["fit_range"][0] <= price <= c["fit_range"][1])
    if extrapolated:
        w = curve["extrapolation_widen"]
        low, high = low * (1 - w), high * (1 + w)
    return {
        "method": "older-building sales converted to new construction",
        "central": round(central),
        "low": round(central * low),
        "high": round(central * high),
        "local_older_price_per_unit": round(price),
        "older_sales": n,
        "radius_mi": radius,
        "extrapolated": extrapolated,
        "curve": {"a": c["a"], "b": c["b"], "fit_on": c["n"], "verified_on": curve["verified_on"]},
    }


def sales_from_db(conn) -> list[OlderSale]:
    rows = conn.execute(
        "select sale_date, price_per_unit, st_y(geom), st_x(geom) from older_sale where geom is not null"
    ).fetchall()
    return [OlderSale(r[0], float(r[1]), r[2], r[3]) for r in rows]


__all__ = ["METRO", "OlderSale", "estimate", "load_curve", "local_price", "sales_from_db"]
