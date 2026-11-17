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
