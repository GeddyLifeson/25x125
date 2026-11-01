import json
from pathlib import Path

from engine.costs import adjustment_for, cost, preset_for

D = json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "rules" / "feasibility_defaults.json").read_text()
)


def test_preset_and_adjustment_do_not_count_the_area_twice():
    assert preset_for(0.78) == "production" and adjustment_for("production", 0.78) == 1.0  # floored
    assert preset_for(1.94) == "high" and adjustment_for("high", 1.94) == 1.0
    assert adjustment_for("production", 1.29) == 1 + 0.5 * 0.29


def test_standard_3_flat_lines():
    c = cost(D, 3, 60_000, lot_sqft=3125, far=1.2, preset="production")
    assert c.gfa_sqft == 3750  # lot x FAR is smaller than 3 x 1,200 x 1.12
    assert c.hard == 3750 * 165 and c.sprinklers == 0 and c.permit == 2000
    pre = 60_000 + c.hard * (1 + 0.05 + 0.22) + 2000
    assert round(c.financing) == round(0.65 * pre * 0.08 * (0.55 + 0.5))
    assert round(c.tax_insurance) == round(0.015 * pre * 1.5)
    assert round(c.total) == round(pre + c.financing + c.origination + c.tax_insurance)
    assert round(c.high - c.land) == round((c.total - c.land) * 1.35)


def test_four_units_add_sprinklers_and_thin_index_widens():
    c = cost(D, 4, 0, index=1.0, thin_index=True)
    assert c.sprinklers == c.gfa_sqft * 5 and c.base_per_sqft == 170
    assert round(c.high) == round(c.total * (1 + 0.35 + 0.10))
