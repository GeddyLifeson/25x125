"""Apply SQL migrations in db/migrations in name order, once each.

Run: python -m db.migrate
"""

import sys
from pathlib import Path

from core.db import connect

MIGRATIONS = Path(__file__).parent / "migrations"


def migrate(url: str | None = None) -> list[str]:
    applied = []
    with connect(url) as conn:
        conn.execute(
            "create table if not exists schema_migration (name text primary key, applied_at timestamptz default now())"
        )
        done = {r[0] for r in conn.execute("select name from schema_migration")}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text())
            conn.execute("insert into schema_migration (name) values (%s)", (path.name,))
            applied.append(path.name)
    return applied


if __name__ == "__main__":
    names = migrate(sys.argv[1] if len(sys.argv) > 1 else None)
    print("applied:", ", ".join(names) if names else "nothing new")
