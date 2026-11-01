"""Deals and outreach log endpoints (engine/deals.py), and the map tile functions (0022_map_tiles.sql)."""

import csv
import io

import psycopg
import pytest
from fastapi.testclient import TestClient

import engine.app as app_module
import engine.areas as areas_module
import engine.deals as deals_module
from db.migrate import migrate

PIN = "16121020310000"
SQUARE = "MULTIPOLYGON(((-87.71 41.90,-87.709 41.90,-87.709 41.901,-87.71 41.901,-87.71 41.90)))"


def _clear(db_url):
    """Remove this file's rows, so tests that count parcels see only their own."""
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate deal, parcel_score cascade")
        conn.execute("delete from parcel_address where pin like '1612102031%'")
        conn.execute("delete from parcel_site where pin10 = '1612102031'")
        conn.execute("delete from parcel_shape where pin10 = '1612102031'")
        conn.execute("delete from parcel where pin like '1612102031%'")
        conn.execute("delete from boundary where code in ('23', '99999')")
        conn.execute("delete from land_value where geo_id in ('23', '99999')")
        conn.execute("delete from source_pull where host = 'test' and dataset_id = 'test'")


@pytest.fixture
def client(db_url, monkeypatch, make_member):
    migrate(db_url)
    _clear(db_url)
    with psycopg.connect(db_url) as conn:
        pull = conn.execute(
            "insert into source_pull (host, dataset_id, started_at, finished_at, status)"
            " values ('test', 'test', now(), now(), 'ok') returning id"
        ).fetchone()[0]
        conn.execute(
            """insert into parcel (pin, pin10, tax_year, municipality_id, community_area_num, community_area_name, geom,
                                   source_pull_id)
               values (%s, %s, 2025, 'chicago', 23, 'HUMBOLDT PARK', st_setsrid(st_point(-87.7095, 41.9005), 4326), %s)""",
            (PIN, PIN[:10], pull),
        )  # fmt: skip
        conn.execute(
            "insert into parcel_address (pin, tax_year, address, zip, source_pull_id) values (%s, 2025, '624 N TROY ST', '60612', %s)",
            (PIN, pull),
        )
        conn.execute(
            "insert into parcel_site (pin, pin10, zone_class) values (%s, %s, 'RT-4')", (PIN, PIN[:10])
        )
        conn.execute(
            "insert into parcel_shape (pin10, vintage, geom, source_pull_id) values (%s, 2025, st_geomfromtext(%s, 4326), %s)",
            (PIN[:10], SQUARE, pull),
        )
        conn.execute(
            """insert into parcel_score (pin10, pin, score, zoning_upside, profit, acquisition, location, incentives,
                                         penalties, by_right_units, profit_central, max_land_price, details, computed_on)
               values (%s, %s, 62, 30, 10, 18, 5, 2, 0, 3, 150000, 90000,
                       '{"signals": ["vacant_land"], "fast_path": true, "penalties": []}', '2026-11-01')""",
            (PIN[:10], PIN),
        )  # fmt: skip
        conn.execute(
            "insert into boundary (kind, code, name, geom, source_pull_id) values"
            " ('community_area', '23', 'HUMBOLDT PARK', st_multi(st_buffer(st_setsrid(st_point(-87.71, 41.90), 4326), 0.02)), %s)",
            (pull,),
        )
        conn.execute(
            "insert into land_value (geo_kind, geo_id, kind, sales, median_per_lot_sqft, computed_on)"
            " values ('community_area', '23', 'all', 12, 40.5, '2026-10-30')"
        )
    monkeypatch.setattr(deals_module, "connect", lambda: psycopg.connect(db_url))
    monkeypatch.setattr(areas_module, "connect", lambda: psycopg.connect(db_url))
    yield TestClient(app_module.app, headers=make_member("owner@test.example", "test-org-a"))
    _clear(db_url)


def fake_feasibility(conn, pin, exit_, overrides, target):
    land = (overrides.get("all") or {}).get("land", 100000)
    return {
        "scenarios": [
            {"name": "A · 3-flat by right", "units": 3, "exit": exit_,
             "cost_range": {"central": 1_200_000, "low": 1_000_000, "high": 1_500_000},
             "sell": {"profit": 300_000 - land, "return_on_cost": 0.15, "max_land_price": 220_000,
                      "range": {"p10": -50_000, "p90": 400_000}}},
        ]
    }  # fmt: skip


