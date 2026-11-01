"""Feasibility: what a scenario costs, what it sells or rents for, and what land price it supports.

Pure functions over inputs the caller loads (zoning result, sale value, rent, land value, cost index), so the
nightly scorer and the live screen give the same answer. Formulas: docs/v1-spec.md, Feasibility math, with the
changes in docs/research/decisions-2026-10-30.md. Every number carries its basis; nothing here recommends.
"""

import math
import random
from dataclasses import dataclass, field

from engine.costs import Cost, cost, unit_size
from engine.zoning import Path, Result


@dataclass
class Inputs:
    """Everything a scenario needs that is not a rule default. All overridable per deal."""

    units: int
    sale_per_unit: float | None = None  # central estimate
    sale_low_mult: float | None = None  # 80% range as multipliers of central
    sale_high_mult: float | None = None
    sale_comps: int | None = None
    rent_per_unit: float | None = None  # monthly
    rent_low_mult: float | None = None
    rent_high_mult: float | None = None
    land: float = 0.0
    land_basis: str = "entered"
    cost_index: float | None = None
    cost_index_thin: bool = False
    lot_sqft: float | None = None
    far: float | None = None
    gross_sqft: float | None = None  # pattern gross area; capped by lot x FAR
    unit_sqft: float | None = None
    preset: str | None = None
    rezoning: bool = False
    stage: str = "feasibility"
    commercial_sqft: float = 0.0
    in_enterprise_zone: bool = False
    in_opportunity_zone: bool = False
    in_tif: bool = False
    toggles: dict = field(default_factory=dict)  # incentive id -> on/off
    answers: dict = field(default_factory=dict)  # eligibility answers
    existing_use_value: float | None = None
    escalation: float = 1.0  # preset x this (Census under-construction index to the build midpoint)
    seed: int = 25125
    draws: int = 10_000


def _lognormal_sigma(low_mult: float, high_mult: float) -> tuple[float, float]:
    """Fit a lognormal to P10 and P90 multipliers: returns (mu, sigma) of log(multiplier)."""
    z = 1.2815515655446004
    lo, hi = math.log(low_mult), math.log(high_mult)
    return (lo + hi) / 2, (hi - lo) / (2 * z)


def osif(d: dict, units: int, unit_sqft: float, year: int) -> float:
    """Open Space Impact Fee per the 2024 ordinance; 2026 table by unit size."""
    o = d["open_space_impact_fee"]
    size = (
        "<800"
        if unit_sqft < 800
        else "800-1599"
        if unit_sqft < 1600
        else "1600-2999"
        if unit_sqft < 3000
        else "3000+"
    )
    persons = o["persons_by_unit_size"][size]
    rate = o["open_space_cost_per_sqft"].get(str(year)) or o["open_space_cost_per_sqft"]["2027"]
    return round(persons * 87 * rate * 0.30) * units


