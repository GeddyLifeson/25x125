"""Neighborhood cost index and permit wait times from new 2-6 unit residential building permits.

Permits: 'PERMIT - NEW CONSTRUCTION' issued in the last 5 years whose description names a new building of 2-6
dwelling units (the parser from scripts/research/citywide.py), reported cost $100,000 or more, not mixed use,
not coach houses or repairs, not cancelled or revoked; the latest permit per address.

Index (data/rules/feasibility_defaults.json cost_index_method): each permit's cost per unit over the city
median for its unit group (2, 3, 4-6), then a recency-weighted median per community area (1.00, 0.75, 0.56,
0.42 for the last four quarters, x0.75 per quarter before that). An area with fewer than 10 permits is blended
with its neighboring community areas: area weight n / 10, neighbors the rest.

Reported costs are rough (69% are exact multiples of $50,000), so the index ranks areas; it does not set the
dollar level. Run: python -m jobs.build_cost_index
"""

import re
import statistics as st
from collections import defaultdict
from datetime import date

from core.db import connect

WORDS = {"TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SINGLE": 1, "ONE": 1}
UNIT_RE = re.compile(
    r"\b(\d{1,2}|TWO|THREE|FOUR|FIVE|SIX|SINGLE|ONE)[\s-]*(?:DWELLING\s*)?(?:UNITS?|DU|D\.U\.|FLAT|FAMILY|APARTMENTS?)\b"
)
GOOD = re.compile(
    r"ERECT|NEW CONSTRUCTION|NEW \d|NEW (TWO|THREE|FOUR|FIVE|SIX)|PROPOSED|FULL BUILDING PERMIT|CONSTRUCT A NEW"
    r"|BUILD A NEW|NEW .*BUILDING"
)
BAD = re.compile(
    r"REPLACE|REPAIR|^\W*PORCH|REBUILD (REAR|FRONT)? ?PORCH|WRECK|DEMOLI|INTERIOR|REVISION TO|CHANGE OF CONTRACTOR"
    r"|GARAGE ONLY|COACH HOUSE|\bADU\b"
)
MIXED = re.compile(r"\bMIXED|COMMERCIAL|RETAIL|OFFICE|STORE")
YEARS = 5
MIN_PERMITS = 10
WEIGHTS = [1.0, 0.75, 0.56, 0.42]


def units_from(desc: str) -> int | None:
    d = desc.upper()
    m = UNIT_RE.search(d)
    if not m or not GOOD.search(d) or BAD.search(d) or MIXED.search(d):
        return None
    u = m.group(1)
    n = int(u) if u.isdigit() else WORDS.get(u)
    return n if n and 2 <= n <= 6 else None


def group(units: int) -> str:
    return "2" if units == 2 else ("3" if units == 3 else "4-6")


def recency_weight(issued: date, today: date) -> float:
    q = max((today - issued).days // 91, 0)
    return WEIGHTS[q] if q < len(WEIGHTS) else WEIGHTS[-1] * 0.75 ** (q - len(WEIGHTS) + 1)


def weighted_quantile(vals: list[tuple[float, float]], q: float) -> float:
    vals = sorted(vals)
    total, acc = sum(w for _, w in vals), 0.0
    for v, w in vals:
        acc += w
        if acc >= total * q - 1e-12:
            return v
    return vals[-1][0]


def run(url: str | None = None, today: date | None = None) -> dict:
    today = today or date.today()
    with connect(url) as conn:
        rows = conn.execute(
            """select distinct on (address) id, community_area_num, issue_date, reported_cost, review_type,
                      processing_days, work_description
               from permit
               where permit_type = 'PERMIT - NEW CONSTRUCTION' and issue_date >= %s
                 and reported_cost >= 100000 and permit_status not in ('CANCELLED', 'REVOKED')
                 and work_description is not null and address is not null
               order by address, issue_date desc""",
            (date(today.year - YEARS, today.month, 1),),
        ).fetchall()
        permits = []
        for pid, ca, issued, cost, review, days, desc in rows:
            if (u := units_from(desc)) and ca:
                permits.append((pid, ca, issued, u, float(cost), review, days, desc[:300]))
        conn.execute("truncate cost_permit")
        with conn.cursor().copy(
            "copy cost_permit (permit_id, community_area_num, issue_date, units, reported_cost, per_unit,"
            " review_type, processing_days, description) from stdin"
        ) as cp:
            for pid, ca, issued, u, cost, review, days, desc in permits:
                cp.write_row((pid, ca, issued, u, cost, cost / u, review, days, desc))

        city = {
            g: st.median([c / u for _, _, _, u, c, *_ in permits if group(u) == g]) for g in ("2", "3", "4-6")
        }
        ratios = defaultdict(list)
        for _, ca, issued, u, cost, *_ in permits:
            ratios[ca].append((cost / u / city[group(u)], recency_weight(issued, today)))
        names = dict(
            conn.execute("select code::int, name from boundary where kind = 'community_area'").fetchall()
        )
        neighbors = defaultdict(list)
        for a, b in conn.execute(
            "select code::int, neighbor_code::int from community_area_neighbor"
        ).fetchall():
            neighbors[a].append(b)

        conn.execute("truncate cost_index")
        for ca, name in sorted(names.items()):
            own = ratios.get(ca, [])
            n = len(own)
            raw = weighted_quantile(own, 0.5) if own else None
            p25 = weighted_quantile(own, 0.25) if own else None
            p75 = weighted_quantile(own, 0.75) if own else None
            nb = [x for b in neighbors[ca] for x in ratios.get(b, [])]
            w_own = 1.0 if n >= MIN_PERMITS or not nb else n / MIN_PERMITS
            nb_idx = weighted_quantile(nb, 0.5) if nb else 1.0
            idx = w_own * (raw or 0) + (1 - w_own) * nb_idx
            conn.execute(
                "insert into cost_index values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    ca,
                    name.title(),
                    n,
                    raw,
                    p25,
                    p75,
                    round(idx, 3),
                    round(1 - w_own, 2),
                    n < MIN_PERMITS,
                    today,
                ),
            )

        conn.execute("truncate permit_wait")
        by_review = defaultdict(list)
        for *_, review, days, _ in permits:
            if days is not None and days >= 0 and review:
                by_review[review].append(days)
        for review, days in by_review.items():
            if len(days) >= 4:
                q = st.quantiles(days, n=4)
                conn.execute(
                    "insert into permit_wait values (%s, %s, %s, %s, %s, %s)",
                    (review, len(days), q[0], st.median(days), q[2], today),
                )
    return {"permits": len(permits), "city_median_per_unit": {g: round(v) for g, v in city.items()}}


if __name__ == "__main__":
    print(run())
