"""The data sources page: every dataset in data/sources/datasets.csv with its publisher, link, how often we
copy it and the date of the last copy in this database (source_pull). Read from Postgres and the repo's data
files only; nothing is fetched from a portal here.
"""

import csv
import json
from pathlib import Path

from fastapi import APIRouter

from core.db import connect

router = APIRouter()
DATA = Path(__file__).resolve().parent.parent / "data"
NOTES = json.loads((DATA / "rules" / "source_notes.json").read_text())


def catalog() -> list[dict]:
    with (DATA / "sources" / "datasets.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def link(row: dict) -> str:
    """The public page for a dataset: Socrata ids get the portal's dataset page, others the listed address."""
    base, ds = row["base_url"], row["id"]
    if base.endswith("/resource/") and len(ds) == 9 and ds[4] == "-":
        return base.removesuffix("resource/") + "d/" + ds
    return base


def last_pull(pulls: dict, catalog_id: str) -> tuple:
    """The newest pull for a catalog row. Socrata ids match exactly; other loaders record a path or address, so
    the row's id (up to any note in brackets) or its alias in source_notes.json is looked for inside it."""
    if catalog_id in pulls:
        return pulls[catalog_id]
    key = NOTES["pull_ids"].get(catalog_id) or catalog_id.split(" (")[0]
    hits = [v for k, v in pulls.items() if key in k]
    return max(hits, key=lambda v: v[0]) if hits else (None, None)


def sources(conn) -> dict:
    pulls = {
        ds: (at, n)
        for ds, at, n in conn.execute(
            """select distinct on (dataset_id) dataset_id, finished_at, row_count from source_pull
               where status = 'ok' and finished_at is not null order by dataset_id, finished_at desc"""
        ).fetchall()
    }
    out = []
    for row in catalog():
        hidden = NOTES["display"].get(row["id"])
        at, n = last_pull(pulls, row["id"])
        out.append({
            "name": row["dataset"], "publisher": row["portal"], "id": row["id"], "url": link(row),
            "refresh": row["refresh"], "used_for": row["used_in"], "last_pulled": at.date().isoformat() if at else None,
            "rows": n, "display": hidden or "shown with its source and date",
        })  # fmt: skip
    return {
        "sources": out,
        "attribution": NOTES["attribution"],
        "not_used": NOTES["not_used"],
        "label": NOTES["label"],
    }


@router.get("/sources")
def list_sources() -> dict:
    """Datasets behind the numbers, with the last copy date of each, plus attribution lines."""
    with connect() as conn:
        return sources(conn)