def incentives(d: dict, x: Inputs, c: Cost, exit_: str, hold_value: float | None) -> list[dict]:
    """Incentives at maximum value, each with its toggle; answers switch toggles off (incentive_questions.json)."""
    hold_years = x.answers.get("hold_years")
    out = []

    def add(id_, name, applies, value, basis, kind="cash", note=None):
        on = x.toggles.get(id_, applies)
        out.append({"id": id_, "name": name, "applies": applies, "on": bool(on and applies), "value": round(value) if applies else 0,
                    "basis": basis, "kind": kind, "note": note})  # fmt: skip

    ez_value = c.hard * 0.40 * 0.1025
    ez_ok = x.in_enterprise_zone and x.answers.get("materials_from_ez_supplier", True)
    add("ez", "Enterprise Zone materials sales tax exemption", ez_ok, ez_value,
        "10.25% sales tax on about 40% of hard cost (materials)", "cash",
        "confirm residential eligibility; buy through an Enterprise Zone certificate")  # fmt: skip
    if exit_ == "sell":
        add("bonus", "Bonus depreciation (tax deferred)", False, 0, "Applies only if you hold", "deferral")
        add(
            "oz",
            "Opportunity Zone gain exclusion",
            False,
            0,
            "Needs a 10-year hold; a sale at 18 months gets deferral only",
            "tax",
        )
    else:
        add("bonus", "Bonus depreciation (tax deferred)", True, c.hard * 0.25 * 0.37,
            "25% of hard cost in short-life property, at a 37% tax rate; timing value, shown apart from profit",
            "deferral")  # fmt: skip
        oz_ok = (
            x.in_opportunity_zone
            and x.answers.get("has_capital_gains", True)
            and (hold_years is None or hold_years >= 10)
        )
        gain = max(0.0, (hold_value or 0) - c.total)
        add("oz", "Opportunity Zone gain exclusion", oz_ok, gain * 0.238,
            "23.8% of value created, if the tract qualifies, you invest capital gains and hold 10 years", "tax",
            "2018 tract list valid through 2028; the 2027 list is not yet verified")  # fmt: skip
    commercial = x.commercial_sqft > 0 or x.answers.get("has_commercial_space")
    add("tif_sbif", "TIF Small Business Improvement Fund", bool(x.in_tif and commercial), 0,
        "Flag only: commercial space in an active TIF district", "flag")  # fmt: skip
    add("class_7", "Cook County Class 7a/7b/8", bool(commercial), 0,
        "Flag only: commercial assessed level 25% to 10% for 10 years; needs a city resolution", "flag")  # fmt: skip
    add("missing_middle", "Missing Middle program", False, 0,
        "City-owned lot in a Missing Middle round: grant up to $150,000 per unit at completion, sale price capped",
        "flag", "owner-occupant buyers required; price cap replaces the comp value when selected")  # fmt: skip
    return out


def scenario(
    d: dict, x: Inputs, exit_: str = "sell", name: str = "", approval: str = "", year: int = 2026
) -> dict:
    """Price one scenario. `exit_` is 'sell' or 'hold'."""
    size = x.unit_sqft or unit_size(d, x.units)
    fee = osif(d, x.units, size, year)
    lot_far_cap = x.lot_sqft * x.far if x.lot_sqft and x.far else None
    gross = x.gross_sqft
    if gross is None:
        gross = x.units * size * d["circulation_factor"]
    if lot_far_cap:
        gross = min(gross, lot_far_cap)
    # Enterprise Zone savings come off hard cost before financing (decision 39) when on.
    c0 = _cost(d, x, gross, fee, 0.0)
    inc0 = incentives(d, x, c0, exit_, None)
    ez = next(i for i in inc0 if i["id"] == "ez")
    savings = ez["value"] if ez["on"] else 0.0
    c = _cost(d, x, gross, fee, savings)

    out = {"name": name, "approval": approval, "units": x.units, "exit": exit_, "gross_sqft": round(gross),
           "unit_sqft": round(size), "cost": c.to_dict(), "lines": _lines(d, x, c, fee)}  # fmt: skip
    out["cost_range"] = {"central": round(c.total), "low": round(c.low), "high": round(c.high),
                         "low_margin": round(c.low - c.total), "high_margin": round(c.high - c.total),
                         "label": "high case is about P90 (AACE ranges); land carries no margin"}  # fmt: skip
    out["cost_per_unit"] = round(c.total / x.units)

    if exit_ == "sell":
        out["sell"] = _sell(d, x, c)
        hold_value = None
    else:
        out["hold"] = _hold(d, x, c)
        hold_value = out["hold"]["value"]
    inc = incentives(d, x, c, exit_, hold_value)
    out["incentives"] = inc
    out["incentive_total"] = sum(i["value"] for i in inc if i["on"])
    out["flags"] = code_flags(x.units, x.rezoning)
    out["buyer_financing"] = _buyer_financing(d, x, out)
    return out


def _cost(d, x: Inputs, gross: float, fee: float, savings: float) -> Cost:
    return cost(
        d, x.units, x.land, x.cost_index, gross, 1.0, x.preset, x.rezoning, x.stage, x.cost_index_thin,
        other_fees=fee, hard_cost_savings=savings, escalation=x.escalation,
    )  # fmt: skip


