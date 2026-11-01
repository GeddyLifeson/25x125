"""Sign-in, organizations and row-level security, plans, Stripe webhook, rate limits, audit log, deletion,
health freshness and the error hook (engine/auth.py, accounts.py, billing.py; migrations 0023-0026).
Named to run after test_db.py, which expects to apply the migrations first."""

import json
import time
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

import engine.app as app_module
import engine.auth as auth_module
import engine.billing as billing_module
import engine.deals as deals_module
import engine.mail as mail_module
from core import errors
from core.settings import settings
from db.migrate import migrate
from engine.auth import CLAIM_HEADER, Caller, make_claim, read_claim, scoped, sign_claim

PIN = "16121020310000"


@pytest.fixture
def db(db_url, monkeypatch, make_member, tmp_path):
    migrate(db_url)
    monkeypatch.setattr(deals_module, "connect", lambda: psycopg.connect(db_url))
    monkeypatch.setattr(mail_module, "DEV_MAIL", tmp_path)
    monkeypatch.setattr(settings, "email_server", "")
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate deal cascade")
        conn.execute("delete from parcel_address where pin = %s", (PIN,))
        conn.execute("delete from parcel where pin = %s", (PIN,))
        pull = conn.execute(
            "insert into source_pull (host, dataset_id, started_at, finished_at, status)"
            " values ('test', 'test-accounts', now(), now(), 'ok') returning id"
        ).fetchone()[0]
        conn.execute(
            """insert into parcel (pin, pin10, tax_year, municipality_id, community_area_num, community_area_name, geom,
                                   source_pull_id)
               values (%s, %s, 2025, 'chicago', 23, 'HUMBOLDT PARK', st_setsrid(st_point(-87.7095, 41.9005), 4326), %s)""",
            (PIN, PIN[:10], pull),
        )  # fmt: skip
    yield db_url
    with psycopg.connect(db_url) as conn:
        conn.execute("truncate deal cascade")
        conn.execute("delete from parcel where pin = %s", (PIN,))
        conn.execute("delete from source_pull where dataset_id = 'test-accounts' or note = 'test-saas'")


def client(headers: dict | None = None) -> TestClient:
    return TestClient(app_module.app, headers=headers or {})


def anon() -> dict:
    return {CLAIM_HEADER: make_claim(None, None)}


# ---- signed claims ----


def test_claims_verify_and_expire():
    v = make_claim("u1", "o1", ttl=60)
    assert read_claim(v)["org"] == "o1"
    body, sig = v.rsplit(".", 1)
    assert read_claim(body + "." + sig[:-2] + "AA") is None
    assert (
        read_claim(sign_claim({"uid": "u1", "org": "o1", "exp": int(time.time()) + 60}, secret="other"))
        is None
    )
    assert read_claim(sign_claim({"uid": "u1", "org": "o1", "exp": int(time.time()) - 1})) is None
    assert read_claim(sign_claim({"uid": "u1", "org": "o1", "exp": int(time.time()) + 3600})) is None


def test_protected_routes_reject_unsigned_and_forged(db, make_member):
    make_member("a@test.example", "test-a")
    assert client().get("/deals").status_code == 401
    forged = {
        CLAIM_HEADER: sign_claim({"uid": "x", "org": "test-a", "exp": int(time.time()) + 60}, secret="guess")
    }
    assert client(forged).get("/deals").status_code == 401
    # A forged claim is refused even on a public route; no claim at all is fine there.
    assert client(forged).get("/health").status_code == 200  # health takes no claim
    assert client(forged).get("/search?q=624 N Troy").status_code == 401
    assert client().get("/search?q=624 N Troy").status_code == 200
    # A valid signature for an organization the user is not in.
    b = make_member("b@test.example", "test-b")
    uid_b = read_claim(b[CLAIM_HEADER])["uid"]
    assert client({CLAIM_HEADER: make_claim(uid_b, "test-a")}).get("/deals").status_code == 403
    # Signed but signed out.
    assert client(anon()).get("/deals").status_code == 401


