import psycopg

from db.migrate import migrate
from jobs import load_parcels, load_sales


class FakeClient:
    def __init__(self, pages):
        self._pages = pages
        self.calls = []

    def pages(self, dataset_id, order, select=None, where=None, page_size=50_000):
        self.calls.append((dataset_id, order, where))
        yield from self._pages


PARCEL = {
    "pin": "16022260370000",
    "pin10": "1602226037",
    "year": "2026",
    "class": "211",
    "township_code": "77",
    "nbhd_code": "77020",
    "ward_num": "26",
    "chicago_community_area_num": "23",
    "chicago_community_area_name": "HUMBOLDT PARK",
    "census_tract_geoid": "17031230900",
    "zip_code": "60651",
    "tax_tif_district_num": "",
    "env_flood_fema_sfha": False,
    "lon": "-87.7071971756",
    "lat": "41.9042033427",
}

SALE = {
    "row_id": "abc-1",
    "pin": "16022260370000",
    "sale_date": "2026-05-07T00:00:00.000",
    "sale_price": "575000.0",
    "deed_type": "Other",
    "class": "211",
    "township_code": "77",
    "nbhd": "77020",
    "is_multisale": False,
    "num_parcels_sale": "1.0",
    "sale_filter_deed_type": True,
}


def test_parcel_load_writes_point_and_source(db_url):
    migrate(db_url)
    client = FakeClient([[PARCEL], [dict(PARCEL, ward_num="27")]])
    assert load_parcels.run(2026, client=client, url=db_url) == 2
    assert "CITY OF CHICAGO" in client.calls[0][2]
    with psycopg.connect(db_url) as conn:
        row = conn.execute(
            "select p.ward, p.tif_district_num, round(st_x(p.geom)::numeric, 4)::float8, s.status, s.row_count"
            " from parcel p join source_pull s on s.id = p.source_pull_id"
        ).fetchall()
    assert row == [(27, None, -87.7072, "ok", 2)]  # second page updated the same PIN


def test_sale_load_is_incremental(db_url):
    migrate(db_url)
    assert load_sales.run(client=FakeClient([[SALE]]), url=db_url) == 1
    client = FakeClient([[]])
    load_sales.run(client=client, url=db_url)
    assert "sale_date >= '2026-05-08'" in client.calls[0][2]
    with psycopg.connect(db_url) as conn:
        assert conn.execute("select sale_price, filter_deed_type, num_parcels_sale from sale").fetchone() == (
            575000,
            True,
            1,
        )


def test_failed_pull_is_recorded(db_url):
    migrate(db_url)

    class Broken(FakeClient):
        def pages(self, *a, **k):
            raise RuntimeError("portal down")
            yield

    try:
        load_sales.run(since="2026-01-01", client=Broken([]), url=db_url)
    except RuntimeError:
        pass
    with psycopg.connect(db_url) as conn:
        assert conn.execute("select status, note from source_pull order by id desc limit 1").fetchone() == (
            "failed",
            "portal down",
        )


def test_permit_pins_address_and_point(db_url):
    from jobs import load_permits

    migrate(db_url)
    row = {
        "id": "p1",
        "permit_": "101030086",
        "permit_type": "PERMIT - NEW CONSTRUCTION",
        "review_type": "SELF CERT",
        "issue_date": "2026-10-08T00:00:00.000",
        "processing_time": "50",
        "street_number": "1463",
        "street_direction": "W",
        "street_name": "MONTROSE AVE",
        "pin_list": "1417301001 | 14173010020000 | junk",
        "xcoordinate": "1165432.0",
        "ycoordinate": "1930654.0",
    }
    assert load_permits.run(client=FakeClient([[row]]), url=db_url) == 1
    with psycopg.connect(db_url) as conn:
        got = conn.execute(
            "select address, pins, processing_days, round(st_y(geom)::numeric, 2)::float8 from permit"
        ).fetchone()
    assert got == ("1463 W MONTROSE AVE", ["14173010010000", "14173010020000"], 50, 41.97)


def test_building_char_reads_apartments_in_words(db_url):
    from jobs import load_building_chars

    migrate(db_url)
    rows = [
        {
            "row_id": "r1",
            "pin": "16022260370000",
            "year": "2026.0",
            "char_apts": "Three",
            "char_bldg_sf": "4044.0",
        },
        {"row_id": "r2", "pin": "16022260380000", "year": "2026.0", "char_apts": "None"},
    ]
    assert load_building_chars.run(2026, client=FakeClient([rows]), url=db_url) == 2
    with psycopg.connect(db_url) as conn:
        got = conn.execute(
            "select apartments, building_sqft, tax_year from building_char order by row_id"
        ).fetchall()
    assert got == [(3, 4044, 2026), (0, None, 2026)]