def test_create_list_update_delete(client, monkeypatch):
    monkeypatch.setattr(deals_module, "feasibility", fake_feasibility)
    r = client.post(
        "/deals", json={"pin": PIN, "exit": "sell", "scenario": 0, "overrides": {"all": {"land": 60000}}}
    )
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["address"] == "624 N TROY ST" and d["pin10"] == PIN[:10] and d["stage"] == "lead"
    assert d["overrides"] == {"all": {"land": 60000}}
    assert d["result"]["profit"] == 240_000 and d["result"]["run_on"]
    assert d["scenario_name"] == "A · 3-flat by right"
    assert d["nightly"]["score"] == 62 and d["nightly"]["computed_on"] == "2026-11-01"

    # A 10-digit lot number finds the lot's PIN; no exit means no feasibility run.
    d2 = client.post("/deals", json={"pin": PIN[:10], "stage": "Contacted"}).json()
    assert d2["pin"] == PIN and d2["stage"] == "contacted" and d2["result"] is None

    assert {x["id"] for x in client.get("/deals").json()} == {d["id"], d2["id"]}
    assert [x["id"] for x in client.get("/deals?stage=contacted").json()] == [d2["id"]]
    counts = client.get("/deals/pipeline").json()
    assert counts["total"] == 2
    assert {s["id"]: s["count"] for s in counts["stages"]} == {
        "lead": 1, "contacted": 1, "feasibility": 0, "under_contract": 0, "passed": 0}  # fmt: skip

    p = client.patch(
        f"/deals/{d['id']}",
        json={"stage": "under_contract", "next_step": "Closing", "next_step_on": "2026-11-20"},
    )
    assert (
        p.status_code == 200
        and p.json()["stage_label"] == "Under contract"
        and p.json()["next_step_on"] == "2026-11-20"
    )
    assert client.patch(f"/deals/{d['id']}", json={"stage": "sold"}).status_code == 400

    assert client.delete(f"/deals/{d2['id']}").status_code == 204
    assert client.get(f"/deals/{d2['id']}").status_code == 404
    assert client.delete(f"/deals/{d2['id']}").status_code == 404


def test_bad_input(client):
    assert client.post("/deals", json={"pin": "123"}).status_code == 400
    assert client.post("/deals", json={"pin": "99999999999999"}).status_code == 404
    assert client.post("/deals", json={"pin": PIN, "stage": "won"}).status_code == 400
    assert client.post("/deals", json={"pin": PIN, "exit": "flip"}).status_code == 400


def test_rerun_uses_saved_overrides(client, monkeypatch):
    monkeypatch.setattr(deals_module, "feasibility", fake_feasibility)
    d = client.post("/deals", json={"pin": PIN, "exit": "sell", "overrides": {"all": {"land": 50000}}}).json()
    assert d["result"]["profit"] == 250_000
    r = client.post(f"/deals/{d['id']}/rerun").json()
    assert r["result"]["profit"] == 250_000 and r["overrides"] == {"all": {"land": 50000}}
    # New edits from the feasibility screen replace the saved ones and re-run.
    r = client.patch(f"/deals/{d['id']}", json={"overrides": {"all": {"land": 80000}}, "exit": "sell"}).json()
    assert r["result"]["profit"] == 220_000 and r["overrides"] == {"all": {"land": 80000}}