def test_one_org_cannot_read_another_orgs_deals(db, make_member):
    a = client(make_member("a@test.example", "test-a"))
    b = client(make_member("b@test.example", "test-b"))
    d = a.post("/deals", json={"pin": PIN, "notes": "org A only"}).json()
    a.post(f"/deals/{d['id']}/events", json={"kind": "call", "note": "A called"})
    assert [x["id"] for x in a.get("/deals").json()] == [d["id"]]

    assert b.get("/deals").json() == []
    assert b.get("/deals/pipeline").json()["total"] == 0
    assert b.get("/deals/events").json() == []
    assert b.get(f"/deals/{d['id']}").status_code == 404
    assert b.patch(f"/deals/{d['id']}", json={"stage": "passed"}).status_code == 404
    assert b.post(f"/deals/{d['id']}/events", json={"kind": "note"}).status_code == 404
    assert b.delete(f"/deals/{d['id']}").status_code == 404
    assert a.get(f"/deals/{d['id']}").json()["stage"] == "lead"

    # Straight SQL in org B's scope: no where clause, still nothing of org A; writing A's org id is refused.
    with psycopg.connect(db) as conn:
        uid_b = conn.execute("select id from account_user where email = 'b@test.example'").fetchone()[0]
    cb = Caller(True, "127.0.0.1", uid_b, "test-b")
    with scoped(psycopg.connect(db), cb) as conn:
        assert conn.execute("select count(*) from deal").fetchone()[0] == 0
        assert conn.execute("select count(*) from deal_event").fetchone()[0] == 0
        assert conn.execute("select count(*) from audit_log").fetchone()[0] == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege), scoped(psycopg.connect(db), cb) as conn:
        conn.execute("insert into deal (org_id, pin, pin10) values ('test-a', %s, %s)", (PIN, PIN[:10]))
    with scoped(psycopg.connect(db), cb) as conn:
        assert conn.execute("update deal set notes = 'x' returning id").fetchall() == []


def test_backfill_puts_old_deals_in_the_default_org(db):
    with psycopg.connect(db) as conn:
        assert conn.execute("select plan, plan_status from org where id = 'default'").fetchone() == (
            "pro",
            "comp",
        )
        # A deal written without an org scope fails: org_id is required.
        with pytest.raises(psycopg.errors.NotNullViolation):
            conn.execute("insert into deal (pin, pin10) values (%s, %s)", (PIN, PIN[:10]))


def test_plan_gates_deals(db, make_member):
    free = client(make_member("f@test.example", "test-free", plan="free", status="none"))
    r = free.get("/deals")
    assert r.status_code == 402 and "Pro" in r.json()["detail"]
    with psycopg.connect(db) as conn:
        conn.execute(
            "update org set plan = 'pro', plan_status = 'trialing', trial_ends_at = now() + interval '3 days'"
            " where id = 'test-free'"
        )
    assert free.get("/deals").status_code == 200
    with psycopg.connect(db) as conn:
        conn.execute("update org set trial_ends_at = now() - interval '1 minute' where id = 'test-free'")
    assert free.get("/deals").status_code == 402
    assert auth_module.effective_plan("pro", "past_due", None) == "pro"
    assert auth_module.effective_plan("pro", "canceled", None) == "free"


# ---- email sign-in ----


def _link_token(tmp_dir, email: str) -> str:
    text = (tmp_dir / f"{email}.txt").read_text()
    return text.split("token=")[1].split()[0]


