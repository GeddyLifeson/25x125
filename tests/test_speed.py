"""Speed fixes from the 2026-11-04 browser sweep: the shared comp tables reload when a load changes them, and the
list's sorts and the one-lot views read through indexes instead of whole-table scans."""

import psycopg

from db.migrate import migrate
from engine import parcel_feasibility
from engine.parcel_feasibility import comp_tables
from engine.parcels import LOT_SORTS


def _plan(conn, sql: str, args=()) -> str:
    return "\n".join(r[0] for r in conn.execute("explain " + sql, args).fetchall())


def test_comp_tables_reload_after_a_load_changes_them(db_url):
    migrate(db_url)
    parcel_feasibility._COMP_TABLES.update(key=None, value=None)
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("delete from comp")
        pool, _, _ = comp_tables(conn)
        assert pool == []
        assert comp_tables(conn)[0] is pool  # unchanged tables: the same copy, no reload
        conn.execute(
            """insert into comp (sale_row_id, pin, kind, building_id, sale_date, price, units, price_per_unit, geom)
               values ('t1', '16121020310000', 'building', '1612102031', '2025-06-01', 900000, 3, 300000,
                       st_setsrid(st_makepoint(-87.71, 41.89), 4326))"""
        )
        pool2, _, _ = comp_tables(conn)
        assert len(pool2) == 1 and pool2[0].price_per_unit == 300000
        conn.execute("delete from comp where sale_row_id = 't1'")
        assert comp_tables(conn)[0] == []


def test_list_sorts_and_lot_lookups_use_indexes(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        names = {r[0] for r in conn.execute("select indexname from pg_indexes where schemaname = 'public'")}
        for idx in ("parcel_score_return", "parcel_score_upside", "parcel_score_score_pin10", "parcel_score_pin",
                    "parcel_site_lot_sqft"):  # fmt: skip
            assert idx in names
        assert all(order.endswith(("s.pin10", "ps.pin")) for order in LOT_SORTS.values())  # unique key last
        conn.execute("set enable_seqscan = off")  # an empty test table would otherwise always scan
        plan = _plan(conn, "select * from lot_market_value where pin10 = %s", ("1612102031",))
        assert "assessed_value_pin10_idx" in plan, plan
