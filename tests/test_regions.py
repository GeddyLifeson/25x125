"""Regions outside Chicago: every region folder loads, and the shared engine prices a lot from its rules."""

import csv
import json

import pytest

from core import region
from core.settings import settings
from engine.costs import cost
from engine.feasibility import pattern_fits, scenarios_for
from engine.rules import Rules
from engine.zoning import Site, evaluate
from jobs import load_fl_dor

OTHERS = [r for r in region.all_ids() if r != "chicago"]


@pytest.fixture
def in_region(monkeypatch):
    def switch(rid: str):
        monkeypatch.setattr(settings, "region", rid)
        return region.current()

    return switch


def test_chicago_is_the_default_and_keeps_its_pin_rules():
    assert region.region_id() == "chicago" and region.is_chicago()
    assert region.lot_id("13361010280000") == "1336101028"
    assert region.clean_parcel_id("13-36-101-028-0000") == "13361010280000"
    assert region.clean_parcel_id("172725001000000187000U") is None
    assert region.rules_json("feasibility_defaults.json")["build_spec_presets"]["production"]["2-3"] == 155


@pytest.mark.parametrize("rid", OTHERS)
def test_region_folder_is_complete(rid, in_region):
    r = in_region(rid)
    assert r["id"] == rid and r["state"] in region.STATE_FIPS and r["counties"]
    assert r["zoning_layer"]["zone_field"] and (r["zoning_layer"].get("url") or r["zoning_layer"].get("urls"))
    assert r["price_basis"] in ("recorded sales", "appraisal district values")
    rules = Rules.from_files()
    assert rules.districts
    for row in csv.DictReader(region.rules_file("zoning_districts.csv").open(encoding="utf-8")):
        assert row["source_url"].startswith("http") and row["verified_on"], row["district"]
    targets = (rules.steps.get("rezoning") or {}).get("targets", {})
    assert all(t in rules.districts for ts in targets.values() for t in ts)
    d = region.rules_json("feasibility_defaults.json")
    assert d["chicago_rules"] is False and d["build_spec_presets"]["production"]["1"] > 0
    assert d["financing"]["rate"] > 0  # inherited from the Chicago file


@pytest.mark.parametrize("rid", OTHERS)
def test_region_parcel_ids_and_single_house(rid, in_region):
    in_region(rid)
    assert region.lot_id("172725001000000187000U") == "172725001000000187000U"
    assert region.clean_parcel_id(" 0660080070 ") == "0660080070"
    rules = Rules.from_files()
    d = next(iter(rules.districts.values()))
    z = evaluate(Site(pin="X1", zone_class=d.match[0], lot_sqft=200000, frontage_ft=300), rules)
    by_right = next(p for p in z.paths if p.id == "by_right")
    assert by_right.units >= 1
    patterns = region.rules_json("building_patterns.json")["patterns"]
    picks = scenarios_for(z, patterns)
    assert picks and picks[0]["units"] >= 1


def test_shared_overlay_and_patterns(in_region):
    in_region("tampa")
    d = region.rules_json("feasibility_defaults.json")
    one = cost(d, 1, land=100000, lot_sqft=None, far=None)
    assert one.base_per_sqft == 162 and one.sprinklers == 0
    assert cost(d, 3, land=0).sprinklers > 0 and cost(d, 2, land=0).sprinklers == 0
    patterns = {p["id"]: p for p in region.rules_json("building_patterns.json")["patterns"]}

    class P:
        id, units, floor_area_sqft, max_height_ft, district = "by_right", 2, None, 35, "RS-50"

    assert pattern_fits(patterns["house-adu"], P, 6000)[0] is False  # only on the ADU path
    assert pattern_fits(patterns["duplex"], P, 6000)[0] is True