def test_magic_link_sign_in_trial_and_invites(db, make_member, tmp_path):
    svc = client(anon())
    assert (
        client()
        .post("/auth/email-link", json={"email": "x@test.example", "base_url": "http://w"})
        .status_code
        == 401
    )
    assert (
        svc.post("/auth/email-link", json={"email": "not an email", "base_url": "http://w"}).status_code
        == 400
    )
    r = svc.post(
        "/auth/email-link",
        json={"email": "New@Test.example", "base_url": "http://localhost:3030", "next": "/deals"},
    )
    assert r.json() == {"sent": False, "dev_mode": True}
    text = (tmp_path / "new@test.example.txt").read_text()
    assert "http://localhost:3030/api/auth/callback?token=" in text and "expires in 30 minutes" in text
    token = _link_token(tmp_path, "new@test.example")

    v = svc.post("/auth/verify", json={"token": token})
    assert v.status_code == 200 and v.json()["next"] == "/deals"
    assert svc.post("/auth/verify", json={"token": token}).status_code == 400  # one use
    s = svc.post("/auth/session", json={"session_token": v.json()["session_token"]}).json()
    assert s["user"]["email"] == "new@test.example"
    org = s["org"]
    assert org["role"] == "owner" and org["plan"] == "pro" and org["plan_status"] == "trialing"
    ends = datetime.fromisoformat(org["trial_ends_at"])
    assert timedelta(days=13.9) < ends - datetime.now(UTC) < timedelta(days=14.1)
    assert "deals" in org["features"] and "exports" in org["features"]
    assert svc.post("/auth/session", json={"session_token": "nope"}).status_code == 401

    # The owner invites a teammate; the teammate signs in and lands in the owner's organization.
    owner = client({CLAIM_HEADER: make_claim(s["user"]["id"], org["id"], ttl=290)})
    inv = owner.post(
        "/account/invites", json={"email": "mate@test.example", "base_url": "http://localhost:3030"}
    )
    assert inv.status_code == 201
    assert "added you to" in (tmp_path / "mate@test.example.txt").read_text()
    svc.post("/auth/email-link", json={"email": "mate@test.example", "base_url": "http://w"})
    v2 = svc.post("/auth/verify", json={"token": _link_token(tmp_path, "mate@test.example")}).json()
    s2 = svc.post("/auth/session", json={"session_token": v2["session_token"]}).json()
    assert s2["org"]["id"] == org["id"] and s2["org"]["role"] == "member" and len(s2["orgs"]) == 1
    acct = owner.get("/account").json()
    assert [m["role"] for m in acct["members"]] == ["owner", "member"] and acct["invites"] == []
    mate = client({CLAIM_HEADER: make_claim(s2["user"]["id"], org["id"])})
    assert (
        mate.post("/account/invites", json={"email": "z@test.example", "base_url": "http://w"}).status_code
        == 403
    )

    # Both see the shared deals; sign-out ends the session.
    d = owner.post("/deals", json={"pin": PIN}).json()
    assert [x["id"] for x in mate.get("/deals").json()] == [d["id"]]
    svc.post("/auth/signout", json={"session_token": v2["session_token"]})
    assert svc.post("/auth/session", json={"session_token": v2["session_token"]}).status_code == 401


def test_sign_in_link_rate_limit(db, monkeypatch):
    monkeypatch.setattr(auth_module, "_limits", lambda: {"sign_in_ip": {"burst": 100, "per_hour": 1},
                                                         "sign_in_email": {"burst": 2, "per_hour": 1}})  # fmt: skip
    svc = client(anon())
    body = {"email": "limit@test.example", "base_url": "http://w"}
    assert [svc.post("/auth/email-link", json=body).status_code for _ in range(3)] == [200, 200, 429]
    r = svc.post("/auth/email-link", json=body)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


# ---- rate limits, audit log, exports ----


def test_search_rate_limit_per_caller(db, monkeypatch, make_member):
    monkeypatch.setattr(auth_module, "_limits", lambda: {"search": {"burst": 2, "per_hour": 1}})
    a = client({CLAIM_HEADER: make_claim(None, None, ip="10.0.0.1")})
    b = client({CLAIM_HEADER: make_claim(None, None, ip="10.0.0.2")})
    assert [a.get("/search?q=624 N Troy").status_code for _ in range(3)] == [200, 200, 429]
    assert b.get("/search?q=624 N Troy").status_code == 200


