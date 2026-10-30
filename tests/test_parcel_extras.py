import psycopg

from db.migrate import migrate
from jobs import load_parcel_extras, load_parcel_shapes
from jobs.load_parcel_extras import day, footprint_row, permit_row, proximity_row
from jobs.load_signals import to_row
from tests.test_loaders import FakeClient
from tests.test_parcel_site import FakeArcGIS, lot_geojson


class FakeYearClient(FakeClient):
    def get(self, dataset_id, params):
        return [{"y": "2025"}]


def test_permit_row_drops_impossible_dates():
    r = {"row_id": "R1", "pin": "24053030660000", "date_issued": "2210-04-21T23:34:33.000", "amount": "176563.0",
         "status": "PENDING", "job_code_primary": "COMMERCIAL PERMIT", "improvement_code_1": "OTHER"}  # fmt: skip
    row = permit_row(r, 7)
    assert row[4] is None
    assert row[7] == 176563.0
    assert day("2024-05-01T00:00:00.000") == "2024-05-01"


def test_proximity_row_reads_counts_and_distances():
    r = {"pin10": "1602226037", "year": "2025", "num_foreclosure_in_half_mile_past_5_years": "4",
         "nearest_new_construction_pin10": "1602226040", "nearest_new_construction_dist_ft": "312.5"}  # fmt: skip
    row = proximity_row(r, 1)
    assert row[:3] == ("1602226037", 2025, 4)
    assert row[5:7] == ("1602226040", 312.5)


def test_footprint_row_blanks_zero_values():
    r = {"bldg_id": "729719", "bldg_statu": "ACTIVE", "stories": "2", "no_of_unit": "0", "year_built": "0",
         "f_add1": "10203", "pre_dir1": "S", "st_name1": "WOOD", "st_type1": "ST",
         "the_geom": {"type": "MultiPolygon", "coordinates": []}}  # fmt: skip
    row = footprint_row(r, 1)
    assert row[2:5] == (2, None, None)
    assert row[7] == "10203 S WOOD ST"


def test_foreclosed_rental_reads_wkt_point():
    r = {"id": "167913", "property_address": "10115 S Emerald Av", "owner_date": "2022-03-24T00:00:00.000",
         "owner_name": "US Bank National Association", "location": "POINT (-87.6415 41.7100)"}  # fmt: skip
    row = to_row("foreclosed_rental", r, 2)
    assert (row[2], row[4], row[8], row[9]) == ("2022-03-24", "US Bank National Association", -87.6415, 41.71)


def test_footprint_ties_to_lot_and_proximity_keeps_chicago_lots(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        lot = lot_geojson(conn)
        conn.execute("delete from parcel_site; delete from parcel; delete from parcel_shape")
        pid = conn.execute(
            "insert into source_pull (host, dataset_id, started_at, status) values ('t', 't', now(), 'ok') returning id"
        ).fetchone()[0]
        conn.execute(
            "insert into parcel (pin, pin10, tax_year, municipality_id, geom, source_pull_id)"
            " values ('16022260370000', '1602226037', 2026, 'chicago', null, %s)",
            (pid,),
        )
        conn.commit()
    load_parcel_shapes.run(
        client=FakeArcGIS([[{"type": "Feature", "properties": {"PIN10": "1602226037"}, "geometry": lot}]]),
        url=db_url,
    )
    shape = {"type": "MultiPolygon", "coordinates": [lot["coordinates"]]}
    fp = {"bldg_id": "1", "bldg_statu": "ACTIVE", "stories": "3", "no_of_unit": "3", "the_geom": shape}
    assert load_parcel_extras.run_source("footprints", client=FakeClient([[fp]]), url=db_url) == 1
    prox = [{"pin10": "1602226037", "year": "2025"}, {"pin10": "0101100002", "year": "2025"}]
    assert load_parcel_extras.run_source("proximity", client=FakeYearClient([prox]), url=db_url) == 2
    with psycopg.connect(db_url) as conn:
        assert conn.execute("select pin10, stories, units from building_footprint").fetchall() == [
            ("1602226037", 3, 3)
        ]
        assert conn.execute("select pin10 from parcel_proximity").fetchall() == [("1602226037",)]
