"""Seed the rule table from data/rules so screens and the nightly scorer read one copy.

Each run replaces the rule sets it seeds. A rule change is an edit to the file followed by this job.
Run: python -m jobs.seed_rules
"""

from psycopg.types.json import Jsonb

from core.db import connect
from engine.rules import rows_from_files


def run(url: str | None = None) -> int:
    data = rows_from_files()
    sets = sorted({r[0] for r in data})
    with connect(url) as conn:
        conn.execute("delete from rule where rule_set = any(%s)", (sets,))
        with conn.cursor() as cur:
            cur.executemany(
                "insert into rule (rule_set, rule_key, value, section, source_url, source_file,"
                " effective_from, effective_to, verified_on) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [(r[0], r[1], Jsonb(r[2]), *r[3:]) for r in data],
            )
    return len(data)


if __name__ == "__main__":
    print(f"rules seeded: {run()}")
