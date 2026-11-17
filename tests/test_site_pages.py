"""The facts added for the finished website: tax sale, city listing, Assessor value and nearby rezonings on the
parcel page; the data sources list; the row-count drop check."""

from datetime import date, timedelta

import psycopg

from db.migrate import migrate
from engine import parcels, sources
from jobs.report import count_drops


def rez(record, intro, final, status, sub, frm="RS-3", to="RT-4", meters=100.0):
    return (record, "100 N MAIN ST", intro, final, status, sub, frm, to, meters)


def test_rezoning_summary_counts_decided_and_passed():
    rows = [
        rez("O1", date(2025, 1, 1), date(2025, 3, 2), "90-Final", "Passed"),
        rez("O2", date(2025, 2, 1), date(2025, 5, 12), "90-Final", "Passed as Substitute"),
        rez("O3", date(2025, 3, 1), date(2025, 4, 1), "90-Final", "Withdrawn"),
        rez("O4", date(2026, 1, 1), None, "4-In Committee", "Referred"),
    ]
    s = parcels.rezoning_summary(rows)
    assert (s["count"], s["decided"], s["passed"]) == (4, 3, 2)
    assert s["share_passed"] == 0.667
    assert s["median_days_to_pass"] == 80  # 60 and 100 days
    assert s["list"][0] == {"record": "O1", "address": "100 N MAIN ST", "introduced": "2025-01-01",
                            "decided": "2025-03-02", "status": "Passed", "from": "RS-3", "to": "RT-4", "feet": 328}  # fmt: skip
    assert "do not predict" in s["label"]


def test_rezoning_summary_with_no_applications():
    s = parcels.rezoning_summary([])
    assert (
        s["count"] == 0 and s["share_passed"] is None and s["median_days_to_pass"] is None and s["list"] == []
    )


def add_parcel(conn, pin, lon, lat=41.8930):
    pid = conn.execute(
        "insert into source_pull (host, dataset_id, started_at, status) values ('t', 't', now(), 'ok') returning id"
    ).fetchone()[0]
    conn.execute(
        "insert into parcel (pin, pin10, tax_year, municipality_id, class, geom, source_pull_id)"
        " values (%s, %s, 2026, 'chicago', '211', st_setsrid(st_makepoint(%s, %s), 4326), %s)",
        (pin, pin[:10], lon, lat, pid),
    )


def seed_lot(conn, pin="16121020310000", sale=None):
    conn.execute("truncate parcel, parcel_site, tax_sale_list, rezoning, lot_for_sale cascade")
    add_parcel(conn, pin, -87.7054)
    conn.execute(
        "insert into parcel_site (pin, pin10, zone_class, lot_sqft, tax_sale_date, tax_sale_due, tax_sale_pins)"
        " values (%s, %s, 'RT-4', 3125, %s, %s, %s)",
        (pin, pin[:10], sale, 2064.26 if sale else None, 1 if sale else None),
    )


def test_parcel_shows_the_tax_sale_rows_until_the_sale(db_url):
    migrate(db_url)
    upcoming, past = date.today() + timedelta(days=20), date.today() - timedelta(days=3)
    with psycopg.connect(db_url) as conn:
        for sale, shown in ((upcoming, True), (past, False)):
            seed_lot(conn, sale=sale)
            conn.execute(
                "insert into tax_sale_list (sale_date, pin, pin10, ward, tax_type, tax_year, total_tax_due, total_due,"
                " classification, listed_through, source_url) values (%s, '16121020310000', '1612102031', 27, '00',"
                " 2023, 1838.49, 2064.26, 'Residential', %s, 'https://example.org/ward27')",
                (sale, sale - timedelta(days=14)),
            )
            p = parcels.parcel(conn, "16121020310000")
            assert (p["tax_sale"] is not None) is shown
        seed_lot(conn, sale=upcoming)
        conn.execute(
            "insert into tax_sale_list (sale_date, pin, pin10, tax_type, tax_year, total_tax_due, total_due,"
            " source_url) values (%s, '16121020310000', '1612102031', '00', 2023, 1838.49, 2064.26, 'https://example.org/w')",
            (upcoming,),
        )
        ts = parcels.parcel(conn, "16121020310000")["tax_sale"]
        conn.rollback()
    assert ts["sale_date"] == upcoming.isoformat() and ts["total_due"] == 2064.26 and ts["pins"] == 1
    assert ts["rows"][0]["tax_year"] == 2023 and ts["rows"][0]["total_due"] == 2064.26
    assert "owner" not in " ".join(ts["rows"][0])  # no taxpayer fields stored or shown
    assert "lien" in ts["note"]


