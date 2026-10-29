"""Step 1 acceptance check: every test parcel resolves to a parcel with zoning, lot area and frontage.

Matches each address in data/reference/test_parcels.csv to its new-construction permit, takes the
permit's PINs, and looks them up in parcel_site by their first 10 digits (condo units share them).
When those PINs no longer exist (the lot was divided or became condo units with new PINs), it takes the
current lot under the permit's location, or the nearest one within 30 meters.
Run: python -m jobs.check_test_parcels
"""

import csv
from pathlib import Path

from core.db import connect

TEST_PARCELS = Path(__file__).resolve().parents[1] / "data" / "reference" / "test_parcels.csv"

SQL = """
with pm as (
  select pins, geom from permit
  where address = %s and permit_type = 'PERMIT - NEW CONSTRUCTION'
  order by issue_date desc
  limit 1
),
by_pin as (
  select s.* from parcel_site s, pm where s.pin10 = any (select left(x, 10) from unnest(pm.pins) x)
),
by_point as (
  select s.* from pm
  cross join lateral (
    select sh.pin10 from parcel_shape sh
    where st_dwithin(sh.geom::geography, pm.geom::geography, 30)
    order by sh.geom <-> pm.geom
    limit 1
  ) near
  join parcel_site s on s.pin10 = near.pin10
  where not exists (select 1 from by_pin)
)
select pin10, max(zone_class), max(lot_sqft), max(frontage_ft),
       max(lot_source) || case when bool_or(found_by = 'point') then ', found by permit location' else '' end,
       count(*)
from (select *, 'pin' as found_by from by_pin union all select *, 'point' from by_point) s
group by pin10
order by count(*) desc
limit 1
"""


def normalize(addr: str) -> str:
    return " ".join(addr.upper().split())


def run(url: str | None = None) -> list[dict]:
    out = []
    with connect(url) as conn:
        for t in csv.DictReader(TEST_PARCELS.open()):
            row = conn.execute(SQL, (normalize(t["addr"]),)).fetchone()
            r = {"addr": t["addr"], "units": t["units"]}
            if row:
                r.update(
                    pin10=row[0], zone=row[1], lot_sqft=row[2], frontage_ft=row[3], source=row[4], pins=row[5]
                )
            r["ok"] = bool(row and row[1] and row[2] and row[3])
            out.append(r)
    return out


if __name__ == "__main__":
    results = run()
    for r in results:
        mark = "ok  " if r["ok"] else "MISS"
        print(
            f"{mark} {r['addr']:<24} {r.get('zone') or '-':<7} lot {r.get('lot_sqft') or '-':>6}"
            f" front {r.get('frontage_ft') or '-':>5} {r.get('source') or ''}"
        )
    print(f"{sum(r['ok'] for r in results)} of {len(results)} resolve with zoning, lot area and frontage")
