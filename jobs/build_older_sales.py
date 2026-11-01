"""Build the older-building sale pool used where no new-construction comps exist within 3 miles.

Arm's-length sales since 2015 of 2-6 unit buildings (class 211) built before 2014: single parcel, Assessor sale
filters passed, warranty or trustee deed, over $20,000. Building facts come from the latest Assessor
characteristics, as in jobs/build_comps.py.
Run: python -m jobs.build_older_sales
"""

from core.db import connect

SQL = """
truncate older_sale;
with bldg as (
  select b.pin, sum(b.apartments) as units, max(b.year_built) as year_built
  from building_char b
  where b.tax_year = (select max(tax_year) from building_char) and b.class = '211'
  group by b.pin
  having max(b.year_built) < 2014 and sum(b.apartments) between 2 and 6
)
insert into older_sale (sale_row_id, pin, sale_date, price, units, price_per_unit, year_built, community_area, geom)
select s.row_id, s.pin, s.sale_date, s.sale_price, b.units, s.sale_price / b.units, b.year_built,
       initcap(p.community_area_name), p.geom
from sale s
join bldg b on b.pin = s.pin
join lateral (select community_area_name, geom from parcel p where p.pin = s.pin and p.geom is not null
              order by tax_year desc limit 1) p on true
where s.sale_date >= '2015-01-01' and s.sale_price > 20000
  and not coalesce(s.is_multisale, false) and not coalesce(s.filter_less_than_10k, false)
  and not coalesce(s.filter_deed_type, false) and s.deed_type in ('Warranty', 'Trustee');
"""


def run(url: str | None = None) -> int:
    with connect(url) as conn:
        conn.execute(SQL)
        return conn.execute("select count(*) from older_sale").fetchone()[0]


if __name__ == "__main__":
    print(f"older sales: {run():,}")
