"""Record every pull from an outside source, so each stored value can show where it came from and when."""

from datetime import UTC, datetime

import psycopg


def start_pull(conn: psycopg.Connection, host: str, dataset_id: str, query: str = "") -> int:
    row = conn.execute(
        "insert into source_pull (host, dataset_id, query, started_at, status)"
        " values (%s, %s, %s, %s, 'running') returning id",
        (host, dataset_id, query, datetime.now(UTC)),
    ).fetchone()
    return row[0]


def finish_pull(
    conn: psycopg.Connection, pull_id: int, row_count: int, status: str = "ok", note: str = ""
) -> None:
    conn.execute(
        "update source_pull set finished_at = %s, row_count = %s, status = %s, note = %s where id = %s",
        (datetime.now(UTC), row_count, status, note, pull_id),
    )