def _lines(d, x: Inputs, c: Cost, fee: float) -> list[dict]:
    m = d["margins_by_stage"][x.stage]
    adj = f" x {c.adjustment:.2f} area adjustment" if c.adjustment != 1 else ""
    lines = [
        ("land", "Land", x.land_basis + " · no margin applied", c.land),
        ("hard", "Hard cost", f"{c.gfa_sqft:,.0f} sq ft x ${c.base_per_sqft} ({c.preset} spec){adj}", c.hard),
        ("sprinklers", "Sprinkler system",
         "Required: building has 4+ units" if c.sprinklers else "Not required: no building over 3 units", c.sprinklers),
        ("contingency", "Contingency", "5% of hard cost", c.contingency),
        ("soft", "Soft cost", "22% of hard" + (" + $30,000 rezoning attorney and architect" if x.rezoning else ""), c.soft),
        ("permit", "Building permit", "City fee formula; construction factor $0.50 per sq ft is a placeholder", c.permit),
        ("osif", "Open Space Impact Fee", "2024 ordinance, 2026 rate by unit size", fee),
        ("financing", "Interest", "65% loan at 8%, 55% drawn over 12 months build, full over 6 months sell", c.financing),
        ("origination", "Loan fee", "1% of loan (placeholder until a lender quote)", c.origination),
        ("tax_insurance", "Tax and insurance while building", "1.5% a year for 18 months", c.tax_insurance),
    ]  # fmt: skip
    if c.hard_cost_savings:
        lines.insert(
            2,
            (
                "ez_savings",
                "Enterprise Zone materials tax saved",
                "10.25% x 40% of hard cost",
                -c.hard_cost_savings,
            ),
        )
    out = []
    for id_, name, basis, v in lines:
        margin = id_ != "land"
        out.append({"id": id_, "name": name, "basis": basis, "value": round(v),
                    "low": round(v * (1 + m["low"])) if margin else round(v),
                    "high": round(v * (1 + m["high"])) if margin else round(v)})  # fmt: skip
    return out


def max_land_price(net: float, c: Cost, target: float) -> float:
    """Exact residual: land L with net / total(L) = 1 + target, where total = (L + other pre-finance cost) x (1 + f)."""
    pre_ex_land = c.total / (1 + c.finance_share) - c.land
    return net / ((1 + target) * (1 + c.finance_share)) - pre_ex_land


def _sell(d, x: Inputs, c: Cost) -> dict:
    s = d["sell"]
    if not x.sale_per_unit:
        return {"missing": "no sale value: enter a sale price per unit"}
    gross = x.sale_per_unit * x.units
    net = gross * s["net_sale_factor"]
    profit = net - c.total
    target = s["target_return_on_cost"]
    lo_m, hi_m = x.sale_low_mult or 0.75, x.sale_high_mult or 1.25
    res = {
        "sale_per_unit": round(x.sale_per_unit), "sale_total": round(gross), "net_sale": round(net),
        "net_sale_basis": "sale x 0.94 (commission, closing and the seller's transfer tax share)",
        "sale_range": {"low": round(gross * lo_m), "high": round(gross * hi_m), "label": "80% range from tested errors",
                       "comps": x.sale_comps},
        "profit": round(profit), "return_on_cost": round(profit / c.total, 4), "margin_on_net_sale": round(profit / net, 4),
        "max_land_price": round(max_land_price(net, c, target)), "target_return_on_cost": target,
        "max_land_price_at": {f"{int(t * 100)}%": round(max_land_price(net, c, t)) for t in (0.15, 0.20, 0.25)},
        "reference_lines": {"return_on_cost": [0.15, 0.20, 0.25], "label": "reference lines, not a verdict"},
    }  # fmt: skip
    res["range"] = simulate(d, x, c, net_central=net, lo_m=lo_m, hi_m=hi_m)
    stress_net = gross * lo_m * s["net_sale_factor"]
    res["stress_case"] = {
        "profit": round(stress_net - c.high),
        "label": "stress case: low sale and high cost together",
    }
    if x.existing_use_value:
        res["existing_use_check"] = {
            "existing_use_value": round(x.existing_use_value),
            "gap": round(res["max_land_price"] - x.existing_use_value),
            "label": "max land price minus the Assessor's market value; the owner may want more than either",
        }
    return res


