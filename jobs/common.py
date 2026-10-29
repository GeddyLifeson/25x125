"""Shared helpers for loaders: typed field parsing and bulk upsert through a temp table."""

from collections.abc import Iterable, Sequence

import psycopg


def text(v) -> str | None:
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def num(v) -> float | None:
    v = text(v)
    return float(v) if v is not None else None


def integer(v) -> int | None:
    v = num(v)
    return int(v) if v is not None else None


def boolean(v) -> bool | None:
    if isinstance(v, bool) or v is None:
        return v
    return str(v).strip().lower() in ("true", "1", "t", "yes")


def upsert(
    conn: psycopg.Connection,
    table: str,
    columns: Sequence[str],
    key: str,
    rows: Iterable[tuple],
    expressions: dict[str, str] | None = None,
) -> int:
    """COPY rows into a temp table, then insert or update the target on `key`.

    `expressions` maps a column to SQL that builds it from the staged columns (e.g. geometry from lon/lat).
    Rows that repeat a key keep one of them; loaders that need to combine repeats do it before calling.
    """
    expressions = expressions or {}
    conn.execute(f"create temp table stage on commit drop as select * from {table} with no data")
    for extra in {c for c in columns if c not in _table_columns(conn, table)}:
        conn.execute(f"alter table stage add column {extra} text")
    with conn.cursor().copy(f"copy stage ({', '.join(columns)}) from stdin") as cp:
        n = 0
        for r in rows:
            cp.write_row(r)
            n += 1
    target_cols = [c for c in _table_columns(conn, table) if c in columns or c in expressions]
    select = [expressions.get(c, c) for c in target_cols]
    updates = ", ".join(f"{c} = excluded.{c}" for c in target_cols if c != key)
    conn.execute(
        f"insert into {table} ({', '.join(target_cols)}) select distinct on ({key}) {', '.join(select)} from stage"
        f" on conflict ({key}) do update set {updates}"
    )
    conn.execute("drop table stage")
    return n


def _table_columns(conn: psycopg.Connection, table: str) -> list[str]:
    rows = conn.execute(
        "select column_name from information_schema.columns where table_name = %s order by ordinal_position",
        (table,),
    ).fetchall()
    return [r[0] for r in rows]