def test_far_only_district_gets_units_from_floor_area(in_region):
    in_region("atlanta")
    rules = Rules.from_files()
    far_only = [d for d in rules.districts.values() if not d.lot_area_per_unit_sqft and d.far]
    assert far_only
    d = far_only[0]
    z = evaluate(Site(pin="X1", zone_class=d.match[0], lot_sqft=20000, frontage_ft=100), rules)
    by_right = next(p for p in z.paths if p.id == "by_right")
    assert by_right.units == int(20000 * d.far // 1100) or by_right.units == d.max_units


def test_florida_roll_row_to_sales_and_use_group():
    row = {"SALE_PRC1": "450000", "SALE_YR1": "2026", "SALE_MO1": "3", "QUAL_CD1": "1", "VI_CD1": "I",
           "OR_BOOK1": "100", "OR_PAGE1": "20", "SALE_PRC2": "90000", "SALE_YR2": "2025", "SALE_MO2": "11",
           "QUAL_CD2": "05", "VI_CD2": "V", "MULTI_PAR_SAL2": ""}  # fmt: skip
    s = list(load_fl_dor.sales_of(row))
    assert s[0][1:] == ("2026-03-01", 450000.0, "book 100 page 20", "01", False, False)
    assert s[1][4:] == ("05", True, True)  # code 05 is a multi-parcel sale; vacant when sold
    assert [load_fl_dor.use_group(c) for c in ("000", "001", "8", "004", "011")] == [
        "vacant", "single", "multi", "condo", "other"]  # fmt: skip
    county = {
        "dor_name": "Hillsborough",
        "dor_county_no": 39,
        "shape_name": "hillsborough",
        "tax_auth_codes": ["TA"],
    }
    assert load_fl_dor.nal_url(county, "2026F").endswith("NAL/2026F/Hillsborough 39 Final NAL 2026.zip")
    assert load_fl_dor.shapes_url(county, "2026F").endswith("2026F PIN/hillsborough_2026pin.zip")
    assert load_fl_dor.in_region({"TAX_AUTH_CD": "TA", "PHY_CITY": "X"}, county, set())
    assert not load_fl_dor.in_region({"TAX_AUTH_CD": "U", "PHY_CITY": "TAMPA"}, county, {"TAMPA"})


def test_rules_json_layers(tmp_path, monkeypatch):
    monkeypatch.setattr(region, "RULES_DIR", tmp_path / "rules")
    monkeypatch.setattr(region, "SHARED_DIR", tmp_path / "shared")
    monkeypatch.setattr(region, "REGIONS_DIR", tmp_path / "regions")
    for folder, data in (("rules", {"a": {"x": 1, "y": 2}, "b": 1}), ("shared", {"extends": True, "a": {"y": 3}}),
                         ("regions/z/rules", {"extends": True, "b": 9})):  # fmt: skip
        (tmp_path / folder).mkdir(parents=True)
        (tmp_path / folder / "f.json").write_text(json.dumps(data))
    assert region.rules_json("f.json", "chicago") == {"a": {"x": 1, "y": 2}, "b": 1}
    out = region.rules_json("f.json", "z")
    assert out["a"] == {"x": 1, "y": 3} and out["b"] == 9


def test_arcgis_parcel_rows():
    from jobs import load_arcgis_parcels as lap

    layer = {"tax_year": 2026, "use_groups": {"A1": "single", "B": "multi", "C1": "vacant"}, "units_by_use": {"B2": 2},
             "fields": {"id": "TAX_ID", "address": "ADDR", "zip": "ZIP", "use_code": "CLS", "market_value": "MKT",
                        "land_value": "LAND", "year_built": "YR", "living_sqft": "SQFT", "land_acres": "AC"}}  # fmt: skip
    square = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}
    page = [
        {"properties": {"TAX_ID": "001", "ADDR": "12 main st", "ZIP": "77002", "CLS": "B2", "MKT": 500000.0,
                        "LAND": 90000, "YR": "2021", "SQFT": "2400", "AC": 0.1}, "geometry": square},
        {"properties": {"TAX_ID": 2.0, "ADDR": "14 MAIN ST", "CLS": "C1", "MKT": 80000, "LAND": 80000}, "geometry": None},
        {"properties": {"TAX_ID": None}, "geometry": square},
    ]  # fmt: skip
    rows = lap.rows_of(page, layer, {"id": "houston"}, 7)
    assert [p[0] for p in rows["parcel"]] == ["001", "2"]
    assert rows["parcel"][0][9] == "multi" and rows["parcel"][1][9] == "vacant"
    assert rows["building"] == [("001", "001", 2026, 1, "B2", 2, 2400, 4356, 2021, 7)]
    assert rows["value"][0][6:8] == (500000.0, 90000.0) and len(rows["shape"]) == 1
    assert lap.group_for("a3", {"A": "single", "A3": "condo"}) == "condo"
    units = {**layer, "use_from_units": True, "fields": {**layer["fields"], "units": "U"}}
    out = lap.rows_of([{"properties": {"TAX_ID": "9", "CLS": "R3", "U": 0}, "geometry": None},
                       {"properties": {"TAX_ID": "8", "CLS": "R3", "U": 3}, "geometry": None},
                       {"properties": {"TAX_ID": "7", "CLS": "C4", "U": 0}, "geometry": None}], units, {"id": "atlanta"}, 1)  # fmt: skip
    assert [p[9] for p in out["parcel"]] == ["vacant", "multi", "other"]


