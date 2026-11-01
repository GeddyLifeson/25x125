"""Build the comp pool from loaded sales, building characteristics and condo characteristics.

Candidates: 2-6 unit buildings (class 211) and condo units in buildings of 2-6 PINs (not parking or common
area, not mixed use), built 2014 or later, sold on or after January 1 of the year built. Each PIN's first such
sale is the candidate. Filters (data/rules/feasibility_defaults.json sale_comps.filters) mark rather than
delete, in this order:
  multi-parcel sale, Assessor sale filters (under $10k, deed type), deed type not warranty or trustee,
  price under the floor ($200,000 building, $150,000 condo unit), price repeats an earlier sale of the PIN
  within 24 months, price per sq ft under 50% of the community area median for its kind (likely sold before
  completion).
Run: python -m jobs.build_comps
"""

from core.db import connect

SQL = """
truncate comp;
with bldg as (
  select b.pin, sum(b.apartments) as units, sum(b.building_sqft) as sqft, max(b.year_built) as year_built
  from building_char b
  where b.tax_year = (select max(tax_year) from building_char) and b.class = '211'
  group by b.pin
  having max(b.year_built) >= 2014 and sum(b.apartments) between 2 and 6
),
unit as (
  select c.pin, coalesce(c.tieback_key_pin, c.pin10) as building_id, c.building_pins as units,
         c.unit_sqft as sqft, c.year_built
  from condo_char c
  where c.tax_year = (select max(tax_year) from condo_char) and c.year_built >= 2014
    and c.building_pins between 2 and 6
    and not coalesce(c.is_parking_space, false) and not coalesce(c.is_common_area, false)
    and not coalesce(c.building_is_mixed_use, false)
),
cand as (
  select 'building' as kind, pin, left(pin, 10) as building_id, units, sqft, year_built from bldg
  union all
  select 'condo', pin, building_id, units, sqft, year_built from unit
),
first_sale as (
  select distinct on (s.pin) c.*, s.row_id, s.sale_date, s.sale_price, s.deed_type, s.is_multisale,
         s.filter_less_than_10k, s.filter_deed_type
  from cand c join sale s on s.pin = c.pin and s.sale_date >= make_date(c.year_built, 1, 1)
  order by s.pin, s.sale_date, s.row_id
)
insert into comp (sale_row_id, pin, kind, building_id, sale_date, price, units, price_per_unit, sqft,
                  price_per_sqft, year_built, deed_type, nbhd_code, community_area, tract_geoid, zip, geom, excluded)
select f.row_id, f.pin, f.kind, f.building_id, f.sale_date, f.sale_price, f.units,
       case f.kind when 'building' then f.sale_price / f.units else f.sale_price end,
       nullif(f.sqft, 0),
       case when f.sqft > (case f.kind when 'building' then 500 else 400 end) then f.sale_price / f.sqft end,
       f.year_built, f.deed_type, p.nbhd_code, initcap(p.community_area_name), p.tract_geoid, p.zip, p.geom,
       case
         when coalesce(f.is_multisale, false) then 'multi-parcel sale'
         when coalesce(f.filter_less_than_10k, false) or coalesce(f.filter_deed_type, false)
           then 'Assessor sale filter'
         when f.deed_type not in ('Warranty', 'Trustee') or f.deed_type is null then 'deed type ' || coalesce(f.deed_type, 'missing')
         when f.sale_price < case f.kind when 'building' then 200000 else 150000 end then 'under price floor'
         when exists (select 1 from sale e where e.pin = f.pin and e.sale_date < f.sale_date
                      and e.sale_date >= f.sale_date - interval '24 months' and e.sale_price = f.sale_price)
           then 'repeats an earlier sale price'
       end
from first_sale f
join lateral (select * from parcel p where p.pin = f.pin order by p.tax_year desc limit 1) p on true;

-- Likely sold before completion: under half the community area median price per sq ft for its kind.
update comp c set excluded = 'under 50% of area median per sq ft'
from (
  select kind, community_area, percentile_cont(0.5) within group (order by price_per_sqft) as med
  from comp where excluded is null and price_per_sqft is not null group by kind, community_area
) m
where c.excluded is null and c.kind = m.kind and c.community_area = m.community_area
  and c.price_per_sqft < 0.5 * m.med;
"""


def run(url: str | None = None) -> dict:
    with connect(url) as conn:
        conn.execute(SQL)
        rows = conn.execute(
            "select kind, coalesce(excluded, 'kept'), count(*) from comp group by 1, 2 order by 1, 3 desc"
        ).fetchall()
    return {f"{k}: {e}": n for k, e, n in rows}


if __name__ == "__main__":
    for k, n in run().items():
        print(f"{k:55} {n:>6,}")