def test_parcel_counts_rezonings_within_half_a_mile_and_hides_unchecked_districts(db_url):
    migrate(db_url)
    today = date.today()
    with psycopg.connect(db_url) as conn:
        seed_lot(conn)
        # a lot about 300 m east (inside half a mile) and one about 2 km east (outside)
        for pin, lon in (("16121020400000", -87.7018), ("16121029990000", -87.6810)):
            add_parcel(conn, pin, lon)
        ins = ("insert into rezoning (record_number, matter_id, title, type1, alderman_filed, address, intro_date,"
               " final_date, status, sub_status, from_district, to_district, pin10, district_check)"
               " values (%s, %s, 't', true, false, %s, %s, %s, %s, %s, 'RS-3', 'RT-4', %s, %s)")  # fmt: skip
        near, far = "1612102040", "1612102999"
        conn.execute(ins, ("O-1", "m1", "700 N A ST", today - timedelta(days=200), today - timedelta(days=110),
                           "90-Final", "Passed", near, "confirmed"))  # fmt: skip
        conn.execute(ins, ("O-2", "m2", "702 N A ST", today - timedelta(days=90), None, "4-In Committee", "Referred",
                           near, "unresolved"))  # fmt: skip
        conn.execute(ins, ("O-3", "m3", "900 N B ST", today - timedelta(days=90), None, "4-In Committee", "Referred",
                           far, "model"))  # fmt: skip
        conn.execute(ins, ("O-4", "m4", "704 N A ST", today - timedelta(days=365 * 7), today - timedelta(days=365 * 7 - 60),
                           "90-Final", "Passed", near, "model"))  # fmt: skip
        r = parcels.parcel(conn, "16121020310000")["rezonings_nearby"]
        conn.rollback()
    assert (r["count"], r["decided"], r["passed"], r["median_days_to_pass"]) == (2, 1, 1, 90)
    by = {x["record"]: x for x in r["list"]}
    assert set(by) == {"O-1", "O-2"}
    assert (by["O-1"]["from"], by["O-1"]["to"]) == ("RS-3", "RT-4")
    assert (by["O-2"]["from"], by["O-2"]["to"]) == (None, None)  # failed the check: districts stay hidden
    assert 900 < by["O-1"]["feet"] < 1100
    assert (r["placed"], r["citywide"]) == (3, 3)


def test_lot_list_filters_to_the_next_tax_sale(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        seed_lot(conn, sale=date.today() + timedelta(days=10))
        add_parcel(conn, "16121020400000", -87.70, 41.89)
        conn.execute(
            "insert into parcel_site (pin, pin10, zone_class, lot_sqft) values ('16121020400000', '1612102040', 'RT-4', 3125)"
        )
        conn.execute("truncate parcel_score")
        for pin in ("16121020310000", "16121020400000"):
            conn.execute(
                "insert into parcel_score (pin10, pin, score, zoning_upside, profit, acquisition, location, incentives,"
                " penalties, details, computed_on) values (%s, %s, 50, 10, 10, 10, 10, 10, 0, '{}', current_date)",
                (pin[:10], pin),
            )
        everyone = parcels.lots(conn)
        listed = parcels.lots(conn, tax_sale=True)
        tile_sig = conn.execute(
            "select prosrc like '%%tax_sale_date >= current_date%%' from pg_proc where proname = 'lot_tiles'"
        ).fetchone()[0]
        conn.rollback()
    assert len(everyone) == 2
    assert [r["pin10"] for r in listed] == ["1612102031"]
    assert listed[0]["tax_sale_due"] == 2064.26 and listed[0]["tax_sale_date"] > date.today().isoformat()
    assert tile_sig  # the map tiles carry the same flag as the list filter


def test_sources_list_links_and_last_copy(db_url):
    migrate(db_url)
    rows = sources.catalog()
    assert len(rows) > 40 and all(r["dataset"] and r["portal"] for r in rows)
    assert sources.link({"base_url": "https://data.cityofchicago.org/resource/", "id": "ydr8-5enu"}) == (
        "https://data.cityofchicago.org/d/ydr8-5enu"
    )
    assert sources.link({"base_url": "https://www.fhfa.gov/x", "id": "hpi"}) == "https://www.fhfa.gov/x"
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate source_pull cascade")
        conn.execute(
            "insert into source_pull (host, dataset_id, started_at, finished_at, row_count, status)"
            " values ('data.cityofchicago.org', 'ydr8-5enu', now(), now(), 1234, 'ok')"
        )
        out = sources.sources(conn)
        conn.rollback()
    by = {s["id"]: s for s in out["sources"]}
    assert by["ydr8-5enu"]["rows"] == 1234 and by["ydr8-5enu"]["last_pulled"] == date.today().isoformat()
    assert by["wvhk-k5uv"]["last_pulled"] is None
    assert "no Zillow figure is shown" in by["zori"]["display"]
    assert any("City of Chicago makes no claims" in a["text"] for a in out["attribution"])
    assert all(a["url"].startswith("https://") and a["verified_on"] for a in out["attribution"])


def test_count_drops_flags_a_source_that_lost_over_ten_percent(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate source_pull cascade")
        ins = ("insert into source_pull (host, dataset_id, query, started_at, finished_at, row_count, status)"
               " values ('h', %s, %s, now() - %s * interval '1 day', now() - %s * interval '1 day', %s, %s)")  # fmt: skip
        conn.execute(ins, ("zoning", "all", 2, 2, 1000, "ok"))
        conn.execute(ins, ("zoning", "all", 1, 1, 850, "ok"))  # 15% fewer: flagged
        conn.execute(ins, ("tif", "all", 2, 2, 1000, "ok"))
        conn.execute(ins, ("tif", "all", 1, 1, 950, "ok"))  # 5% fewer: fine
        conn.execute(ins, ("sales", "since 2026-11-01", 2, 2, 5000, "ok"))
        conn.execute(
            ins, ("sales", "since 2026-11-16", 1, 1, 40, "ok")
        )  # new rows only, another query: not compared
        conn.execute(ins, ("cta", "all", 3, 3, 1000, "ok"))
        conn.execute(ins, ("cta", "all", 2, 2, 100, "ok"))
        conn.execute(ins, ("cta", "all", 1, 1, 1000, "ok"))  # recovered: the newest pull is fine
        conn.execute(ins, ("landmarks", "all", 2, 2, 300, "ok"))
        conn.execute(ins, ("landmarks", "all", 1, 1, 0, "failed"))  # failed pulls are reported elsewhere
        drops = count_drops(conn)
        conn.rollback()
    assert [(d["dataset_id"], d["previous_rows"], d["rows"], d["drop"]) for d in drops] == [
        ("zoning", 1000, 850, 0.15)
    ]