def _hold(d, x: Inputs, c: Cost) -> dict:
    h = d["hold"]
    if not x.rent_per_unit:
        return {"missing": "no rent: enter a monthly rent per unit"}
    egi = x.rent_per_unit * 12 * x.units * h["vacancy_factor"]
    noi_bt = egi * (1 - h["opex_ratio_before_tax"])
    t = h["property_tax"]["effective_tax_rate_default"]
    value = noi_bt / (h["cap_rate"] + t)
    tax = value * t
    noi = noi_bt - tax
    yoc = noi / c.total
    rt = h["reference_tests"]
    loan_dscr = noi / rt["dscr"] / _annual_constant(d["financing"]["rate"], 30)
    return {
        "rent_per_unit": round(x.rent_per_unit), "effective_gross_income": round(egi),
        "operating_costs_before_tax": round(egi - noi_bt), "property_tax": round(tax), "noi": round(noi),
        "value": round(value), "value_basis": f"NOI before tax / (cap {h['cap_rate']:.2%} + tax {t:.2%})",
        "yield_on_cost": round(yoc, 4), "equity_created": round(value - c.total),
        "spread_over_cap_rate_pts": round((yoc - h["cap_rate"]) * 100, 2),
        "loan_at_dscr": round(loan_dscr),
        "loan_at_dscr_basis": f"NOI / {rt['dscr']} DSCR / 30-year constant at {d['financing']['rate']:.0%}",
        "refinance_gap": round(c.total * d["financing"]["loan_to_cost"] - loan_dscr),
        "reference_lines": {"spread_over_cap_rate_pts": rt["spread_over_cap_rate_pts"], "dscr": rt["dscr"],
                            "label": "reference lines, not a verdict"},
        "rent_range": {"low": round(x.rent_per_unit * (x.rent_low_mult or 0.8)),
                       "high": round(x.rent_per_unit * (x.rent_high_mult or 1.2))},
    }  # fmt: skip


def _annual_constant(rate: float, years: int) -> float:
    r = rate / 12
    n = years * 12
    return 12 * r / (1 - (1 + r) ** -n)


def simulate(d, x: Inputs, c: Cost, net_central: float, lo_m: float, hi_m: float) -> dict:
    """Seeded Monte Carlo of profit: sale and cost multipliers lognormal (fit to their P10/P90), correlated."""
    rm = d["range_method"]
    rho = x.toggles.get("sale_cost_correlation", rm["sale_cost_correlation"])
    m = d["margins_by_stage"][x.stage]
    smu, ssig = _lognormal_sigma(lo_m, hi_m)
    cmu, csig = _lognormal_sigma(1 + m["low"], 1 + m["high"])
    rng = random.Random(x.seed)
    ex_land = c.total - c.land
    profits = []
    for _ in range(x.draws):
        z1, z2 = rng.gauss(0, 1), rng.gauss(0, 1)
        zc = rho * z1 + math.sqrt(1 - rho * rho) * z2
        sale = net_central * math.exp(smu + ssig * z1)
        cost_ = c.land + ex_land * math.exp(cmu + csig * zc)
        profits.append(sale - cost_)
    profits.sort()
    q = lambda p: round(profits[min(int(p * len(profits)), len(profits) - 1)])
    return {
        "p10": q(0.10), "p50": q(0.50), "p90": q(0.90),
        "loss_share": round(sum(p < 0 for p in profits) / len(profits), 3),
        "draws": x.draws, "seed": x.seed, "sale_cost_correlation": rho,
        "label": "profit range from 10,000 seeded draws of sale and cost; the same inputs give the same answer",
    }  # fmt: skip


