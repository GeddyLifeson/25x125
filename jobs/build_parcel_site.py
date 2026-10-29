"""Join parcels to zoning and lot measures into parcel_site.

Zoning comes from the district under the parcel point; the share of the lot polygon inside that district
is kept so split-zoned lots can be flagged. Lot size comes from the PIN's polygon. A PIN created after the
polygon layer (new condo units, divided or combined lots) takes the polygon under its point instead,
and failing that the Assessor's land square feet.
Run: python -m jobs.build_parcel_site
"""

from core.db import connect

SQL = """
truncate parcel_site;
insert into parcel_site (pin, pin10, zone_class, zone_share, lot_sqft, frontage_ft, depth_ft, lot_source)
select p.pin, p.pin10, z.zone_class,
       case when s.geom is not null and st_area(s.geom) > 0
            then round((st_area(st_intersection(s.geom, z.geom)) / st_area(s.geom))::numeric, 2) end,
       coalesce(s.lot_sqft, bc.land_sqft),
       s.frontage_ft, s.depth_ft,
       case when s.pin10 = p.pin10 then 'polygon ' || s.vintage
            when s.lot_sqft is not null then 'polygon ' || s.vintage || ' under the parcel point'
            when bc.land_sqft is not null then 'assessor' end
from parcel p
left join lateral (
  select * from parcel_shape s where s.pin10 = p.pin10
  union all
  select * from parcel_shape s
  where p.geom is not null and st_contains(s.geom, p.geom)
    and not exists (select 1 from parcel_shape x where x.pin10 = p.pin10)
  limit 1
) s on true
left join lateral (
  select zone_class, geom from zoning_district_area z
  where st_intersects(z.geom, coalesce(st_pointonsurface(s.geom), p.geom))
  limit 1
) z on true
left join lateral (
  select land_sqft from building_char b where b.pin = p.pin and b.land_sqft > 0
  order by tax_year desc, card limit 1
) bc on true;
"""


def run(url: str | None = None) -> int:
    with connect(url) as conn:
        conn.execute(SQL)
        return conn.execute("select count(*) from parcel_site").fetchone()[0]


if __name__ == "__main__":
    print(f"parcel sites built: {run():,}")
