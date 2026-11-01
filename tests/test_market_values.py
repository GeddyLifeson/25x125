import psycopg

from db.migrate import migrate
from jobs import load_assessed_values
from jobs.load_assessed_values import level_for, load_rules, to_row
from tests.test_loaders import FakeClient

RULES = load_rules()
ROW = {"pin": "17283310290000", "year": "2025", "class": "211", "township_code": "76", "nbhd": "76030",
       "mailed_bldg": "23969.0", "mailed_land": "17031.0", "mailed_tot": "41000.0",
       "certified_bldg": "23969.0", "certified_land": "17031.0", "certified_tot": "41000.0",
       "board_bldg": "19705.0", "board_land": "17031.0", "board_tot": "36736.0", "row_id": "172833102900002025"}  # fmt: skip


def test_levels_by_class():
    assert level_for("211", RULES) == (0.10, False)
    assert level_for("318", RULES) == (0.10, False)
    assert level_for("517", RULES) == (0.25, False)
    assert level_for("4-97", RULES) == (0.20, False)
    assert level_for("791", RULES) == (0.10, True)
    assert level_for("EX", RULES) == (None, False)
    assert level_for(None, RULES) == (None, False)


def test_row_takes_best_stage_and_divides_by_level():
    r = to_row(ROW, 7, RULES)
    assert r[:6] == ("17283310290000", "1728331029", 2025, "211", "76030", "board")
    assert r[8] == 36736.0 and r[11] == 367360 and r[12] == 170310
    mailed_only = {k: v for k, v in ROW.items() if not k.startswith(("board", "certified"))}
    assert to_row({**mailed_only, "year": "2026"}, 7, RULES)[5] == "mailed"
    assert to_row({**ROW, "class": "EX"}, 7, RULES)[11] is None
    assert to_row({"pin": "123", "board_tot": "1"}, 7, RULES) is None


def test_lot_rollup_prefers_final_values(db_url):
    migrate(db_url)
    unit2 = {**ROW, "pin": "17283310291001", "board_tot": "10000.0", "board_land": "1000.0"}
    newer = {k: v for k, v in ROW.items() if not k.startswith(("board", "certified"))} | {"year": "2026"}
    client = FakeClient([[ROW, unit2, newer]])
    assert load_assessed_values.run(client=client, url=db_url, tax_years=["2025", "2026"]) == 3
    with psycopg.connect(db_url) as conn:
        lot = conn.execute(
            "select tax_year, stages, pins, market_value from lot_market_value where pin10 = '1728331029'"
        ).fetchone()
    assert lot == (2025, "board", 2, 467360)
