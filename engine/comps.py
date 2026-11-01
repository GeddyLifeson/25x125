"""Sale value from new-construction comps.

Method (docs/research/decisions-2026-10-30.md, decisions 1-13; parameters in
data/rules/feasibility_defaults.json sale_comps):
1. Search rings: same unit-count group within 0.75 mi, then 1.5 mi, then any group within 1.5 mi, then 3 mi,
   then citywide, until a ring holds the minimum count. Sales within 3 years of the estimate date.
2. Each comp's price per unit is moved to the estimate year with an FHFA index (by default the Chicago metro
   division; tract and ZIP can be switched on), and condo units are adjusted for size:
   price x (target sq ft / comp sq ft) ^ elasticity.
3. Inverse-distance weighted median, weight 1 / (0.2 + miles).
4. Optional thin-area blend: the local (first ring) median weighted n / (n + k) against the 3-mile median.
   Off by default: it did not beat the ring fallback on the holdout (jobs/check_comps.py).
5. Range: central x (1 + the 10th and 90th percentile leave-one-out error for the ring and kind), from
   data/rules/sale_band.json, refit by `python -m jobs.check_comps`.
"""

import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parents[1] / "data" / "rules"

MILES_PER_DEG_LAT = 69.0
COS_LAT = math.cos(math.radians(41.85))
METRO = "16984"  # Chicago-Naperville-Schaumburg metro division


@dataclass(frozen=True)
class Comp:
    id: str
    pin: str
    kind: str  # 'building' or 'condo'
    building_id: str
    sale_date: date
    price_per_unit: float
    units: int
    sqft_per_unit: float | None
    lat: float
    lon: float
    tract: str | None = None
    zip: str | None = None
    nbhd: str | None = None
    community_area: str | None = None


@dataclass(frozen=True)
class Target:
    lat: float
    lon: float
    units: int
    as_of: date
    sqft_per_unit: float | None = None
    kind: str | None = None  # restrict comps to one kind; None uses both
    tract: str | None = None
    zip: str | None = None


@dataclass
class Params:
    rings: list[tuple[float, bool]] = field(
        default_factory=lambda: [(0.75, True), (1.5, True), (1.5, False), (3.0, False), (999.0, False)]
    )
    min_comps: int = 6
    max_age_years: float = 3.0
    distance_offset_mi: float = 0.2
    size_elasticity: dict = field(default_factory=lambda: {"condo": 0.50})
    blend_k: float = 0.0  # 0 keeps the ring fallback; above 0 blends n / (n + k)
    prior_radius_mi: float = 3.0
    index_levels: tuple = ("metro",)
    condo_to_building: float = 1.0  # condo comp price per unit x this, for whole-building estimates
    band: dict = field(default_factory=dict)  # {"ring|kind": [q10, q90]}

    @classmethod
    def from_rules(cls, sale_comps: dict, band: dict | None = None) -> "Params":
        m = sale_comps["method"]
        return cls(
            min_comps=m["min_comps"],
            max_age_years=m["max_age_years"],
            distance_offset_mi=m["distance_offset_mi"],
            size_elasticity=m["size_elasticity"],
            blend_k=m["blend_k"],
            condo_to_building=m.get("condo_to_building", 1.0),
            index_levels=tuple(m["time_index_levels"]),
            band={k: v[:2] for k, v in (band or {}).get("band", {}).items()},
        )


@dataclass
class Estimate:
    per_unit: float
    low: float | None
    high: float | None
    ring: int
    radius_mi: float
    same_group: bool
    n: int
    n_local: int
    local_weight: float
    index_used: dict
    comps: list[tuple[Comp, float, float]]  # comp, adjusted value, weight
    notes: list[str]


def miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return math.hypot((lat1 - lat2) * MILES_PER_DEG_LAT, (lon1 - lon2) * MILES_PER_DEG_LAT * COS_LAT)


def group(units: int) -> str:
    return "2" if units == 2 else ("3" if units == 3 else "4-6")


class Index:
    """FHFA index lookup: (kind, geo_id, year) -> value; the metro series is averaged by year."""

    def __init__(self, rows: Iterable[tuple[str, str, int, int, float]]):
        self.v: dict[tuple[str, str, int], float] = {}
        metro: dict[tuple[str, int], list[float]] = {}
        for kind, geo, year, quarter, hpi in rows:
            if kind == "metro":
                metro.setdefault((geo, year), []).append(float(hpi))
            else:
                self.v[(kind, geo, year)] = float(hpi)
        for (geo, year), vals in metro.items():
            self.v[("metro", geo, year)] = sum(vals) / len(vals)
        self.last_year = {k: max(y for kk, _, y in self.v if kk == k) for k in {k for k, _, _ in self.v}}

    def factor(self, comp: Comp, to_year: int, levels=("tract", "zip", "metro")) -> tuple[float, str]:
        for kind, geo in (("tract", comp.tract), ("zip", comp.zip), ("metro", METRO)):
            if not geo or kind not in levels:
                continue
            y_to = min(to_year, self.last_year.get(kind, to_year))
            a = self.v.get((kind, geo, comp.sale_date.year))
            b = self.v.get((kind, geo, y_to))
            if a and b:
                return b / a, kind
        return 1.0, "none"


