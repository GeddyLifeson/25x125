"""Land value map from vacant-land and teardown sales in the last 36 months.

Vacant: Assessor classes 100, 190 and 241. Teardown: a sale of a lot with a residential building (2xx, not
condo 299) followed within 24 months by a demolition or new construction permit on that lot (McMillen and
Singh's definition; teardown prices approximate land value, Dye and McMillen 2007). Sales pass the same
arm's-length checks as comps (single parcel, Assessor filters, warranty or trustee deed, $10,000 or more).

Each sale gives price per sq ft of lot, per buildable sq ft (lot x FAR of its district), and per sq ft
moved to a 3,125 sq ft lot with a lot-size elasticity of 0.858 (McMillen and Singh): price x (3125 / lot) ^
0.858 / 3125. Medians are kept by Assessor neighborhood and by community area, for vacant, teardown and all
sales, with counts and date range. Run: python -m jobs.build_land_values
"""

from core.db import connect
from engine.rules import Rules

ELASTICITY = 0.858
STD_LOT = 3125

SQL = """
truncate land_sale;
create temp table permit_lot on commit drop as
select s.pin10, p.issue_date, p.permit_type, p.permit_no
from permit p join parcel_shape s on st_contains(s.geom, p.geom)
where p.permit_type in ('PERMIT - WRECKING/DEMOLITION', 'PERMIT - NEW CONSTRUCTION')
  and p.issue_date >= current_date - interval '62 months';
create index on permit_lot (pin10, issue_date);

insert into land_sale
select distinct on (s.row_id) s.row_id, s.pin, left(s.pin, 10),
       case when s.class in ('100', '190', '241') then 'vacant' else 'teardown' end,
       s.sale_date, s.sale_price, ps.lot_sqft, f.far,
       s.sale_price / ps.lot_sqft,
       s.sale_price * power({std} / ps.lot_sqft, {e}) / {std},
       case when f.far > 0 then s.sale_price / (ps.lot_sqft * f.far) end,
       p.nbhd_code, p.community_area_num,
       case when s.class not in ('100', '190', '241') then pl.permit_type || ' ' || pl.permit_no || ' on ' || pl.issue_date end
from sale s
join parcel_site ps on ps.pin = s.pin
join lateral (select * from parcel p where p.pin = s.pin order by p.tax_year desc limit 1) p on true
left join zone_far f on f.zone_class = ps.zone_class
left join lateral (
  select * from permit_lot pl where pl.pin10 = left(s.pin, 10)
    and pl.issue_date > s.sale_date and pl.issue_date <= s.sale_date + interval '24 months'
  order by pl.issue_date limit 1
) pl on true
where s.sale_date >= current_date - interval '36 months'
  and s.sale_price >= 10000 and ps.lot_sqft >= 1000
  and not coalesce(s.is_multisale, false) and not coalesce(s.filter_less_than_10k, false)
  and not coalesce(s.filter_deed_type, false) and s.deed_type in ('Warranty', 'Trustee')
  and (s.class in ('100', '190', '241') or (s.class like '2%' and s.class <> '299' and pl.pin10 is not null))
order by s.row_id;

truncate land_value;
insert into land_value
select geo_kind, geo_id, map_kind, count(*),
       percentile_cont(0.5) within group (order by per_lot_sqft),
       percentile_cont(0.5) within group (order by per_lot_sqft_std),
       percentile_cont(0.5) within group (order by per_buildable_sqft),
       min(sale_date), max(sale_date), current_date
from (
  select 'nbhd' as geo_kind, nbhd_code as geo_id, kind as map_kind, * from land_sale where nbhd_code is not null
  union all
  select 'nbhd', nbhd_code, 'all', * from land_sale where nbhd_code is not null
  union all
  select 'community_area', community_area_num::text, kind, * from land_sale where community_area_num is not null
  union all
  select 'community_area', community_area_num::text, 'all', * from land_sale where community_area_num is not null
) x
group by geo_kind, geo_id, map_kind;
"""


def run(url: str | None = None) -> dict:
    with connect(url) as conn:
        rules = Rules.from_db(conn)
        conn.execute("create temp table zone_far (zone_class text primary key, far numeric) on commit drop")
        classes = [
            r[0]
            for r in conn.execute("select distinct zone_class from parcel_site where zone_class is not null")
        ]
        rows = [(z, d.far) for z in classes if (d := rules.district_for(z)) and d.far]
        with conn.cursor().copy("copy zone_far from stdin") as cp:
            for r in rows:
                cp.write_row(r)
        conn.execute(SQL.format(std=STD_LOT, e=ELASTICITY))
        out = dict(conn.execute("select kind, count(*) from land_sale group by 1").fetchall())
        out["areas"] = conn.execute(
            "select count(*) from land_value where geo_kind = 'community_area' and kind = 'all'"
        ).fetchone()[0]
    return out


if __name__ == "__main__":
    print(run())