def test_audit_log_and_export_gate(db, make_member):
    a = client(make_member("a@test.example", "test-a"))
    d = a.post("/deals", json={"pin": PIN}).json()
    a.patch(f"/deals/{d['id']}", json={"stage": "contacted"})
    a.put(f"/overrides/{PIN}", json={"exit": "sell", "overrides": {"all": {"land": 60000}}})
    assert a.get("/deals?format=csv").status_code == 200
    assert a.post("/exports", json={"kind": "pdf", "target": f"PIN {PIN}"}).json() == {"ok": True}
    assert a.post("/exports", json={"kind": "zip"}).status_code == 400
    log = a.get("/account/audit").json()
    actions = [x["action"] for x in log]
    for want in ("deal.create", "deal.update", "override.save", "export.deals_csv", "export.pdf"):
        assert want in actions
    assert all(x["who"] == "a@test.example" for x in log)
    assert next(x for x in log if x["action"] == "override.save")["detail"]["overrides"] == {
        "all": {"land": 60000}
    }

    free = client(make_member("f@test.example", "test-free", plan="free", status="none"))
    assert free.post("/exports", json={"kind": "pdf"}).status_code == 402
    assert client(anon()).get("/lots?format=csv").status_code == 401


def test_saved_overrides_and_searches_stay_in_the_org(db, make_member):
    a = client(make_member("a@test.example", "test-a"))
    b = client(make_member("b@test.example", "test-b"))
    assert a.get(f"/overrides/{PIN}").status_code == 404
    r = a.put(f"/overrides/{PIN}", json={"exit": "hold", "overrides": {"0": {"units": 4}}}).json()
    assert r["overrides"] == {"0": {"units": 4}} and r["updated_by"] == "a@test.example"
    assert b.get(f"/overrides/{PIN}").status_code == 404
    s = a.post(
        "/saved-searches", json={"name": "Humboldt Park 50+", "params": "?community_area=23&min_score=50"}
    )
    assert s.status_code == 201 and s.json()["params"] == "community_area=23&min_score=50"
    assert len(a.get("/saved-searches").json()) == 1 and b.get("/saved-searches").json() == []
    assert b.delete(f"/saved-searches/{s.json()['id']}").status_code == 404
    assert a.delete(f"/saved-searches/{s.json()['id']}").status_code == 204


# ---- Stripe ----

SUB_EVENT = {
    "id": "evt_test_sub_1",
    "type": "customer.subscription.updated",
    "created": 1793548800,
    "data": {
        "object": {
            "id": "sub_test_1",
            "object": "subscription",
            "customer": "cus_test_1",
            "status": "active",
            "metadata": {"org_id": "test-a"},
            "trial_end": None,
            "items": {"data": [{"price": {"id": "price_pro_test"}, "current_period_end": 1796227200}]},
        }
    },
}


