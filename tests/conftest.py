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