def test_outreach_log(client):
    d = client.post("/deals", json={"pin": PIN}).json()
    r = client.post(
        f"/deals/{d['id']}/events", json={"kind": "letter", "event_on": "2026-10-02", "note": "Offer letter"}
    )
    assert r.status_code == 201 and r.json()["kind_label"] == "Letter mailed"
    client.post(
        f"/deals/{d['id']}/events",
        json={"kind": "call", "event_on": "2026-10-14", "note": "Owner wants comps"},
    )
    assert client.post(f"/deals/{d['id']}/events", json={"kind": "fax"}).status_code == 400
    full = client.get(f"/deals/{d['id']}").json()
    assert [e["kind"] for e in full["events"]] == ["letter", "call"]
    assert "TCPA" in full["outreach_note"] and "CAN-SPAM" in full["outreach_note"]
    rows = list(csv.DictReader(io.StringIO(client.get(f"/deals/{d['id']}/events?format=csv").text)))
    assert [x["note"] for x in rows] == ["Offer letter", "Owner wants comps"]
    assert len(client.get("/deals/events").json()) == 2
    eid = full["events"][0]["id"]
    assert client.delete(f"/deals/{d['id']}/events/{eid}").status_code == 204
    assert len(client.get(f"/deals/{d['id']}/events").json()) == 1


def test_csv_export_and_import_round_trip(client, monkeypatch):
    monkeypatch.setattr(deals_module, "feasibility", fake_feasibility)
    d = client.post("/deals", json={"pin": PIN, "exit": "sell", "overrides": {"all": {"land": 60000}}}).json()
    out = client.get("/deals?format=csv")
    assert out.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(out.text)))
    assert rows[0]["profit"] == "240000" and rows[0]["numbers_from"] == "saved feasibility run"
    assert rows[0]["max_land_price"] == "220000" and rows[0]["stage"] == "Lead"

    # Edit the export: move the deal to Contacted, and add a new row without an id.
    rows[0]["stage"] = "Contacted"
    rows[0]["notes"] = "Owner called back"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerow(rows[0])
    w.writerow(
        {**{k: "" for k in rows[0]}, "pin": "16-12-102-031-0000", "stage": "lead", "next_step": "Find owner"}
    )
    w.writerow({**{k: "" for k in rows[0]}, "pin": "1234", "stage": "lead"})
    r = client.post("/deals/import", content=buf.getvalue(), headers={"content-type": "text/csv"}).json()
    assert r["created"] == 1 and r["updated"] == 1 and len(r["errors"]) == 1 and "line 4" in r["errors"][0]
    got = client.get(f"/deals/{d['id']}").json()
    assert (
        got["stage"] == "contacted"
        and got["notes"] == "Owner called back"
        and got["overrides"] == {"all": {"land": 60000}}
    )
    deals = client.get("/deals").json()
    assert len(deals) == 2
    new = next(x for x in deals if x["id"] != d["id"])
    assert (
        new["next_step"] == "Find owner"
        and new["result"] is None
        and new["nightly"]["profit_central"] == 150000
    )

    assert (
        client.post("/deals/import", content="a,b\n1,2\n", headers={"content-type": "text/csv"}).status_code
        == 400
    )


def test_areas_and_tiles(client, db_url):
    areas = client.get("/community-areas").json()
    hp = next(a for a in areas if a["num"] == 23)
    assert hp["name"] == "Humboldt Park" and len(hp["bounds"]) == 4
    snap = client.get("/community-areas/23/snapshot").json()
    assert snap["land_value"]["per_lot_sqft"] == 40.5 and snap["land_value"]["sales"] == 12
    assert client.get("/community-areas/999/snapshot").status_code == 404

    # z14 tile over the lot holds its shape; z10 holds a point only when the score is 50 or more.
    def tile_xy(z, lon=-87.7095, lat=41.9005):
        import math

        n = 2**z
        x = int((lon + 180) / 360 * n)
        y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        return z, x, y

    with psycopg.connect(db_url) as conn:
        assert len(conn.execute("select lot_tiles(%s, %s, %s)", tile_xy(14)).fetchone()[0]) > 0
        assert len(conn.execute("select lot_tiles(%s, %s, %s)", tile_xy(10)).fetchone()[0]) > 0
        conn.execute("update parcel_score set score = 45")
        assert len(conn.execute("select lot_tiles(%s, %s, %s)", tile_xy(10)).fetchone()[0]) == 0
        assert len(conn.execute("select land_value_tiles(%s, %s, %s)", tile_xy(12)).fetchone()[0]) > 0
        assert conn.execute("select lot_for_sale_tiles(%s, %s, %s)", tile_xy(12)).fetchone()[0] is not None
