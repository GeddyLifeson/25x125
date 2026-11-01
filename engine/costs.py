"""Development cost for a 2-6 unit building, from data/rules/feasibility_defaults.json (docs/v1-spec.md,
Feasibility math and Cost model). Every line is returned so screens can show and override it.
"""

from dataclasses import asdict, dataclass


@dataclass
class Cost:
    gfa_sqft: float
    preset: str
    base_per_sqft: float
    adjustment: float
    land: float
    hard: float
    sprinklers: float
    contingency: float
    soft: float
    permit: float
    other_fees: float
    hard_cost_savings: float
    financing: float
    origination: float
    tax_insurance: float
    total: float
    finance_share: float
    low: float
    high: float
    stage: str

    def to_dict(self) -> dict:
        return {
            k: (round(v, 4) if k in ("adjustment", "finance_share") else round(v))
            if isinstance(v, float)
            else v
            for k, v in asdict(self).items()
        }


def unit_size(d: dict, units: int) -> float:
    s = d["unit_size_sqft"]
    return s["2"] if units == 2 else (s["3"] if units == 3 else s["4-6"])


def gfa(d: dict, units: int, lot_sqft: float | None = None, far: float | None = None) -> float:
    built = units * unit_size(d, units) * d["circulation_factor"]
    return min(built, lot_sqft * far) if lot_sqft and far else built


def preset_for(index: float | None) -> str:
    """Area cost index picks the preset: below 1.3 production, 1.3-1.8 standard, 1.8 and up high."""
    if index is None or index < 1.3:
        return "production"
    return "standard" if index < 1.8 else "high"


def adjustment_for(preset: str, index: float | None) -> float:
    """Production preset only: 1 + 0.5 x (min(index, 1.3) - 1); the other presets already reflect the area."""
    if preset != "production" or index is None:
        return 1.0
    return 1 + 0.5 * (min(index, 1.3) - 1)


def cost(
    d: dict,
    units: int,
    land: float,
    index: float | None = None,
    lot_sqft: float | None = None,
    far: float | None = None,
    preset: str | None = None,
    rezoning: bool = False,
    stage: str = "feasibility",
    thin_index: bool = False,
    other_fees: float = 0.0,
    hard_cost_savings: float = 0.0,
    escalation: float = 1.0,
) -> Cost:
    area = gfa(d, units, lot_sqft, far)
    preset = preset or preset_for(index)
    base = d["build_spec_presets"][preset]["2-3" if units <= 3 else "4-6"] * escalation
    adj = adjustment_for(preset, index)
    hard = area * base * adj
    sprinklers = area * d["sprinklers_per_sqft_at_4_plus_units"] if units >= 4 else 0.0
    contingency = d["hard_cost_contingency"] * hard
    soft = d["soft_cost_pct_of_hard"] * hard + (d["rezoning_soft_cost_add"] if rezoning else 0)
    pf = d["permit_fee"]
    scope = pf["scope_factor"]["3_or_fewer_units" if units <= 3 else "4_plus_units"]
    permit = max(scope["minimum"], area * pf["construction_factor_per_sqft"] * scope["factor"])
    pre = land + hard - hard_cost_savings + sprinklers + contingency + soft + permit + other_fees
    f = d["financing"]
    months = f["months_build"] + f["months_sell"]
    loan = f["loan_to_cost"] * pre
    interest = loan * f["rate"] * (f["months_build"] / 12 * f["avg_drawn"] + f["months_sell"] / 12)
    origination = loan * f.get("origination_fee_pct_of_loan", 0)
    tax_ins = f["tax_and_insurance_pct_cost_per_year"] * pre * months / 12
    total = pre + interest + origination + tax_ins
    m = d["margins_by_stage"][stage]
    widen = d["thin_data"]["extra_margin_points_when_thin"] if thin_index else 0
    ex_land = total - land
    finance_share = (interest + origination + tax_ins) / pre if pre else 0.0
    return Cost(
        gfa_sqft=area, preset=preset, base_per_sqft=base, adjustment=adj, land=land, hard=hard,
        sprinklers=sprinklers, contingency=contingency, soft=soft, permit=permit, other_fees=other_fees,
        hard_cost_savings=hard_cost_savings, financing=interest,
        origination=origination, tax_insurance=tax_ins, total=total, finance_share=finance_share,
        low=land + ex_land * (1 + m["low"] - widen), high=land + ex_land * (1 + m["high"] + widen), stage=stage,
    )  # fmt: skip
