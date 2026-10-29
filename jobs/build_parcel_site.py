"""Join parcels to zoning and lot measures into parcel_site.

Zoning comes from the district under the parcel point; the share of the lot polygon inside that district
is kept so split-zoned lots can be flagged. Lot size comes from the PIN's polygon. A PIN created after the
polygon layer (new condo units, divided or combined lots) takes the polygon under its point instead,
and failing that the Assessor's land square feet.
Overlays add the historic survey rating (Red or Orange means a 90-day demolition hold), landmark name and
TIF district, and transit adds straight-line feet to the nearest CTA rail and Metra station.
Signals (violations, 311 vacant requests, scofflaw list, city-owned land, demolition notices) are tied to
the lot their point falls on (or the nearest lot within 15 m), or the source PIN where one is given, and
summed per lot.
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

-- Historic survey Red and Orange buildings and landmarks: those whose footprint centers sit on the lot.
update parcel_site ps set historic_rating = x.rating
from (
  select s.pin10,
         (array_agg(o.rating order by case o.rating when 'Red' then 0 else 1 end))[1] as rating
  from overlay o join parcel_shape s on st_contains(s.geom, st_pointonsurface(o.geom))
  where o.kind = 'historic_survey' and o.rating in ('Red', 'Orange')
  group by s.pin10
) x where ps.pin10 = x.pin10;

update parcel_site ps set landmark_name = x.name
from (
  select s.pin10, min(o.name) as name
  from overlay o join parcel_shape s on st_intersects(s.geom, o.geom)
   and st_area(st_intersection(s.geom, o.geom)) > 0.5 * st_area(s.geom)
  where o.kind = 'landmark'
  group by s.pin10
) x where ps.pin10 = x.pin10;

update parcel_site ps set tif_name = o.name
from parcel p join overlay o on o.kind = 'tif' and st_contains(o.geom, p.geom)
where ps.pin = p.pin;

-- Straight-line distance to the nearest station, in feet.
update parcel_site ps set
  cta_rail_ft = (select round(st_distance(t.geom::geography, p.geom::geography) * 3.28084)
                 from transit_station t where t.mode = 'cta' order by t.geom <-> p.geom limit 1),
  metra_ft = (select round(st_distance(t.geom::geography, p.geom::geography) * 3.28084)
              from transit_station t where t.mode = 'metra' order by t.geom <-> p.geom limit 1)
from parcel p where ps.pin = p.pin and p.geom is not null;

-- Signals: the source PIN where given, else the lot polygon under the point, else the nearest lot within
-- 15 m (address points often sit on the sidewalk in front of the lot).
update parcel_signal g set pin10 = coalesce(left(g.pin, 10),
  (select s.pin10 from parcel_shape s where st_contains(s.geom, g.geom) limit 1),
  (select n.pin10 from (select s.pin10, s.geom from parcel_shape s order by s.geom <-> g.geom limit 1) n
   where st_dwithin(n.geom::geography, g.geom::geography, 15)))
where g.geom is not null or g.pin is not null;

update parcel_site ps set
  open_violations = x.open_violations, last_violation_date = x.last_violation_date,
  vacant_building_311 = x.vacant_building_311, vacant_lot_311 = x.vacant_lot_311,
  scofflaw = x.scofflaw, city_owned_status = x.city_owned_status,
  demolition_notice_date = x.demolition_notice_date
from (
  select pin10,
    count(*) filter (where kind = 'violation' and status = 'OPEN') as open_violations,
    max(signal_date) filter (where kind = 'violation') as last_violation_date,
    count(*) filter (where kind = 'vacant_building_311' and signal_date > current_date - 1095
                     and lower(coalesce(attrs->>'duplicate', '')) <> 'true') as vacant_building_311,
    count(*) filter (where kind = 'vacant_lot_311' and signal_date > current_date - 1095
                     and lower(coalesce(attrs->>'duplicate', '')) <> 'true') as vacant_lot_311,
    bool_or(kind = 'scofflaw') as scofflaw,
    min(status) filter (where kind = 'city_owned') as city_owned_status,
    max(signal_date) filter (where kind = 'demolition_notice') as demolition_notice_date
  from parcel_signal where pin10 is not null group by pin10
) x where ps.pin10 = x.pin10;
"""


def run(url: str | None = None) -> int:
    with connect(url) as conn:
        conn.execute(SQL)
        return conn.execute("select count(*) from parcel_site").fetchone()[0]


if __name__ == "__main__":
    print(f"parcel sites built: {run():,}")
