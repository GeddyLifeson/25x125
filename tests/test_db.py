import psycopg

from core.sources import finish_pull, start_pull
from db.migrate import migrate


def test_migrations_apply_once_and_postgis_works(db_url):
    assert "0001_init.sql" in migrate(db_url)
    assert migrate(db_url) == []
    with psycopg.connect(db_url) as conn:
        assert conn.execute("select postgis_version()").fetchone()[0]
        assert conn.execute("select name from municipality where loaded").fetchall() == [("Chicago",)]


def test_source_pull_is_recorded(db_url):
    migrate(db_url)
    with psycopg.connect(db_url) as conn:
        pid = start_pull(conn, "data.cityofchicago.org", "ydr8-5enu", "$limit=1")
        finish_pull(conn, pid, 1)
        row = conn.execute(
            "select status, row_count, finished_at is not null from source_pull where id = %s", (pid,)
        )
        assert row.fetchone() == ("ok", 1, True)
