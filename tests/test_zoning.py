import psycopg
from fastapi.testclient import TestClient

import engine.app as app_module
from db.migrate import migrate
from engine.rules import Rules
from engine.zoning import Site, evaluate
from jobs import seed_rules

RULES = Rules.from_files()


def paths(res) -> dict:
    return {p.id: p for p in res.paths}


def test_rt4_standard_lot():
    res = evaluate(Site("1", "RT-4", 3125, 25), RULES)
    p = paths(res)
    assert (
        p["by_right"].units == 3
        and p["by_right"].floor_area_sqft == 3750
        and p["by_right"].max_height_ft == 38
    )
    assert p["by_right"].parking_spaces == 3
    assert "admin_adjustment" not in p  # 3125 / 900 still gives 3
    assert p["adu"].units == 4
    assert p["rezoning"].district == "RM-5" and p["rezoning"].units == 7 and p["rezoning"].max_height_ft == 45


def test_admin_adjustment_adds_a_unit_on_a_short_lot():
    p = paths(evaluate(Site("1", "RT-4", 2946, 24), RULES))
    assert p["by_right"].units == 2
    assert p["admin_adjustment"].units == 3 and p["admin_adjustment"].max_height_ft == 41.8


def test_rs3_block_face_test_at_60_percent():
    base = {"pin": "1", "zone_class": "RS-3", "lot_sqft": 3125, "frontage_ft": 25, "block_lots": 10}
    yes = paths(evaluate(Site(**base, block_multi_lots=6), RULES))
    no = paths(evaluate(Site(**base, block_multi_lots=5), RULES))
    assert yes["rs3_two_flat"].units == 2 and "6 of 10" in yes["rs3_two_flat"].notes[0]
    assert "rs3_two_flat" not in no and no["by_right"].units == 1


def test_rs3_two_flat_in_the_606_district_without_block_data():
    s = Site("1", "RS-3", 3125, 25, special_district="Predominance of the Block (606) District")
    assert paths(evaluate(s, RULES))["rs3_two_flat"].units == 2


def test_rs3_outside_adu_zone_flags_no_adu_and_inside_adds_one():
    out = evaluate(Site("1", "RS-3", 5000, 40), RULES)
    inside = evaluate(Site("1", "RS-3", 5000, 40, adu_zone="Zone 6", adu_limits="No Limitations"), RULES)
    assert "no_adu" in {f.id for f in out.flags} and "adu" not in paths(out)
    assert paths(inside)["adu"].units == 3


def test_transit_served_drops_parking_and_b3_3_gets_bonus_tiers():
    res = evaluate(Site("1", "B3-3", 5000, 50, transit_served="CTA station"), RULES)
    p = paths(res)
    assert p["by_right"].units == 12 and p["by_right"].parking_spaces == 0 and p["by_right"].bike_spaces == 12
    assert p["by_right"].max_height_ft == 60  # 50 ft frontage, no ground-floor commercial
    assert [p[f"tsl_bonus_{n}"].units for n in (50, 75, 100)] == [14, 15, 16]
    assert p["rezoning"].name == "Rezone to B3-5"
    assert "ground_floor" in {f.id for f in res.flags}


def test_b2_allows_ground_floor_units_and_c3_does_not():
    assert "ground_floor" not in {f.id for f in evaluate(Site("1", "B2-3", 3125, 25), RULES).flags}
    c3 = [f.text for f in evaluate(Site("1", "C3-2", 3125, 25), RULES).flags if f.id == "ground_floor"]
    assert c3 and "not allowed" in c3[0]


def test_rm5_height_steps_up_at_32_ft_frontage():
    assert paths(evaluate(Site("1", "RM-5", 4000, 31), RULES))["by_right"].max_height_ft == 45
    assert paths(evaluate(Site("1", "RM-5", 4000, 32), RULES))["by_right"].max_height_ft == 47


def test_flags_and_uncovered_district():
    s = Site("1", "PD 30", 3125, 25, historic_rating="Orange", fire_limits=True,
             special_district="Multi-Unit Preservation (Pilsen) District", units_now=4)  # fmt: skip
    res = evaluate(s, RULES)
    flags = {f.id: f for f in res.flags}
    assert not res.covered and res.paths == []
    assert {"historic", "fire_limits", "demolition_surcharge", "not_covered"} <= set(flags)
    assert flags["demolition_surcharge"].dollars == 80_000  # 4 units x $20,000 beats $60,000


def test_seeded_rules_match_the_files(db_url):
    migrate(db_url)
    seed_rules.run(db_url)
    with psycopg.connect(db_url) as conn:
        from_db = Rules.from_db(conn)
    assert from_db.districts == RULES.districts
    assert len(from_db.heights) == len(RULES.heights) and from_db.steps == RULES.steps


def test_zoning_endpoint_rejects_bad_pin():
    assert TestClient(app_module.app).get("/parcels/12ab/zoning").status_code == 400