def test_webhook_verifies_signature_and_sets_plan(db, make_member, monkeypatch):
    make_member("a@test.example", "test-a", plan="free", status="none")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_local")
    payload = json.dumps(SUB_EVENT).encode()
    good = billing_module.signature_header(payload, "whsec_test_local")
    c = client()
    assert (
        c.post("/billing/webhook", content=payload, headers={"stripe-signature": "t=1,v1=00"}).status_code
        == 400
    )
    bad = billing_module.signature_header(payload, "whsec_wrong")
    assert c.post("/billing/webhook", content=payload, headers={"stripe-signature": bad}).status_code == 400
    old = billing_module.signature_header(payload, "whsec_test_local", t=int(time.time()) - 600)
    assert c.post("/billing/webhook", content=payload, headers={"stripe-signature": old}).status_code == 400

    r = c.post("/billing/webhook", content=payload, headers={"stripe-signature": good})
    assert r.status_code == 200 and r.json()["org_id"] == "test-a"
    with psycopg.connect(db) as conn:
        row = conn.execute(
            "select plan, plan_status, stripe_customer_id, stripe_subscription_id, stripe_price_id,"
            " current_period_end from org where id = 'test-a'"
        ).fetchone()
    assert row[:5] == ("pro", "active", "cus_test_1", "sub_test_1", "price_pro_test")
    assert row[5] == datetime.fromtimestamp(1796227200, UTC)
    # The same event again changes nothing.
    assert (
        c.post("/billing/webhook", content=payload, headers={"stripe-signature": good}).json()["org_id"]
        is None
    )

    # Cancellation, found by customer id; an older event arriving late does not undo it.
    gone = {**SUB_EVENT, "id": "evt_test_sub_2", "type": "customer.subscription.deleted", "created": 1793552400,
            "data": {"object": {**SUB_EVENT["data"]["object"], "metadata": {}, "status": "canceled"}}}  # fmt: skip
    p2 = json.dumps(gone).encode()
    c.post(
        "/billing/webhook",
        content=p2,
        headers={"stripe-signature": billing_module.signature_header(p2, "whsec_test_local")},
    )
    late = {**SUB_EVENT, "id": "evt_test_sub_0", "created": 1793545200}
    p3 = json.dumps(late).encode()
    c.post(
        "/billing/webhook",
        content=p3,
        headers={"stripe-signature": billing_module.signature_header(p3, "whsec_test_local")},
    )
    with psycopg.connect(db) as conn:
        assert conn.execute("select plan, plan_status from org where id = 'test-a'").fetchone() == (
            "free",
            "canceled",
        )
        conn.execute("delete from stripe_event where id like 'evt_test_%'")


def test_checkout_has_tax_trial_and_founding_price(db, make_member, monkeypatch):
    calls = []

    def fake(method, path, params=None):
        calls.append((method, path, params))
        return {"id": "cus_new"} if path == "/customers" else {"url": "https://checkout.stripe.test/s"}

    monkeypatch.setattr(billing_module, "stripe_call", fake)
    monkeypatch.setattr(settings, "stripe_price_pro_monthly", "price_pro")
    monkeypatch.setattr(settings, "stripe_price_founding_monthly", "price_founding")
    h = make_member("a@test.example", "test-a", plan="pro", status="trialing")
    with psycopg.connect(db) as conn:
        conn.execute(
            "update org set trial_ends_at = now() + interval '10 days', founding = true where id = 'test-a'"
        )
    r = client(h).post("/billing/checkout", json={"base_url": "http://localhost:3030"})
    assert r.json() == {"url": "https://checkout.stripe.test/s"}
    params = calls[-1][2]
    assert params["automatic_tax[enabled]"] == "true" and params["line_items[0][price]"] == "price_founding"
    assert params["customer"] == "cus_new" and params["client_reference_id"] == "test-a"
    assert params["subscription_data[trial_end]"] > time.time() + 9 * 86400
    member = make_member("m@test.example", "test-a", role="member")
    assert client(member).post("/billing/checkout", json={"base_url": "http://w"}).status_code == 403


def test_billing_without_keys_says_so(db, make_member, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "stripe_price_pro_monthly", "price_pro")
    h = make_member("a@test.example", "test-a")
    r = client(h).post("/billing/checkout", json={"base_url": "http://w"})
    assert r.status_code == 503 and "STRIPE_SECRET_KEY" in r.json()["detail"]
    plans = client().get("/billing/plans").json()
    assert plans["plans"]["pro"]["price_month"] == 129 and plans["plans"]["pro"]["founding_price_month"] == 79
    assert plans["trial_days"] == 14 and plans["billing_ready"] is False


# ---- deletion ----


