"""Desktop program: single-user local mode (LOCAL_MODE=1) and map tiles straight from the engine.
Named to run after test_db.py, which expects to apply the migrations first."""

import psycopg
import pytest
from fastapi.testclient import TestClient

import engine.app as app_module
from core.settings import settings
from db.migrate import migrate
from engine.auth import CLAIM_HEADER, make_claim

client = TestClient(app_module.app)


@pytest.fixture
def db(db_url, monkeypatch):
    migrate(db_url)
    monkeypatch.setattr(settings, "database_url", db_url)
    monkeypatch.setattr(settings, "local_user_email", "me@desktop.test.example")
    yield db_url
    with psycopg.connect(db_url) as conn:
        conn.execute("delete from account_user where email = 'me@desktop.test.example'")


def signed() -> dict:
    return {CLAIM_HEADER: make_claim(None, None)}


def test_local_session_is_off_unless_local_mode(db, monkeypatch):
    monkeypatch.setattr(settings, "local_mode", False)
    assert client.post("/auth/local-session", headers=signed()).status_code == 404


def test_local_session_needs_a_signed_call(db, monkeypatch):
    monkeypatch.setattr(settings, "local_mode", True)
    assert client.post("/auth/local-session").status_code == 401


def test_local_mode_refused_in_production(db, monkeypatch):
    monkeypatch.setattr(settings, "local_mode", True)
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "engine_shared_secret", "s" * 32)
    r = client.post("/auth/local-session", headers={CLAIM_HEADER: make_claim(None, None)})
    assert r.status_code == 500


def test_local_session_owns_default_org_on_pro(db, monkeypatch):
    monkeypatch.setattr(settings, "local_mode", True)
    first = client.post("/auth/local-session", headers=signed())
    assert first.status_code == 200, first.text
    s = first.json()
    assert s["local"] is True and s["is_admin"] is True
    assert s["org"]["id"] == "default" and s["org"]["plan"] == "pro" and s["org"]["role"] == "owner"
    assert "deals" in s["org"]["features"] and "exports" in s["org"]["features"]
    # Same user on every call.
    again = client.post("/auth/local-session", headers=signed()).json()
    assert again["user"]["id"] == s["user"]["id"]
    # The claim the web app then signs works on Pro routes: deals, exports and the admin feedback list.
    claim = {CLAIM_HEADER: make_claim(s["user"]["id"], "default", ttl=290)}
    assert client.get("/deals", headers=claim).status_code == 200
    assert (
        client.post("/exports", headers=claim, json={"kind": "pdf", "target": "16121020310000"}).status_code
        == 200
    )
    assert client.get("/feedback", headers=claim).status_code == 200


def test_local_session_takes_over_an_existing_owner(db, monkeypatch):
    monkeypatch.setattr(settings, "local_mode", True)
    with psycopg.connect(db) as conn:
        uid = conn.execute(
            "insert into account_user (email) values ('old-owner@test.example') on conflict (email)"
            " do update set email = excluded.email returning id"
        ).fetchone()[0]
        conn.execute("delete from membership where org_id = 'default'")
        conn.execute("insert into membership (org_id, user_id, role) values ('default', %s, 'owner')", (uid,))
    s = client.post("/auth/local-session", headers=signed()).json()
    assert s["org"]["role"] == "owner"
    with psycopg.connect(db) as conn:
        role = conn.execute(
            "select role from membership where org_id = 'default' and user_id = %s", (uid,)
        ).fetchone()[0]
        conn.execute("delete from account_user where id = %s", (uid,))
    assert role == "member"


def test_engine_tiles(db):
    assert client.get("/tiles/nope/14/4202/6087").status_code == 404
    assert client.get("/tiles/lots/14/99999/6087").status_code == 400
    assert client.get("/tiles/lots/5/8/11").status_code == 204  # below the layer's min zoom
    r = client.get("/tiles/lots/14/4202/6087")
    assert r.status_code in (200, 204)
    if r.status_code == 200:
        assert r.headers["content-type"] == "application/x-protobuf"
