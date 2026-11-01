import os

import psycopg
import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/x25x125_test")


def _admin_url(url: str) -> str:
    return url.rsplit("/", 1)[0] + "/postgres"


@pytest.fixture(scope="session")
def db_url():
    """A fresh test database on the local PostGIS server; tests that need it skip if none is running."""
    name = TEST_DB.rsplit("/", 1)[1]
    try:
        with psycopg.connect(_admin_url(TEST_DB), autocommit=True, connect_timeout=3) as conn:
            conn.execute(f'drop database if exists "{name}"')
            conn.execute(f'create database "{name}"')
    except psycopg.OperationalError:
        pytest.skip("no local database (run: docker compose up -d)")
    yield TEST_DB


@pytest.fixture
def make_member(db_url, monkeypatch):
    """Create a user in an organization and return the signed claim header the web app would send.

    Points the engine's database settings at the test database for the test's length."""
    from core.settings import settings
    from engine.auth import CLAIM_HEADER, make_claim

    monkeypatch.setattr(settings, "database_url", db_url)

    def make(email: str, org_id: str, role: str = "owner", plan: str = "pro", status: str = "comp") -> dict:
        with psycopg.connect(db_url) as conn:
            conn.execute(
                "insert into org (id, name, plan, plan_status) values (%s, %s, %s, %s) on conflict (id) do update"
                " set plan = excluded.plan, plan_status = excluded.plan_status",
                (org_id, org_id, plan, status),
            )
            uid = conn.execute(
                "insert into account_user (email) values (%s) on conflict (email) do update set email = excluded.email"
                " returning id",
                (email,),
            ).fetchone()[0]
            conn.execute(
                "insert into membership (org_id, user_id, role) values (%s, %s, %s) on conflict do nothing",
                (org_id, uid, role),
            )
        return {CLAIM_HEADER: make_claim(uid, org_id, ttl=290)}

    yield make
    with psycopg.connect(db_url) as conn:
        conn.execute("delete from org where id like 'test-%' or name like '%@test.example'")
        conn.execute("delete from account_user where email like '%@test.example'")
        conn.execute("truncate rate_bucket")
