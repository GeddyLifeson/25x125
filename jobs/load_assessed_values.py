"""Load Cook County Assessor assessed values (uzyt-m557) for Chicago and turn them into market values.

Two tax years are kept: the newest year with Board of Review values (final) and the newest year on the portal
(mailed or certified while appeals run). Each row keeps the best stage it has. Market value is assessed value
divided by the level of assessment for the property's major class (data/rules/assessment_levels.json).
Chicago townships are codes 70-77. Each run replaces both years.
Run: python -m jobs.load_assessed_values
"""

import json
from pathlib import Path

from core.db import connect
from core.socrata import COOK, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import integer, num, text, upsert

DATASET = "uzyt-m557"
CHICAGO = "township_code between '70' and '77'"
RULES = Path(__file__).resolve().parents[1] / "data" / "rules" / "assessment_levels.json"
COLUMNS = [
    "pin", "pin10", "tax_year", "class", "nbhd", "stage", "land_av", "bldg_av", "total_av", "level",
    "incentive_class", "market_value", "land_market_value", "source_pull_id",
]  # fmt: skip
STAGES = ("board", "certified", "mailed")


def load_rules(path: Path = RULES) -> dict:
    return json.loads(path.read_text())


def level_for(cls: str | None, rules: dict) -> tuple[float | None, bool]:
    """Level of assessment and whether it is an incentive class: '211' -> (0.10, False)."""
    c = (cls or "").strip().upper()
    if not c or c in rules["no_market_value"] or not c[0].isdigit():
        return None, False
    lv = rules["levels_by_major_class"].get(c[0])
    if not lv:
        return None, False
    return lv["level"], bool(lv.get("incentive"))


def to_row(r: dict, pull_id: int, rules: dict) -> tuple | None:
    pin = (text(r.get("pin")) or "").replace("-", "")
    if len(pin) != 14:
        return None
    for stage in STAGES:
        total = num(r.get(f"{stage}_tot"))
        if total is not None:
            break
    else:
        return None
    land, bldg = num(r.get(f"{stage}_land")), num(r.get(f"{stage}_bldg"))
    level, incentive = level_for(r.get("class"), rules)
    return (
        pin, pin[:10], integer(r.get("year")), text(r.get("class")), text(r.get("nbhd")), stage,
        land, bldg, total, level, incentive,
        round(total / level) if level else None,
        round(land / level) if level and land is not None else None,
        pull_id,
    )  # fmt: skip


def years(client: Socrata) -> list[str]:
    """Newest year with board values, and the newest year at any stage."""
    rows = client.get(
        DATASET,
        {"$select": "year, count(board_tot) as board", "$where": CHICAGO, "$group": "year", "$order": "year DESC",
         "$limit": 5},
    )  # fmt: skip
    newest = rows[0]["year"]
    final = next((r["year"] for r in rows if integer(r.get("board"))), newest)
    return sorted({newest, final})


def run(client: Socrata | None = None, url: str | None = None, tax_years: list[str] | None = None) -> int:
    client = client or Socrata(COOK)
    rules = load_rules()
    pick = tax_years or years(client)
    where = f"{CHICAGO} and year in ({', '.join(repr(y) for y in pick)})"
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, COOK, DATASET, where)
        conn.commit()
        try:
            conn.execute("delete from assessed_value")
            for page in client.pages(DATASET, order="row_id", where=where):
                rows = (row for r in page if (row := to_row(r, pull_id, rules)))
                total += upsert(conn, "assessed_value", COLUMNS, "pin, tax_year", rows)
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


if __name__ == "__main__":
    print(f"assessed values: {run():,}")
