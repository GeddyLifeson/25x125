import json

import psycopg

from db.migrate import migrate
from jobs import build_parcel_site, load_parcel_shapes, load_signals
from jobs.load_signals import to_row
from tests.test_loaders import FakeClient
from tests.test_parcel_site import FakeArcGIS, lot_geojson


def test_city_owned_row_keeps_pin_without_dashes_and_drops_bad_points():
    r = {"id": "8638", "pin": "16-09-424-002-0000", "address": "4853 W WEST END AVE",
         "property_status": "Owned by City", "date_of_acquisition": "2003-09-17T00:00:00.000",
         "latitude": "0", "longitude": "0", "land_value": "17989"}  # fmt: skip
    kind, sid, date, status, _, addr, pin, attrs, lon, lat, pull = to_row("city_owned", r, 3)
    assert (kind, sid, date, status, addr, pin, lon, lat, pull) == (
        "city_owned", "8638", "2003-09-17", "Owned by City", "4853 W WEST END AVE", "16094240020000",
        None, None, 3,
    )  # fmt: skip
    assert json.loads(attrs) == {"land_value": "17989"}


def test_signals_sum_onto_the_lot_under_the_point(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        lot = lot_geojson(conn)
        lon, lat = conn.execute(
            "select st_x(c), st_y(c) from (select st_centroid(st_geomfromgeojson(%s)) c) x",
            (json.dumps(lot),),
        ).fetchone()
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
    point = {"latitude": str(lat), "longitude": str(lon)}
    violations = [
        dict(point, id="1", violation_date="2025-03-01T00:00:00.000", violation_status="OPEN"),
        dict(point, id="2", violation_date="2026-06-01T00:00:00.000", violation_status="COMPLIED"),
        dict(point, id="3", violation_date="2026-07-01T00:00:00.000", violation_status="OPEN"),
    ]
    assert load_signals.run_kind("violation", client=FakeClient([violations]), url=db_url) == 3
    recent = "2026-01-05T00:00:00.000"
    complaints = [
        dict(point, sr_number="SR1", created_date=recent, duplicate="False"),
        dict(point, sr_number="SR2", created_date=recent, duplicate="True"),
    ]
    load_signals.run_kind("vacant_building_311", client=FakeClient([complaints]), url=db_url)
    load_signals.run_kind("scofflaw", client=FakeClient([[dict(point, record_id="R1")]]), url=db_url)
    build_parcel_site.run(db_url)
    with psycopg.connect(db_url) as conn:
        row = conn.execute(
            "select open_violations, last_violation_date::text, vacant_building_311, scofflaw, city_owned_status"
            " from parcel_site"
        ).fetchone()
    assert row == (2, "2026-07-01", 1, True, None)
