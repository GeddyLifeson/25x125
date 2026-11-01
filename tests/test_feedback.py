"""Feedback on the app's numbers (engine/feedback.py, migration 0027): who may send and read it, validation,
the rate limit, the audit log, the CSV and the summary of how far the app's figures are from people's own."""

import csv
import io

import psycopg
import pytest
from fastapi.testclient import TestClient

import engine.app as app_module
import engine.auth as auth_module
from core.settings import settings
from db.migrate import migrate
from engine.auth import CLAIM_HEADER, make_claim, token_hash

SNAP = {"total_cost": 1_200_000, "cost_per_unit": 400_000, "hard_cost_per_sqft": 180, "total_cost_per_sqft": 300,
        "sale_per_unit": 500_000, "profit": 150_000, "max_land_price": 90_000, "preset": "production",
        "cost_index": 1.04, "exit": "sell", "units": 3}  # fmt: skip


@pytest.fixture
def db(db_url, make_member, monkeypatch):
    migrate(db_url)
    monkeypatch.setattr(settings, "admin_emails", "Boss@test.example, other@test.example")
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate feedback")
        conn.execute("truncate rate_bucket")
    yield db_url
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate feedback")


def client(headers: dict | None = None) -> TestClient:
    return TestClient(app_module.app, headers=headers or {})


def anon(ip: str = "127.0.0.1") -> TestClient:
    return client({CLAIM_HEADER: make_claim(None, None, ip=ip)})


def test_signed_in_feedback_saved_with_snapshot_and_audited(db, make_member):
    a = client(make_member("builder@test.example", "test-fb"))
    body = {"pin": "16-12-102-031-0000", "scenario": "B", "page_path": "/parcels/16121020310000/feasibility",
            "rating": 4, "cost_per_sqft_own": 210, "cost_total_own": 1_300_000, "sale_per_unit_own": 450_000,
            "numbers_wrong": "Soft cost looks low", "outside_questions": "Utility tap fees", "missing": "Demolition",
            "minutes_spent": 25, "would_use": "maybe", "notes": "  ", "app_snapshot": SNAP}  # fmt: skip
    r = a.post("/feedback", json=body)
    assert r.status_code == 201, r.text
    with psycopg.connect(db) as conn:
        row = conn.execute(
            "select email, org_id, pin, scenario, screen, rating, cost_per_sqft_own, notes, app_snapshot"
            " from feedback where id = %s",
            (r.json()["id"],),
        ).fetchone()
        assert row[:6] == ("builder@test.example", "test-fb", "16121020310000", "B", "feasibility", 4)
        assert float(row[6]) == 210 and row[7] is None
        assert row[8]["hard_cost_per_sqft"] == 180 and row[8]["preset"] == "production"
        conn.execute("select set_config('app.org_id', 'test-fb', false)")
        act = conn.execute("select action, target from audit_log where org_id = 'test-fb'").fetchall()
    assert ("feedback.create", f"feedback {r.json()['id']}") in act


def test_signed_out_needs_email_and_signed_request(db):
    body = {"rating": 3, "notes": "General note"}
    assert client().post("/feedback", json=body).status_code == 401  # not from the web app
    r = anon().post("/feedback", json=body)
    assert r.status_code == 400 and "email" in r.json()["detail"]
    assert anon().post("/feedback", json={**body, "email": "not an email"}).status_code == 400
    r = anon().post("/feedback", json={**body, "email": " Visitor@Test.Example "})
    assert r.status_code == 201
    with psycopg.connect(db) as conn:
        row = conn.execute("select email, user_id, org_id, screen from feedback").fetchone()
    assert row == ("visitor@test.example", None, None, "general")


@pytest.mark.parametrize(
    "bad",
    [
        {"rating": 6},
        {"rating": 0},
        {"scenario": "D", "rating": 3},
        {"would_use": "sure", "rating": 3},
        {"cost_per_sqft_own": -5},
        {"minutes_spent": 5000, "rating": 3},
        {"pin": "123", "rating": 3},
        {"numbers_wrong": "x" * 5000},
        {"rating": 3, "app_snapshot": {"total_cost": "lots"}},
        {},  # nothing answered
    ],
)
def test_validation(db, bad):
    r = anon().post("/feedback", json={"email": "v@test.example", **bad})
    assert r.status_code in (400, 422), (bad, r.status_code)


def test_rate_limited(db, monkeypatch):
    monkeypatch.setattr(auth_module, "_limits", lambda: {"feedback": {"burst": 2, "per_hour": 1}})
    body = {"email": "v@test.example", "rating": 2}
    codes = [anon("10.1.1.1").post("/feedback", json=body).status_code for _ in range(3)]
    assert codes == [201, 201, 429]
    assert anon("10.1.1.2").post("/feedback", json=body).status_code == 201


def test_admin_only_reads(db, make_member):
    member = client(make_member("builder@test.example", "test-fb"))
    boss = client(make_member("boss@test.example", "test-boss"))
    for path in ("/feedback", "/feedback/summary", "/feedback.csv"):
        assert anon().get(path).status_code == 401
        assert member.get(path).status_code == 403
        assert boss.get(path).status_code == 200
    # A forged claim for the admin's user id does not pass.
    uid = make_claim("x", "y").split(".")[0]
    assert client({CLAIM_HEADER: uid + ".bad"}).get("/feedback").status_code == 401


