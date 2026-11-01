"""Join parcels to zoning and lot measures into parcel_site.

Zoning is the district covering the largest share of the lot polygon (the parcel point when there is no
polygon); its share and the second district are kept so split-zoned lots can be flagged. Lot size comes from the PIN's polygon. A PIN created after the
polygon layer (new condo units, divided or combined lots) takes the polygon under its point instead,
and failing that the Assessor's land square feet.
Overlays add the historic survey rating (Red or Orange means a 90-day demolition hold), landmark name and
TIF district, and transit adds straight-line feet to the nearest CTA rail and Metra station.
Signals (violations, 311 vacant requests, scofflaw list, city-owned land, demolition notices) are tied to
the lot their point falls on (or the nearest lot within 15 m), or the source PIN where one is given, and
summed per lot. City map layers (transit-served areas, ADU zones, special districts, ARO areas, pedestrian
streets, Enterprise Zones, 2018 Opportunity Zones, fire limits) are tested at the lot's point on surface.
Depth channels add foreclosures within half a mile and distance to new construction (Assessor proximity),
stories and units (city footprints), fines owed, environmental holds, foreclosed rentals and exempt owners.
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
  -- The district covering the largest share of the lot; the parcel point when there is no polygon.
  select zone_class, geom from zoning_district_area z
  where st_intersects(z.geom, coalesce(s.geom, p.geom))
  order by case when s.geom is null then 0 else st_area(st_intersection(z.geom, s.geom)) end desc
  limit 1
) z on true
left join lateral (
  select land_sqft from building_char b where b.pin = p.pin and b.land_sqft > 0
  order by tax_year desc, card limit 1
) bc on true;

-- Second district on split-zoned lots, ignoring slivers under 2% of the lot.
update parcel_site ps set zone_class_2 = x.zone_class, zone_share_2 = x.share
from (
  select distinct on (s.pin10) s.pin10, z.zone_class,
         round((st_area(st_intersection(z.geom, s.geom)) / st_area(s.geom))::numeric, 2) as share
  from parcel_site q join parcel_shape s on s.pin10 = q.pin10
  join zoning_district_area z on st_intersects(z.geom, s.geom) and z.zone_class <> q.zone_class
  where q.zone_share < 0.98 and st_area(s.geom) > 0
  order by s.pin10, st_area(st_intersection(z.geom, s.geom)) desc
) x where ps.pin10 = x.pin10 and x.share >= 0.02;

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

-- Signals: the source PIN where given, else an exact match of the source address to one lot's address, else
-- the lot polygon under the point, else the nearest lot within 15 m (address points often sit on the
-- sidewalk). The method is kept so screens can show how each record was tied to the lot.
create temp table address_lot on commit drop as
select addr, min(pin10) as pin10 from (
  select regexp_replace(upper(a.address),
           '\\s(AVE|ST|BLVD|RD|DR|PL|CT|PKWY|TER|WAY|LN|HWY|SQ|PLZ|CIR|ROW)\\s.*$', ' \\1') as addr,
         left(a.pin, 10) as pin10
  from parcel_address a where a.address is not null
) x group by addr having count(distinct pin10) = 1;
create index on address_lot (addr);
analyze address_lot;

update parcel_signal set pin10 = null, match_method = null;
update parcel_signal g set pin10 = left(g.pin, 10), match_method = 'source pin' where g.pin is not null;
update parcel_signal g set pin10 = al.pin10, match_method = 'address'
from address_lot al
where g.pin is null and al.addr = regexp_replace(upper(g.address), '\\s+', ' ', 'g');
update parcel_signal g set
  pin10 = coalesce(
    (select s.pin10 from parcel_shape s where st_contains(s.geom, g.geom) limit 1),
    (select n.pin10 from (select s.pin10, s.geom from parcel_shape s order by s.geom <-> g.geom limit 1) n
     where st_dwithin(n.geom::geography, g.geom::geography, 15))),
  match_method = case when exists (select 1 from parcel_shape s where st_contains(s.geom, g.geom))
                      then 'point in lot' else 'nearest lot within 15 m' end
where g.pin is null and g.match_method is distinct from 'address' and g.geom is not null;
update parcel_signal set match_method = null where pin10 is null;

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

update parcel_site ps set
  hearing_fines_3y = x.hearing_fines_3y, vacant_building_fine_due = x.vacant_building_fine_due,
  environmental_hold = x.environmental_hold, foreclosed_rental_date = x.foreclosed_rental_date
from (
  select pin10,
    sum((attrs->>'imposed_fine')::numeric) filter (where kind = 'hearing_fine' and signal_date > current_date - 1095)
      as hearing_fines_3y,
    sum((attrs->>'current_amount_due')::numeric) filter (where kind = 'vacant_building_fine')
      as vacant_building_fine_due,
    (array_agg(detail order by signal_date desc nulls last) filter (where kind = 'environmental_hold'))[1]
      as environmental_hold,
    max(signal_date) filter (where kind = 'foreclosed_rental') as foreclosed_rental_date
  from parcel_signal
  where pin10 is not null and kind in ('hearing_fine', 'vacant_building_fine', 'environmental_hold', 'foreclosed_rental')
  group by pin10
) x where ps.pin10 = x.pin10;

update parcel_site ps set foreclosure_auction_date = x.signal_date, foreclosure_auction_status = x.status
from (
  select distinct on (pin10) pin10, signal_date, status from parcel_signal
  where pin10 is not null and kind = 'foreclosure_auction' order by pin10, signal_date desc nulls last
) x where ps.pin10 = x.pin10;

update parcel_site ps set public_sale_source = x.source, public_sale_price = x.price
from (
  select distinct on (pin10) pin10, source, coalesce(asking_price, minimum_bid, city_land_value) as price
  from lot_for_sale where for_sale and pin10 is not null order by pin10, source
) x where ps.pin10 = x.pin10;

-- Depth channels keyed by lot or PIN: Assessor proximity, city footprints, tax-exempt owners.
update parcel_site ps set foreclosures_half_mile_5y = x.foreclosures_half_mile_5y,
  nearest_new_construction_ft = x.nearest_new_construction_ft
from parcel_proximity x where ps.pin10 = x.pin10;
update parcel_site ps set stories = x.stories, footprint_units = x.units
from (select pin10, max(stories) as stories, sum(units) as units from building_footprint
      where pin10 is not null and status = 'ACTIVE' group by pin10) x
where ps.pin10 = x.pin10;
update parcel_site ps set exempt_owner = x.owner_name from exempt_parcel x where ps.pin = x.pin;

-- City map layers, tested at one point per PIN.
create temp table site_point on commit drop as
select p.pin, coalesce((select st_pointonsurface(s.geom) from parcel_shape s where s.pin10 = p.pin10), p.geom) as geom
from parcel p;
create index on site_point using gist (geom);
analyze site_point;
-- Large polygons (the citywide station buffers) split into small parts keep point tests fast.
create temp table overlay_part on commit drop as
select kind, name, rating, attrs, st_subdivide(geom, 256) as geom from overlay
where kind in ('tsl_cta_station', 'tsl_metra_station', 'tsl_bus_corridor', 'adu_area', 'special_district',
               'aro_area', 'enterprise_zone', 'opportunity_zone_2018', 'fire_limits');
create index on overlay_part using gist (geom);
analyze overlay_part;

update parcel_site ps set
  transit_served = (
    select case o.kind when 'tsl_cta_station' then 'CTA station' when 'tsl_metra_station' then 'Metra station'
                       else 'bus corridor: ' || o.name end
    from overlay_part o
    where o.kind in ('tsl_cta_station', 'tsl_metra_station', 'tsl_bus_corridor') and st_contains(o.geom, sp.geom)
    order by case o.kind when 'tsl_cta_station' then 0 when 'tsl_metra_station' then 1 else 2 end, o.name
    limit 1),
  adu_zone = (select o.name from overlay_part o where o.kind = 'adu_area' and st_contains(o.geom, sp.geom) limit 1),
  adu_limits = (select o.attrs->>'TEXT' from overlay_part o
                where o.kind = 'adu_area' and st_contains(o.geom, sp.geom) limit 1),
  special_district = (select string_agg(distinct o.name, '; ' order by o.name) from overlay_part o
                      where o.kind = 'special_district' and st_contains(o.geom, sp.geom)),
  aro_area = (select o.rating from overlay_part o where o.kind = 'aro_area' and st_contains(o.geom, sp.geom) limit 1),
  enterprise_zone = (select o.name from overlay_part o
                     where o.kind = 'enterprise_zone' and st_contains(o.geom, sp.geom) limit 1),
  opportunity_zone_2018 = (select o.name from overlay_part o
                           where o.kind = 'opportunity_zone_2018' and st_contains(o.geom, sp.geom) limit 1),
  fire_limits = exists (select 1 from overlay_part o where o.kind = 'fire_limits' and st_contains(o.geom, sp.geom))
from site_point sp where ps.pin = sp.pin and sp.geom is not null;

-- Pedestrian streets are drawn as the street itself, so a lot is on one when its polygon is within about
-- 10 m (0.0001 degrees) of it.
update parcel_site ps set pedestrian_street = x.name
from (
  select s.pin10, min(o.name) as name
  from overlay o join parcel_shape s on st_dwithin(s.geom, o.geom, 0.0001)
  where o.kind = 'pedestrian_street'
  group by s.pin10
) x where ps.pin10 = x.pin10;
"""


def run(url: str | None = None) -> int:
    with connect(url) as conn:
        conn.execute(SQL)
        return conn.execute("select count(*) from parcel_site").fetchone()[0]


if __name__ == "__main__":
    print(f"parcel sites built: {run():,}")
