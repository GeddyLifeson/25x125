import io

from jobs.load_rents import acs_rows, zori_rows

ACS = """GEO_ID|B25031_E001|B25031_M001|B25031_E002|B25031_M002|B25031_E003|B25031_M003|B25031_E004|B25031_M004|B25031_E005|B25031_M005|B25031_E006|B25031_M006|B25031_E007|B25031_M007
0100000US|1413|2|1248|5|1235|2|1407|2|1584|4|1957|9|2074|24
1400000US17031231200|1300|50|-666666666|-222222222|1100|90|1427|392|1704|307|-666666666|-222222222|-666666666|-222222222
860Z200US60651|1264|69|838|309|974|121|1200|71|1480|89|2199|286|1069|551
860Z200US10001|9|9|9|9|9|9|9|9|9|9|9|9|9|9
"""


def test_acs_rows_keep_illinois_and_drop_annotation_codes():
    rows = list(acs_rows(io.StringIO(ACS), "b25031", "2020-2024"))
    tract = {r[3]: r[4] for r in rows if r[0] == "tract"}
    assert tract == {"1": 1100, "2": 1427, "3": 1704}
    assert {r[1] for r in rows} == {"17031231200", "60651"}


def test_zori_rows_only_illinois():
    csv_text = "RegionID,SizeRank,RegionName,RegionType,StateName,State,2022-07-31,2026-09-30\n1,1,60651,zip,IL,IL,1306,1751\n2,2,10001,zip,NY,NY,4000,4200\n"
    rows = list(zori_rows(io.StringIO(csv_text)))
    assert [(z, m.isoformat(), v) for z, m, v in rows] == [
        ("60651", "2022-07-01", 1306),
        ("60651", "2026-09-01", 1751),
    ]


def test_acs_rows_for_a_region_keep_its_state_and_zip_prefixes():
    text = (
        ACS
        + "1400000US48201530200|2100|300|-666666666|-222222222|900|90|1200|100|2180|326|2500|400|2700|500\n"
    )
    text += "860Z200US77007|1900|100|800|90|1000|90|1300|90|1700|90|2100|90|2400|90\n"
    geo = {"state_fips": "48", "state": "TX", "zip_prefixes": ("770", "772")}
    rows = list(acs_rows(io.StringIO(text), "b25031", "2020-2024", geo))
    assert {r[1] for r in rows} == {"48201530200", "77007"}
    assert {r[3]: r[4] for r in rows if r[0] == "tract"}["3"] == 2180


def test_new_building_factor_from_census_years_built():
    from jobs.check_rents_acs import MIN_TRACTS, factor

    overall = {str(i): {"001": 1000} for i in range(40)}
    by_year = {str(i): {"003": 1000 + i * 5} for i in range(40)}  # 2010-2019 only
    res = factor(by_year, overall)
    assert res["basis"] == "built_2010_2019" and res["tracts"] == 40
    assert abs(res["factor"] - 1.0975) < 0.001  # median of 1.000 .. 1.195
    for i in range(MIN_TRACTS):
        by_year[str(i)]["002"] = 1200
    res = factor(by_year, overall)
    assert res["basis"] == "built_2020_or_later" and res["factor"] == 1.2
    assert factor({}, overall)["missing"]


def test_tract_shapes_read_from_a_state_file():
    import zipfile

    import shapefile

    from jobs.load_tracts import tracts

    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    for f in ("STATEFP", "COUNTYFP", "GEOID"):
        w.field(f, "C")
    w.poly([[[-95.4, 29.7], [-95.3, 29.7], [-95.3, 29.8], [-95.4, 29.8], [-95.4, 29.7]]])
    w.record("48", "201", "48201530200")
    w.close()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for ext, b in (("shp", shp), ("shx", shx), ("dbf", dbf)):
            z.writestr(f"cb_2024_48_tract_500k.{ext}", b.getvalue())
    rows = list(tracts(buf.getvalue()))
    assert rows[0][0] == "48201530200" and '"Polygon"' in rows[0][1]