def test_session_says_admin(db, make_member):
    make_member("boss@test.example", "test-boss")
    make_member("builder@test.example", "test-fb")
    with psycopg.connect(db) as conn:
        for email, org, tok in [
            ("boss@test.example", "test-boss", "fb-a"),
            ("builder@test.example", "test-fb", "fb-b"),
        ]:
            uid = conn.execute("select id from account_user where email = %s", (email,)).fetchone()[0]
            conn.execute(
                "insert into auth_session (token_hash, user_id, org_id, expires_at)"
                " values (%s, %s, %s, now() + interval '1 day')",
                (token_hash(tok), uid, org),
            )
    assert anon().post("/auth/session", json={"session_token": "fb-a"}).json()["is_admin"] is True
    assert anon().post("/auth/session", json={"session_token": "fb-b"}).json()["is_admin"] is False


def test_summary_ratios_and_dollars(db, make_member):
    boss = client(make_member("boss@test.example", "test-boss"))
    a = anon()
    entries = [
        {"rating": 2, "cost_per_sqft_own": 216, "sale_per_unit_own": 450_000, "would_use": "yes"},  # 1.2, 0.9
        {"rating": 4, "cost_per_sqft_own": 180, "cost_total_own": 1_500_000, "would_use": "maybe"},  # 1.0
        {"rating": 5, "cost_per_sqft_own": 144, "minutes_spent": 30},  # 0.8
        {"rating": 3, "notes": "no numbers"},
    ]
    for e in entries:
        assert (
            a.post("/feedback", json={"email": "v@test.example", "app_snapshot": SNAP, **e}).status_code
            == 201
        )
    a.post(
        "/feedback", json={"email": "v@test.example", "rating": 1, "cost_per_sqft_own": 200}
    )  # no snapshot
    s = boss.get("/feedback/summary").json()
    assert s["count"] == 5 and s["rating"] == {"n": 5, "median": 3}
    c = s["comparisons"]["cost_per_sqft"]
    assert c["n"] == 3 and c["ratio"] == {"median": 1.0, "low": 0.8, "high": 1.2}
    assert c["difference"] == {"median": 0, "low": -36, "high": 36}
    assert c["own_median"] == 180 and c["app_median"] == 180
    sale = s["comparisons"]["sale_per_unit"]
    assert sale["n"] == 1 and sale["ratio"]["median"] == 0.9 and sale["difference"]["median"] == -50_000
    assert s["comparisons"]["cost_total"]["ratio"]["median"] == 1.25
    assert s["would_use"] == {"yes": 1, "maybe": 1, "no": 0}
    assert s["minutes_spent"] == {"n": 1, "total": 30}

    rows = boss.get("/feedback").json()
    assert len(rows) == 5 and rows[0]["rating"] == 1  # newest first
    assert rows[-1]["comparisons"]["cost_per_sqft"] == {
        "own": 216,
        "app": 180,
        "difference": 36,
        "ratio": 1.2,
    }

    r = boss.get("/feedback.csv")
    assert r.headers["content-type"].startswith("text/csv")
    table = list(csv.DictReader(io.StringIO(r.text)))
    assert len(table) == 5
    first = next(t for t in table if t["cost_per_sqft_own"] == "216")
    assert first["app_hard_cost_per_sqft"] == "180" and first["cost_per_sqft_ratio"] == "1.2"
    with psycopg.connect(db) as conn:
        conn.execute("select set_config('app.org_id', 'test-boss', false)")
        assert (
            conn.execute(
                "select count(*) from audit_log where org_id = 'test-boss' and action = 'export.feedback_csv'"
            ).fetchone()[0]
            == 1
        )

    gone = rows[0]["id"]
    assert (
        client(make_member("builder@test.example", "test-fb")).delete(f"/feedback/{gone}").status_code == 403
    )
    assert boss.delete(f"/feedback/{gone}").status_code == 204
    assert boss.delete(f"/feedback/{gone}").status_code == 404
    assert boss.get("/feedback/summary").json()["count"] == 4


def test_restricted_role_cannot_read_feedback(db):
    anon().post("/feedback", json={"email": "v@test.example", "rating": 3})
    with psycopg.connect(db) as conn:
        conn.execute("set role x25_app")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select count(*) from feedback")


def test_account_deletion_removes_email_from_feedback(db, make_member):
    from engine.accounts import delete_user

    a = client(make_member("leaving@test.example", "test-leave"))
    assert a.post("/feedback", json={"rating": 4}).status_code == 201
    with psycopg.connect(db) as conn:
        uid = conn.execute("select id from account_user where email = 'leaving@test.example'").fetchone()[0]
        out = delete_user(conn, uid, "self")
        left = conn.execute("select email, user_id, rating from feedback").fetchall()
    assert out["rows_deleted"]["feedback_anonymized"] == 1
    assert left == [(None, None, 4)]
