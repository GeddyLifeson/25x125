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
