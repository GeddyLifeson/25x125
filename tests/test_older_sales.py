import math
from datetime import date

import psycopg

from db.migrate import migrate
from engine.older_sales import OlderSale, estimate, local_price
from jobs import build_older_sales
from jobs.check_older_sales import fit

CURVE = {
    "verified_on": "2026-11-01",
    "extrapolation_widen": 0.15,
    "curves": {
        "building": {"a": 4.8535, "b": 0.6471, "n": 191, "band": [0.742, 1.274], "fit_range": [93177, 518513]}
    },
}
LAT, LON = 41.73, -87.55


def sales_near(price: float, n: int = 12, step: float = 0.002) -> list[OlderSale]:
    return [OlderSale(date(2025, 6, 1), price, LAT + i * step / 69, LON) for i in range(n)]


def test_local_price_needs_ten_recent_sales_and_widens_radius():
    assert local_price(sales_near(100_000, 9), LAT, LON, date(2026, 11, 1)) is None
    price, n, radius = local_price(sales_near(100_000), LAT, LON, date(2026, 11, 1))
    assert (price, n, radius) == (100_000, 12, 0.75)
    far = sales_near(100_000, 12, step=0.1)  # 8 within 0.75 mi, all 12 within 1.1 mi
    assert local_price(far, LAT, LON, date(2026, 11, 1))[2] == 1.5
    old = [OlderSale(date(2022, 1, 1), 100_000, LAT, LON)] * 12
    assert local_price(old, LAT, LON, date(2026, 11, 1)) is None


def test_estimate_converts_older_price_with_the_curve():
    e = estimate(sales_near(150_000), LAT, LON, date(2026, 11, 1), curve=CURVE)
    assert e["central"] == round(math.exp(4.8535 + 0.6471 * math.log(150_000)))
    assert e["low"] < e["central"] < e["high"] and not e["extrapolated"]
    low = estimate(sales_near(80_000), LAT, LON, date(2026, 11, 1), curve=CURVE)
    assert low["extrapolated"] and low["low"] / low["central"] < 0.742 * 0.86


def test_fit_recovers_a_line():
    pts = [(x, 2.0 + 0.5 * x) for x in (11.0, 11.5, 12.0, 12.5)]
    a, b = fit(pts)
    assert round(a, 6) == 2.0 and round(b, 6) == 0.5


def test_build_keeps_older_arms_length_building_sales(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        pull = conn.execute(
            "insert into source_pull (host, dataset_id, started_at, status) values ('t', 't', now(), 'ok') returning id"
        ).fetchone()[0]
        conn.execute(
            "insert into building_char (row_id, pin, tax_year, class, apartments, year_built, source_pull_id)"
            " values ('b1', '20000000010000', 2026, '211', 3, 1905, %s),"
            " ('b2', '20000000020000', 2026, '211', 3, 2018, %s)",
            (pull, pull),
        )
        conn.execute(
            "insert into parcel (pin, pin10, tax_year, municipality_id, class, community_area_name, geom, source_pull_id)"
            " values ('20000000010000', '2000000001', 2026, 'chicago', '211', 'SOUTH CHICAGO',"
            "  st_setsrid(st_makepoint(-87.55, 41.73), 4326), %s)",
            (pull,),
        )
        conn.execute(
            "insert into sale (row_id, pin, sale_date, sale_price, deed_type, source_pull_id) values"
            " ('s1', '20000000010000', '2025-03-01', 270000, 'Warranty', %s),"
            " ('s2', '20000000010000', '2024-03-01', 90000, 'Other', %s),"
            " ('s3', '20000000020000', '2025-03-01', 900000, 'Warranty', %s)",
            (pull, pull, pull),
        )
    assert build_older_sales.run(db_url) == 1
    with psycopg.connect(db_url) as conn:
        row = conn.execute("select pin, price_per_unit, community_area from older_sale").fetchone()
    assert row == ("20000000010000", 90000, "South Chicago")