def test_dcad_files(tmp_path):
    from jobs import load_dcad

    files = {
        "ACCOUNT_APPRL_YEAR.CSV": 'ACCOUNT_NUM,APPRAISAL_YR,LAND_VAL,TOT_VAL,CITY_JURIS_DESC,SPTD_CODE\n'
                                  '"A1","2026","50000.00","400000.00","DALLAS","A11"\n"A2","2026","1","2","IRVING","A11"\n',
        "ACCOUNT_INFO.CSV": "ACCOUNT_NUM,STREET_NUM,FULL_STREET_NAME,UNIT_ID,PROPERTY_ZIPCODE,NBHD_CD\n"
                            '"A1","12","elm st","","752011234","1DSA"\n',
        "RES_DETAIL.CSV": "ACCOUNT_NUM,YR_BUILT,TOT_LIVING_AREA_SF,NUM_UNITS\n"
                          '"A1","2020","1500","1"\n"A1","2022","600","1"\n',
        "LAND.CSV": 'ACCOUNT_NUM,AREA_SIZE,AREA_UOM_DESC\n"A1","7000.000","SQUARE FEET"\n"A1","0.1","ACRE"\n',
    }  # fmt: skip
    for name, body in files.items():
        (tmp_path / name).write_text(body)
    acct = load_dcad.read(tmp_path, {"DALLAS"})
    assert list(acct) == ["A1"]
    a = acct["A1"]
    assert (a["market"], a["land"], a["living"], a["units"], a["built"]) == (400000.0, 50000.0, 2100, 2, 2022)
    assert a["address"] == "12 ELM ST" and a["zip"] == "75201" and round(a["land_sqft"]) == 11356


def test_tcad_fixed_width_row():
    from jobs import load_tcad

    line = [" "] * 5000

    def put(start, text):
        line[start - 1 : start - 1 + len(text)] = text

    put(1, "000000100022")
    put(13, "R")
    put(18, "02026")
    put(1050, "LAMAR")
    put(1100, "BLVD")
    put(1140, "78704")
    put(1686, "SC")
    put(1811, "000000001687500")
    put(2732, "A1")
    put(4214, "00000001703397")
    put(4460, "1105")
    pid, row = load_tcad.prop_row("".join(line))
    assert pid == "100022" and row["year"] == 2026 and row["use"] == "A1"
    assert row["market"] == 1703397.0 and row["land"] == 1687500.0
    assert row["address"] == "1105 LAMAR BLVD" and row["zip"] == "78704" and row["nbhd"] == "SC"
    put(13, "P")
    assert load_tcad.prop_row("".join(line)) is None


def test_florida_countywide_comps_only_newer_homes():
    from jobs import load_fl_dor

    county = {"tax_auth_prefixes": ["01"], "comps_countywide": {"built_since": 2014}}
    assert load_fl_dor.in_region({"TAX_AUTH_CD": "0100", "DOR_UC": "017"}, county, set())
    outside = {"TAX_AUTH_CD": "2200", "DOR_UC": "001", "ACT_YR_BLT": "2020", "NO_RES_UNTS": "1"}
    assert load_fl_dor.in_region(outside, county, set())
    assert not load_fl_dor.in_region({**outside, "ACT_YR_BLT": "1990"}, county, set())
    assert not load_fl_dor.in_region({**outside, "DOR_UC": "000"}, county, set())
    assert not load_fl_dor.in_region({**outside, "NO_RES_UNTS": "12"}, county, set())
    assert not load_fl_dor.in_region(outside, {"tax_auth_prefixes": ["01"]}, set())


def test_city_step_paths_orlando(in_region):
    from engine import zoning
    from engine.rules import Rules

    in_region("orlando")
    rules = Rules.from_files()
    d = rules.district_for("R-2B")
    assert d is not None and d.lot_area_per_unit_sqft
    big = zoning._step_paths(
        zoning.Site(pin="1", zone_class="R-2B", lot_sqft=20000, frontage_ft=60), rules, d, 20000
    )
    ids = {p.id: p.units for p in big}
    assert ids["duplex_lot"] == 2 and 3 <= ids["multiplex"] <= 5
    small = zoning._step_paths(
        zoning.Site(pin="1", zone_class="R-2B", lot_sqft=4000, frontage_ft=40), rules, d, 4000
    )
    assert "duplex_lot" not in {p.id for p in small}


def test_city_step_paths_austin_home(in_region):
    from engine import zoning
    from engine.rules import Rules

    in_region("austin")
    rules = Rules.from_files()
    d = rules.district_for("SF-3")
    site = zoning.Site(pin="1", zone_class="SF-3", lot_sqft=6000, frontage_ft=50)
    assert {p.id: p.units for p in zoning._step_paths(site, rules, d, 6000)}["home_two_and_three_units"] == 3
    assert not zoning._step_paths(zoning.Site(pin="1", zone_class="SF-3", lot_sqft=5000), rules, d, 5000)