def test_delete_account_removes_owned_org_data(db, make_member):
    a_h = make_member("a@test.example", "test-a")
    m_h = make_member("m@test.example", "test-a", role="member")
    other = client(make_member("o@test.example", "test-o"))
    a = client(a_h)
    d = a.post("/deals", json={"pin": PIN}).json()
    a.post(f"/deals/{d['id']}/events", json={"kind": "note", "note": "x"})
    a.put(f"/overrides/{PIN}", json={"overrides": {}})
    keep = other.post("/deals", json={"pin": PIN}).json()

    assert a.delete("/account?confirm=wrong@test.example").status_code == 400
    r = a.delete("/account?confirm=a@test.example").json()
    assert r["orgs_deleted"] == 1 and r["rows_deleted"]["deal"] == 1 and r["rows_deleted"]["deal_event"] == 1
    assert r["rows_deleted"]["other_members"] == 1
    with psycopg.connect(db) as conn:
        assert conn.execute("select count(*) from org where id = 'test-a'").fetchone()[0] == 0
        assert (
            conn.execute("select count(*) from account_user where email = 'a@test.example'").fetchone()[0]
            == 0
        )
        assert (
            conn.execute("select count(*) from account_user where email = 'm@test.example'").fetchone()[0]
            == 1
        )
        assert conn.execute("select count(*) from deal where org_id = 'test-a'").fetchone()[0] == 0
        assert (
            conn.execute("select count(*) from deletion_log where requested_by = 'self'").fetchone()[0] >= 1
        )
    assert [x["id"] for x in other.get("/deals").json()] == [keep["id"]]
    assert client(m_h).get("/deals").status_code == 403  # the org is gone


# ---- health and errors ----


def test_health_flags_stale_nightly_sources(db, monkeypatch):
    monkeypatch.setattr(app_module, "connect", lambda: psycopg.connect(db))
    fresh_rules = {
        **app_module.FRESHNESS,
        "nightly_datasets": ["test-nightly"],
        "labels": {"test-nightly": "building permits"},
    }
    monkeypatch.setattr(app_module, "FRESHNESS", fresh_rules)
    with psycopg.connect(db) as conn:
        conn.execute(
            "insert into source_pull (host, dataset_id, started_at, finished_at, status, note) values ('data.cityofchicago.org',"
            " 'test-nightly', now() - interval '40 hours', now() - interval '40 hours', 'ok', 'test-saas')"
        )
    body = client().get("/health").json()
    assert body["status"] == "stale" and body["stale_after_hours"] == 36
    stale = {s["dataset_id"]: s for s in body["stale"]}
    assert stale["test-nightly"]["label"] == "building permits" and stale["test-nightly"]["hours_old"] >= 40
    fresh = next(s for s in body["sources"] if s["dataset_id"] == "test-accounts")
    assert fresh["stale"] is False


def test_error_hook_is_a_no_op_without_dsn(monkeypatch):
    monkeypatch.setattr(settings, "sentry_dsn", "")
    assert errors.report(ValueError("x")) is False
    assert errors._endpoint("https://abc@o1.ingest.sentry.io/42") == (
        "https://o1.ingest.sentry.io/api/42/envelope/",
        "abc",
    )
    try:
        raise RuntimeError("boom")
    except RuntimeError as e:
        body = errors.envelope(e, {"path": "/x"}).decode().splitlines()
    event = json.loads(body[2])
    assert event["exception"]["values"][0]["type"] == "RuntimeError" and event["extra"] == {"path": "/x"}


def test_delete_account_script(db, make_member, capsys):
    from jobs import delete_account

    make_member("s@test.example", "test-s")
    assert delete_account.main(["s@test.example"]) == 0
    assert "nothing deleted" in capsys.readouterr().out
    assert delete_account.main(["s@test.example", "--confirm"]) == 0
    assert '"orgs_deleted": 1' in capsys.readouterr().out
    assert delete_account.main(["s@test.example"]) == 1
