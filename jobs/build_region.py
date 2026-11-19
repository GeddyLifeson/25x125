"""Builders for regions outside Chicago: what stands on each lot, the comp pool and the land value map.

They read the shared tables a region loader fills (parcel with use_group, building_char, sale with
qualification and vacant_at_sale, assessed_value, parcel_site) and write the same tables the Chicago builders
write, so the engine and screens do not change.

Comps: 1-6 unit residential buildings built in or after `comps.built_since` (region.json, default 2014). With
recorded prices (Florida), each parcel's first qualified arm's-length improved sale on or after January 1 of
the year built. In states that keep prices private (Texas), `price_basis` is "appraisal district values" and
each recent build's appraised market value stands in, dated January 1 of the roll year and marked
basis = 'appraisal'.
Land: qualified sales of parcels that were vacant when sold, last 36 months, by appraiser neighborhood and ZIP.
Run: python -m jobs.build_region
"""

from core import region
from core.db import connect

LOT_USE = """
truncate lot_use;
insert into lot_use (pin10, use_now, units_now, block_face, block_face_source)
select p.pin10,
       case p.use_group when 'vacant' then 'vacant' when 'single' then 'single' when 'multi' then 'multi'
            else 'other' end,
       case p.use_group when 'vacant' then 0 when 'single' then greatest(coalesce(b.apartments, 1), 1)
            when 'multi' then greatest(coalesce(b.apartments, 2), 2) when 'condo' then 1 else 0 end,
       m[2] || '|' || case when m[1]::bigint % 2 = 0 then 'even' else 'odd' end || '|' || (m[1]::bigint / 100 * 100),
       case when m is not null then 'hundred block' end
from parcel p
left join building_char b on b.row_id = p.pin
left join parcel_address a on a.pin = p.pin
left join lateral regexp_match(upper(a.address), '^([0-9]{1,9})\\s+(.+)$') m on true;
"""

COMPS_SALE = """
with cand as (
  select b.pin, greatest(coalesce(b.apartments, 1), 1) as units, b.building_sqft as sqft, b.year_built
  from building_char b join parcel p on p.pin = b.pin
  where p.use_group in ('single', 'multi') and b.year_built >= %(since)s
    and greatest(coalesce(b.apartments, 1), 1) between 1 and 6
),
first_sale as (
  select distinct on (s.pin) c.*, s.row_id, s.sale_date, s.sale_price
  from cand c join sale s on s.pin = c.pin
  where s.sale_date >= make_date(c.year_built, 1, 1) and s.qualification = any(%(qualified)s)
    and not coalesce(s.is_multisale, false) and s.vacant_at_sale is not true
  order by s.pin, s.sale_date, s.row_id
)
insert into comp (sale_row_id, pin, kind, building_id, sale_date, price, units, price_per_unit, sqft,
                  price_per_sqft, year_built, nbhd_code, community_area, tract_geoid, zip, geom, excluded, basis, source)
select f.row_id, f.pin, 'building', f.pin, f.sale_date, f.sale_price, f.units, f.sale_price / f.units,
       nullif(f.sqft, 0), case when f.sqft > 500 then f.sale_price / f.sqft end, f.year_built,
       p.nbhd_code, p.community_area_name, p.tract_geoid, p.zip, p.geom,
       case when f.sale_price / f.units < %(floor)s then 'under price floor' end, 'sale', %(source)s
from first_sale f join parcel p on p.pin = f.pin;
"""

COMPS_APPRAISAL = """
insert into comp (sale_row_id, pin, kind, building_id, sale_date, price, units, price_per_unit, sqft,
                  price_per_sqft, year_built, nbhd_code, community_area, tract_geoid, zip, geom, excluded, basis, source)
select 'av-' || b.pin, b.pin, 'building', b.pin, make_date(v.tax_year, 1, 1), v.market_value,
       greatest(coalesce(b.apartments, 1), 1), v.market_value / greatest(coalesce(b.apartments, 1), 1),
       nullif(b.building_sqft, 0), case when b.building_sqft > 500 then v.market_value / b.building_sqft end,
       b.year_built, p.nbhd_code, p.community_area_name, p.tract_geoid, p.zip, p.geom,
       case when v.market_value / greatest(coalesce(b.apartments, 1), 1) < %(floor)s then 'under price floor' end,
       'appraisal', %(source)s
from building_char b join parcel p on p.pin = b.pin
join lateral (select * from assessed_value v where v.pin = b.pin and v.market_value > 0
              order by v.tax_year desc limit 1) v on true
where p.use_group in ('single', 'multi') and b.year_built >= %(since)s and b.year_built < v.tax_year
  and greatest(coalesce(b.apartments, 1), 1) between 1 and 6;
"""

