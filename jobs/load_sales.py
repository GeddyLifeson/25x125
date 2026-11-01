"""Load recorded sales for Chicago townships from the Assessor (wvhk-k5uv).

Pulls sales since --since (default: the day after the latest stored sale, or 2014-01-01 on an empty table).
Run: python -m jobs.load_sales [--since 2014-01-01] [--limit N]
"""

import argparse

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import boolean, integer, num, text, upsert

DATASET = "wvhk-k5uv"
CHICAGO_TOWNSHIPS = ("70", "71", "72", "73", "74", "75", "76", "77")
COLUMNS = [
    "row_id", "pin", "sale_date", "sale_price", "doc_no", "deed_type", "class", "township_code", "nbhd_code",
    "is_multisale", "num_parcels_sale", "filter_same_sale_within_365", "filter_less_than_10k",
    "filter_deed_type", "source_pull_id",
]  # fmt: skip


def where(since: str) -> str:
    towns = ", ".join(f"'{t}'" for t in CHICAGO_TOWNSHIPS)
    return f"township_code in ({towns}) and sale_date >= '{since}'"


def to_row(r: dict, pull_id: int) -> tuple:
    return (
        text(r.get("row_id")),
        text(r.get("pin")),
        text(r.get("sale_date"))[:10],
        num(r.get("sale_price")),
        text(r.get("doc_no")),
        text(r.get("deed_type")),
        text(r.get("class")),
        text(r.get("township_code")),
        text(r.get("nbhd")),
        boolean(r.get("is_multisale")),
        integer(r.get("num_parcels_sale")),
        boolean(r.get("sale_filter_same_sale_within_365")),
        boolean(r.get("sale_filter_less_than_10k")),
        boolean(r.get("sale_filter_deed_type")),
        pull_id,
    )


def latest_since(conn) -> str:
    d = conn.execute("select max(sale_date) + 1 from sale").fetchone()[0]
    return d.isoformat() if d else "2014-01-01"


def run(
    since: str | None = None, limit: int | None = None, client: Socrata | None = None, url: str | None = None
) -> int:
    client = client or Socrata(COOK)
    total = 0
    with connect(url) as conn:
        since = since or latest_since(conn)
        pull_id = start_pull(conn, COOK, DATASET, where(since))
        conn.commit()
        try:
            for page in client.pages(DATASET, order="row_id", where=where(since), page_size=limit or 50_000):
                total += upsert(conn, "sale", COLUMNS, "row_id", (to_row(r, pull_id) for r in page))
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
    print(f"sales loaded: {run(a.since, a.limit):,}")
