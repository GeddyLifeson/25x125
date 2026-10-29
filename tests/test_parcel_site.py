import json

import psycopg

from db.migrate import migrate
from jobs import build_parcel_site, load_parcel_shapes, load_zoning
from tests.test_loaders import FakeClient

# A 25 x 125 ft lot drawn in State Plane feet, then converted to lon/lat.
LOT_3435 = "POLYGON((1154690 1908300, 1154715 1908300, 1154715 1908425, 1154690 1908425, 1154690 1908300))"


def lot_geojson(conn) -> dict:
    g = conn.execute(
        f"select st_asgeojson(st_transform(st_geomfromtext('{LOT_3435}', 3435), 4326))"
    ).fetchone()[0]
    return json.loads(g)


def test_lot_measures_on_a_standard_lot(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        area, short, long = conn.execute(
            f"select round(area_sqft), round(short_ft), round(long_ft)"
            f" from lot_measures(st_transform(st_geomfromtext('{LOT_3435}', 3435), 4326))"
        ).fetchone()
    assert (area, short, long) == (3125, 25, 125)


def test_parcel_site_joins_zoning_and_lot(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        lot = lot_geojson(conn)
        conn.execute(
            "delete from parcel_site; delete from parcel; delete from parcel_shape; delete from zoning_district_area"
        )
        pid = conn.execute(
            "insert into source_pull (host, dataset_id, started_at, status) values ('t', 't', now(), 'ok') returning id"
        ).fetchone()[0]
        conn.execute(
            "insert into parcel (pin, pin10, tax_year, municipality_id, geom, source_pull_id) values"
            " ('16022260371001', '1602226037', 2026, 'chicago', null, %s),"
            " ('16022260371002', '1602226037', 2026, 'chicago', null, %s)",
            (pid, pid),
        )
        conn.commit()
    # Two polygon rows for the same PIN merge into one shape.
    half = {"type": "Polygon", "coordinates": lot["coordinates"]}
    load_parcel_shapes.run(client=FakeClient([[{"pin10": "1602226037", "the_geom": half}]]), url=db_url)
    big = {
        "type": "MultiPolygon",
        "coordinates": [[[[-87.8, 41.8], [-87.6, 41.8], [-87.6, 42.0], [-87.8, 42.0], [-87.8, 41.8]]]],
    }
    load_zoning.run(
        client=FakeClient([[{"objectid": "1", "zone_class": "RT-4", "zone_type": "1", "the_geom": big}]]),
        url=db_url,
    )
    assert build_parcel_site.run(db_url) == 2
    with psycopg.connect(db_url) as conn:
        rows = conn.execute(
            "select pin, zone_class, zone_share, round(lot_sqft), round(frontage_ft), lot_source from parcel_site order by pin"
        ).fetchall()
    assert rows == [
        ("16022260371001", "RT-4", 1, 3125, 25, "polygon 2021"),
        ("16022260371002", "RT-4", 1, 3125, 25, "polygon 2021"),
    ]
