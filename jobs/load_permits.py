"""Load City of Chicago building permits (ydr8-5enu), incrementally by issue date.

Run: python -m jobs.load_permits [--since 2014-01-01] [--limit N]
"""

import argparse

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, num, text, upsert

DATASET = "ydr8-5enu"
COLUMNS = [
    "id", "permit_no", "permit_type", "review_type", "permit_status", "permit_milestone",
    "application_start_date", "issue_date", "processing_days", "address", "work_type", "work_description",
    "reported_cost", "total_fee", "ward", "community_area_num", "census_tract", "pins", "x", "y",
    "source_pull_id",
]  # fmt: skip
# Permit coordinates are Illinois State Plane East (feet), EPSG:3435.
GEOM = {
    "geom": "case when x is not null and y is not null"
    " then st_transform(st_setsrid(st_makepoint(x::float8, y::float8), 3435), 4326) end"
}


def pins(pin_list) -> str | None:
    """'1602226037 | 1602226038' -> Postgres array literal of 14-digit PINs."""
    parts = [p.strip() for p in (text(pin_list) or "").split("|") if p.strip().isdigit()]
    full = [p + "0000" if len(p) == 10 else p for p in parts]
    return "{" + ",".join(full) + "}" if full else None


def address(r: dict) -> str | None:
    parts = [text(r.get(k)) for k in ("street_number", "street_direction", "street_name")]
    return " ".join(p for p in parts if p) or None


def to_row(r: dict, pull_id: int) -> tuple:
    return (
        text(r.get("id")),
        text(r.get("permit_")),
        text(r.get("permit_type")),
        text(r.get("review_type")),
        text(r.get("permit_status")),
        text(r.get("permit_milestone")),
        (text(r.get("application_start_date")) or "")[:10] or None,
        (text(r.get("issue_date")) or "")[:10] or None,
        integer(r.get("processing_time")),
        address(r),
        text(r.get("work_type")),
        text(r.get("work_description")),
        num(r.get("reported_cost")),
        num(r.get("total_fee")),
        integer(r.get("ward")),
        integer(r.get("community_area")),
        text(r.get("census_tract")),
        pins(r.get("pin_list")),
        text(r.get("xcoordinate")),
        text(r.get("ycoordinate")),
        pull_id,
    )


def where(since: str) -> str:
    return f"issue_date >= '{since}'"


def latest_since(conn) -> str:
    d = conn.execute("select max(issue_date) from permit").fetchone()[0]
    return d.isoformat() if d else "2014-01-01"


def run(
    since: str | None = None, limit: int | None = None, client: Socrata | None = None, url: str | None = None
) -> int:
    client = client or Socrata(CHICAGO)
    total = 0
    with connect(url) as conn:
        since = since or latest_since(conn)  # re-pull the latest day; upsert makes it safe
        pull_id = start_pull(conn, CHICAGO, DATASET, where(since))
        conn.commit()
        try:
            for page in client.pages(DATASET, order="id", where=where(since), page_size=limit or 50_000):
                total += upsert(conn, "permit", COLUMNS, "id", (to_row(r, pull_id) for r in page), GEOM)
                conn.commit()
                if limit:
                    break
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    print(f"permits loaded: {run(a.since, a.limit):,}")
