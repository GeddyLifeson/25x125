import json
from datetime import date

from engine.comps import RULES_DIR, Comp, Params, Target, estimate
from engine.parcel_feasibility import load_defaults, load_patterns
from engine.rules import Rules
from engine.sites import FIELDS
from jobs.score_parcels import score_lot

RULES = Rules.from_files()
W = json.loads((RULES_DIR / "development_score.json").read_text())
TODAY = date(2026, 11, 1)


def row(**kw):
    base = dict.fromkeys(FIELDS)
    base.update(
        pin="16012160310000",
        zone_class="RT-4",
        lot_sqft=3125.0,
        frontage_ft=25.0,
        use_now="vacant",
        units_now=0,
    )
    base.update(kw)
    return tuple(base[f] for f in FIELDS)


def ctx(**kw):
    c = {"pin10": "1601216031", "lat": 41.9, "lon": -87.7, "nbhd": None, "ca_num": 23, "enterprise_zone": None,
         "opportunity_zone": None, "tif": None, "environmental_hold": None, "open_violations": 0, "scofflaw": False, "demolition_notice_date": None,
         "vacant_building_2y": 0, "for_sale": False, "land_values": None, "cost_index": {"index": 1.0, "thin": False},
         "patterns": load_patterns(), "d": load_defaults(), "esc": {"factor": 1.0}}  # fmt: skip
    c.update(kw)
    return c


POOL = [Comp(str(i), "1", "building", str(i), date(2026, 6, 1), price, 3, 1200, 41.9 + i * 1e-4, -87.7)
        for i, price in enumerate([520_000, 540_000, 560_000, 580_000, 600_000, 620_000])]  # fmt: skip


def sale_for(lat, lon, units, unit_sqft):
    return estimate(Target(lat, lon, units, TODAY, unit_sqft), POOL, Params(band={"any|any": [-0.2, 0.2]}))


def test_vacant_rt4_lot_scores_every_part():
    s = score_lot(row(), W, RULES, ctx(for_sale=True), sale_for, [], TODAY)
    assert s["by_right_units"] == 3 and s["units_priced"] == 3
    assert s["zoning_upside"] == 30  # 3 extra units by right
    assert s["acquisition"] == 18 and set(s["details"]["signals"]) == {"city_owned_for_sale", "vacant_land"}
    assert s["location"] == 5  # 6 comps within 0.75 mi, not transit served
    assert s["profit_p25"] < s["profit_central"]
    assert (
        s["profit"] == 0 and "land priced at $0" in s["details"]["profit"]
    )  # no land sales: no profit points
    assert s["score"] == round(s["zoning_upside"] + s["profit"] + s["acquisition"] + s["location"]
                               + s["incentives"] + s["penalties"], 1)  # fmt: skip


def test_penalties_and_caps():
    s = score_lot(row(historic_rating="Orange", landmark_name="X", fire_limits=True, units_now=3, use_now="multi"),
                  W, RULES, ctx(open_violations=2, scofflaw=True, vacant_building_2y=1,
                                demolition_notice_date=date(2026, 1, 1), for_sale=True), sale_for, [], TODAY)  # fmt: skip
    assert s["zoning_upside"] == 0
    assert s["penalties"] == -20  # -30 capped at the floor
    assert s["acquisition"] == 20  # 32 capped at the part's max


def test_no_by_right_program_gets_no_profit_points():
    s = score_lot(row(zone_class="RS-1", lot_sqft=6000.0, frontage_ft=50.0, use_now="single", units_now=1),
                  W, RULES, ctx(), sale_for, [], TODAY)  # fmt: skip
    assert s.get("units_priced") is None and s["profit"] == 0 and "by right" in s["details"]["profit"]


def test_profit_points_with_a_land_price():
    lv = {"geo": "nbhd", "geo_id": "1", "sales": 9, "per_lot_sqft": 20.0, "per_buildable_sqft": 15.0,
          "first_sale": "2024-01-01", "last_sale": "2026-06-01"}  # fmt: skip
    s = score_lot(row(), W, RULES, ctx(land_values=lv), sale_for, [], TODAY)
    assert s["land"] == round(15.0 * 3125 * 1.2) and s["details"]["sale_ring"] == 0
    assert s["profit"] == round(min(max(s["return_on_cost_p25"] / 0.25, 0), 1) * 30, 1)


def test_fast_path():
    from engine.feasibility import fast_path
    from engine.zoning import Site, evaluate

    z = evaluate(Site("1", "RT-4", 3125, 25), RULES)
    assert fast_path(z, None, None, "vacant", None)["eligible"]
    assert not fast_path(z, "Wicker Park", None, "vacant", None)["eligible"]
    assert fast_path(z, None, "Orange", "vacant", None)["eligible"]  # nothing to demolish
    w = {"SELF CERT": {"permits": 372, "p25": 0, "median": 48.5, "p75": 94, "computed_on": "2026-10-30"}}
    assert not fast_path(z, None, "Orange", "multi", None, w)["eligible"]
    assert fast_path(z, None, None, "vacant", None, w)["weeks_to_permit"]["median"] == 7
    s = score_lot(row(), W, RULES, ctx(), sale_for, [], TODAY)
    assert s["details"]["fast_path"] is True