def code_flags(units: int, rezoning: bool) -> list[dict]:
    f = []
    if units <= 3:
        f += [
            {"tag": "Saves", "text": "3 units or fewer: no sprinkler system required"},
            {"tag": "Saves", "text": "No building over 3 units: no Certificate of Occupancy needed"},
        ]
    else:
        f += [
            {"tag": "Adds cost", "text": f"{units} units: sprinkler system required (4+ units)"},
            {"tag": "Adds cost", "text": "Certificate of Occupancy required before move-in (4+ units)"},
            {"tag": "Adds cost", "text": "Ground-floor units must meet Fair Housing accessibility (Type B)"},
        ]
    if rezoning:
        f.append(
            {
                "tag": "Risk",
                "text": "Rezoning needs the alderperson and a community meeting; unit count is locked to filed plans",
            }
        )
        if units >= 10:
            f.append(
                {
                    "tag": "Adds cost",
                    "text": "10 or more units with a rezoning: Affordable Requirements Ordinance applies",
                }
            )
        else:
            f.append(
                {"tag": "Note", "text": f"{units} units stays under the 10-unit affordable housing trigger"}
            )
    if units >= 3:
        f.append({"tag": "Note", "text": "An Illinois-licensed architect must stamp drawings for 3+ units"})
    f.append(
        {
            "tag": "Verify",
            "text": "Code thresholds are from the 2019 Chicago code; check against the 2026 text",
        }
    )
    return f


def _buyer_financing(d, x: Inputs, out: dict) -> dict:
    b = d["sell"]["buyer_financing"]
    if x.units <= 4:
        limit = b["residential_owner_occupant"]["fha_limit_cook_2026"].get(str(x.units))
        price = out.get("sell", {}).get("sale_total")
        return {"class": "residential (2-4 units): owner-occupant loans, 3.5-5% down", "fha_limit": limit,
                "over_fha_limit": bool(limit and price and price > limit)}  # fmt: skip
    return {"class": "commercial (5+ units): commercial loan and appraisal"}


def pattern_fits(pattern: dict, path: Path, lot_sqft: float | None) -> tuple[bool, str]:
    """A pattern fits a zoning path when its units, floor area and height are within the path's limits."""
    if pattern["units"] > path.units:
        return False, f"{pattern['units']} units > {path.units} allowed"
    if path.floor_area_sqft and pattern["gross_sqft"] > path.floor_area_sqft * 1.001:
        return False, f"{pattern['gross_sqft']:,} sq ft > {path.floor_area_sqft:,.0f} allowed"
    if path.max_height_ft and pattern["stories"] * 11 + 4 > path.max_height_ft:
        return False, f"{pattern['stories']} stories may exceed {path.max_height_ft:.0f} ft"
    if pattern.get("commercial_sqft") and not path.district.startswith("B/C"):
        return False, "commercial space needs a B or C district"
    return True, "fits"


def scenarios_for(zoning: Result, patterns: list[dict]) -> list[dict]:
    """Default A/B/C scenarios: the largest fitting pattern by right, the best other path, the rezoning path.

    Each entry: path, pattern (or None for a custom program sized to the path), and why.
    """
    by_id = {p.id: p for p in zoning.paths}
    picks = []

    def best(path: Path) -> dict | None:
        fits = [(pt, pattern_fits(pt, path, zoning.lot_sqft)) for pt in patterns]
        ok = [pt for pt, (f, _) in fits if f]
        return max(ok, key=lambda pt: (pt["units"], pt["gross_sqft"])) if ok else None

    order = ["by_right", "rs3_two_flat", "admin_adjustment", "adu", "rezoning"]
    for pid in order:
        if pid not in by_id or len(picks) >= 3:
            continue
        path = by_id[pid]
        target = min(path.units, 6)  # version 1 prices 2-6 unit buildings
        if target < 2 or any(p["units"] == target for p in picks):
            continue
        pt = best(path)
        if pt and pt["units"] == target:
            picks.append({"path": path, "pattern": pt["id"], "units": target, "gross_sqft": pt["gross_sqft"],
                          "unit_sqft": pt["unit_sqft"], "commercial_sqft": pt.get("commercial_sqft", 0)})  # fmt: skip
            continue
        # No pattern fits the path's unit count: a custom program at that count, sized to the floor area allowed.
        size = 1300 if target == 2 else 1200 if target == 3 else 1000
        gross = target * size * 1.12
        if path.floor_area_sqft:
            gross = min(gross, path.floor_area_sqft)
        picks.append({"path": path, "pattern": None, "units": target, "gross_sqft": round(gross),
                      "unit_sqft": round(gross / 1.12 / target), "commercial_sqft": 0})  # fmt: skip
    return picks
