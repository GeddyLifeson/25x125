"""Step 1 acceptance check: every test parcel resolves to a parcel with zoning, lot area and frontage.

Matches each address in data/reference/test_parcels.csv to its new-construction permit, takes the
permit's PINs, and looks them up in parcel_site by their first 10 digits (condo units share them).
When those PINs no longer exist (the lot became condo units with new PINs), it takes the current
parcels whose points fall inside the old PIN's polygon.
Run: python -m jobs.check_test_parcels
"""

import csv
from pathlib import Path

from core.db import connect

TEST_PARCELS = Path(__file__).resolve().parents[1] / "data" / "reference" / "test_parcels.csv"

SQL = """
with pm as (
  select distinct left(unnest(pins), 10) as pin10 from permit
  where address = %s and permit_type = 'PERMIT - NEW CONSTRUCTION'
),
by_pin as (
  select s.* from parcel_site s join pm on s.pin10 = pm.pin10
),
by_shape as (
  select s.* from pm
  join parcel_shape old on old.pin10 = pm.pin10
  join parcel p on st_contains(old.geom, p.geom)
  join parcel_site s on s.pin = p.pin
  where not exists (select 1 from by_pin)
)
select pin10, max(zone_class), max(lot_sqft), max(frontage_ft), max(lot_source), count(*)
from (select * from by_pin union all select * from by_shape) s
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