def weighted_quantile(vals: list[tuple[float, float]], q: float) -> float:
    vals = sorted(vals)
    total = sum(w for _, w in vals)
    acc = 0.0
    for v, w in vals:
        acc += w
        if acc >= total * q - 1e-12:
            return v
    return vals[-1][0]


def _adjusted(t: Target, c: Comp, p: Params, index: Index | None) -> tuple[float, str]:
    v = c.price_per_unit
    kind = "none"
    if index is not None:
        f, kind = index.factor(c, t.as_of.year, p.index_levels)
        v *= f
    if c.kind == "condo" and t.kind is None:
        v *= p.condo_to_building
    e = p.size_elasticity.get(c.kind, 0)
    if e and t.sqft_per_unit and c.sqft_per_unit:
        v *= (t.sqft_per_unit / c.sqft_per_unit) ** e
    return v, kind


def estimate(
    t: Target,
    pool: list[Comp],
    p: Params,
    index: Index | None = None,
    exclude: Callable[[Comp], bool] | None = None,
) -> Estimate | None:
    max_days = p.max_age_years * 365.25
    cand = []
    for c in pool:
        if exclude and exclude(c):
            continue
        if t.kind and c.kind != t.kind:
            continue
        age = (t.as_of - c.sale_date).days
        if age < 0 or age > max_days:
            continue
        cand.append((c, miles(t.lat, t.lon, c.lat, c.lon)))
    if not cand:
        return None
    g = group(t.units)

    def ring_members(radius: float, same: bool):
        return [(c, d) for c, d in cand if d <= radius and (not same or group(c.units) == g)]

    def median(members):
        vals = []
        used = {}
        for c, d in members:
            v, k = _adjusted(t, c, p, index)
            vals.append((c, v, 1 / (p.distance_offset_mi + d)))
            used[k] = used.get(k, 0) + 1
        return weighted_quantile([(v, w) for _, v, w in vals], 0.5), vals, used

    ring_i, members = len(p.rings) - 1, cand
    for i, (radius, same) in enumerate(p.rings):
        m = ring_members(radius, same)
        if len(m) >= p.min_comps:
            ring_i, members = i, m
            break
    central, vals, used = median(members)
    notes = []
    local = ring_members(*p.rings[0])
    n_local = len(local)
    w_local = 1.0 if ring_i == 0 else 0.0
    if p.blend_k > 0:
        # Empirical-Bayes style shrinkage: local median weighted n / (n + k) against the wider median.
        prior, _, _ = median(ring_members(p.prior_radius_mi, False) or cand)
        if n_local:
            local_med, _, _ = median(local)
            w_local = n_local / (n_local + p.blend_k)
            central = w_local * local_med + (1 - w_local) * prior
        else:
            w_local, central = 0.0, prior
        notes.append(
            f"{n_local} comp(s) of the same size group within {p.rings[0][0]} mi, weighted {w_local:.0%};"
            f" the rest from the {p.prior_radius_mi:g}-mile median"
        )
    radius, same = p.rings[ring_i]
    if radius > 3:
        notes.append("comps came from across the city; the range is wider")
    kind = t.kind or "building"  # no kind filter means a whole-building estimate
    band = next(
        (p.band[k] for k in (f"{ring_i}|{kind}", f"{ring_i}|any", f"any|{kind}", "any|any") if k in p.band),
        None,
    )
    low = high = None
    if band:
        low, high = central * (1 + band[0]), central * (1 + band[1])
    return Estimate(
        per_unit=central,
        low=low,
        high=high,
        ring=ring_i,
        radius_mi=radius,
        same_group=same,
        n=len(members),
        n_local=n_local,
        local_weight=w_local,
        index_used=used,
        comps=vals,
        notes=notes,
    )


def pool_from_db(conn) -> list[Comp]:
    """Kept comps from the `comp` table (jobs/build_comps.py); price per unit and sq ft per unit."""
    rows = conn.execute(
        """select sale_row_id, pin, kind, building_id, sale_date, price_per_unit, units,
                  case when kind = 'building' then sqft / units else sqft end,
                  st_y(geom), st_x(geom), tract_geoid, zip, nbhd_code, community_area
           from comp where excluded is null and geom is not null"""
    ).fetchall()
    return [Comp(r[0], r[1], r[2], r[3], r[4], float(r[5]), r[6], float(r[7]) if r[7] else None,
                 r[8], r[9], r[10], r[11], r[12], r[13]) for r in rows]  # fmt: skip


def index_from_db(conn) -> Index:
    return Index(conn.execute("select geo_kind, geo_id, year, quarter, hpi from hpi").fetchall())


def params_from_files() -> Params:
    defaults = json.loads((RULES_DIR / "feasibility_defaults.json").read_text())
    band = RULES_DIR / "sale_band.json"
    return Params.from_rules(defaults["sale_comps"], json.loads(band.read_text()) if band.exists() else None)
