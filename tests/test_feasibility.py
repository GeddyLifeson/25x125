import json
from pathlib import Path

from engine.feasibility import Inputs, osif, pattern_fits, scenario, scenarios_for
from engine.rules import Rules
from engine.zoning import Path as ZPath
from engine.zoning import Site, evaluate

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "data" / "rules" / "feasibility_defaults.json").read_text())
PATTERNS = json.loads((ROOT / "data" / "rules" / "building_patterns.json").read_text())["patterns"]


def three_flat(**kw) -> Inputs:
    base = {"units": 3, "sale_per_unit": 300_000, "sale_low_mult": 0.77, "sale_high_mult": 1.22, "rent_per_unit": 2_000,
                "land": 60_000, "cost_index": 0.78, "lot_sqft": 3125, "far": 1.2, "unit_sqft": 1116}  # fmt: skip
    return Inputs(**{**base, **kw})


def test_sell_profit_and_exact_residual():
    s = scenario(D, three_flat(), "sell")
    c, sell = s["cost"], s["sell"]
    assert sell["net_sale"] == round(900_000 * 0.94)
    assert sell["profit"] == round(900_000 * 0.94 - c["total"])
    # At the max land price the return on cost is exactly the target.
    x = three_flat(land=sell["max_land_price"])
    s2 = scenario(D, x, "sell")
    assert abs(s2["sell"]["return_on_cost"] - D["sell"]["target_return_on_cost"]) < 0.001


def test_margins_exclude_land_and_follow_the_stage():
    s = scenario(D, three_flat(), "sell")
    land = next(line for line in s["lines"] if line["id"] == "land")
    assert land["low"] == land["high"] == 60_000
    ex_land = s["cost"]["total"] - 60_000
    assert abs(s["cost_range"]["high"] - (60_000 + ex_land * 1.35)) <= 1


def test_monte_carlo_is_seeded_and_ordered():
    a = scenario(D, three_flat(), "sell")["sell"]["range"]
    b = scenario(D, three_flat(), "sell")["sell"]["range"]
    assert a == b and a["p10"] < a["p50"] < a["p90"] and 0 <= a["loss_share"] <= 1
    stress = scenario(D, three_flat(), "sell")["sell"]["stress_case"]["profit"]
    assert stress < a["p10"]  # the corner is worse than the 10th percentile


def test_hold_value_with_explicit_tax():
    h = scenario(D, three_flat(), "hold")["hold"]
    egi = 2_000 * 12 * 3 * 0.95
    noi_bt = egi * 0.70
    value = noi_bt / (0.0625 + 0.018)
    assert h["value"] == round(value) and h["property_tax"] == round(value * 0.018)
    assert h["noi"] == round(noi_bt - value * 0.018)


def test_incentives_sell_vs_hold_and_toggles():
    sell = {
        i["id"]: i
        for i in scenario(D, three_flat(in_enterprise_zone=True, in_opportunity_zone=True), "sell")[
            "incentives"
        ]
    }
    assert sell["oz"]["value"] == 0 and sell["bonus"]["value"] == 0 and sell["ez"]["on"]
    hold = {i["id"]: i for i in scenario(D, three_flat(in_opportunity_zone=True), "hold")["incentives"]}
    assert hold["bonus"]["kind"] == "deferral" and hold["bonus"]["value"] > 0
    off = {i["id"]: i for i in scenario(D, three_flat(in_opportunity_zone=True, answers={"has_capital_gains": False}),
                                         "hold")["incentives"]}  # fmt: skip
    assert not off["oz"]["on"]


def test_enterprise_zone_savings_lower_cost_before_financing():
    a = scenario(D, three_flat(), "sell")["cost"]["total"]
    b = scenario(D, three_flat(in_enterprise_zone=True), "sell")["cost"]["total"]
    assert b < a


def test_open_space_fee_by_unit_size():
    assert osif(D, 3, 1116, 2026) == 1044 * 3
    assert osif(D, 2, 700, 2026) == 522 * 2


def test_code_flags_at_four_units():
    texts = [f["text"] for f in scenario(D, three_flat(units=4, unit_sqft=1000), "sell")["flags"]]
    assert any("sprinkler system required" in t for t in texts)


def test_patterns_and_default_scenarios():
    rt4 = ZPath("by_right", "By right", "building permit", "RT-4", 3, 3750, 38, 3, 0)
    ok, _ = pattern_fits(next(p for p in PATTERNS if p["id"] == "three-flat"), rt4, 3125)
    assert ok
    z = evaluate(Site("1", "RT-4", 3072, 24), Rules.from_files())
    picks = scenarios_for(z, PATTERNS)
    assert picks[0]["units"] == 3 and picks[0]["gross_sqft"] <= 3072 * 1.2 + 1


def test_max_land_price_at_the_reference_targets():
    sell = scenario(D, three_flat(land=0), "sell")["sell"]
    at = sell["max_land_price_at"]
    assert sell["max_land_price"] == at["20%"] and at["15%"] > at["20%"] > at["25%"]