# Likely a lot sale or a sale before completion: under half the ZIP's median price per sq ft.
COMPS_FILTER = """
update comp c set excluded = 'under 50%% of area median per sq ft'
from (
  select community_area, percentile_cont(0.5) within group (order by price_per_sqft) as med
  from comp where excluded is null and price_per_sqft is not null group by community_area
) m
where c.excluded is null and c.community_area = m.community_area and c.price_per_sqft < 0.5 * m.med;
"""

LAND = """
insert into land_sale (sale_row_id, pin, pin10, kind, sale_date, price, lot_sqft, per_lot_sqft, per_lot_sqft_std,
                       nbhd_code, community_area_num, evidence, basis)
select s.row_id, s.pin, s.pin, 'vacant', s.sale_date, s.sale_price, ps.lot_sqft, s.sale_price / ps.lot_sqft,
       s.sale_price / ps.lot_sqft, p.nbhd_code, p.community_area_num,
       'vacant when sold, qualification code ' || s.qualification, 'sale'
from sale s join parcel_site ps on ps.pin = s.pin join parcel p on p.pin = s.pin
where s.vacant_at_sale and s.qualification = any(%(land_qualified)s) and not coalesce(s.is_multisale, false)
  and s.sale_date >= current_date - interval '36 months' and s.sale_price >= 10000
  and ps.lot_sqft between 1000 and 87120 and p.use_group in ('vacant', 'single', 'multi');
"""

LAND_VALUE = """
truncate land_value;
insert into land_value
select geo_kind, geo_id, 'all', count(*), percentile_cont(0.5) within group (order by per_lot_sqft),
       percentile_cont(0.5) within group (order by per_lot_sqft_std), null, min(sale_date), max(sale_date), current_date
from (
  select 'nbhd' as geo_kind, nbhd_code as geo_id, * from land_sale where nbhd_code is not null
  union all
  select 'community_area', community_area_num::text, * from land_sale where community_area_num is not null
) x group by geo_kind, geo_id;
"""


# Overlays on each lot: those that cover the lot's inside point. Large polygons (county flood zones) are split
# first so the point tests stay fast.
OVERLAYS = """
create temp table region_overlay_part on commit drop as
select kind, name, st_subdivide(geom, 256) as geom from overlay;
create index on region_overlay_part using gist (geom);
analyze region_overlay_part;
update parcel_site ps set overlays = x.o
from (
  select p.pin, jsonb_agg(distinct jsonb_build_object('kind', o.kind, 'name', o.name)) as o
  from parcel p join region_overlay_part o on st_contains(o.geom, p.geom)
  group by p.pin
) x where ps.pin = x.pin;
"""


def run(url: str | None = None) -> dict:
    r = region.current()
    c = r.get("comps") or {}
    args = {
        "since": c.get("built_since", 2014),
        "floor": c.get("price_floor_per_unit", 100000),
        "qualified": c.get("qualified_codes", ["01", "02"]),
        "land_qualified": c.get("land_qualified_codes", ["01", "02", "03"]),
        "source": c.get("source", r["name"]),
    }
    appraisal = r.get("price_basis") == "appraisal district values"
    with connect(url) as conn:
        conn.execute(LOT_USE)
        conn.execute("truncate comp")
        conn.execute(COMPS_APPRAISAL if appraisal else COMPS_SALE, args)
        conn.execute(COMPS_FILTER.replace("%%", "%"))
        conn.execute("truncate land_sale")
        conn.execute(LAND, args)
        conn.execute(LAND_VALUE)
        conn.execute("update parcel_site set overlays = null")
        for stmt in OVERLAYS.split(";"):
            if stmt.strip():
                conn.execute(stmt)
        out = {"lots": conn.execute("select count(*) from lot_use").fetchone()[0]}
        out["lots with overlays"] = conn.execute(
            "select count(*) from parcel_site where overlays is not null"
        ).fetchone()[0]
        for e, n in conn.execute("select coalesce(excluded, 'kept'), count(*) from comp group by 1"):
            out[f"comps {e}"] = n
        out["land sales"] = conn.execute("select count(*) from land_sale").fetchone()[0]
        out["land areas"] = conn.execute("select count(*) from land_value").fetchone()[0]
    return out


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k:45} {v:>8,}")
