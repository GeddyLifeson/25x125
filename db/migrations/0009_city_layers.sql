-- Flags from the city map layers (jobs.load_city_layers), set per parcel by jobs.build_parcel_site.
-- Each is tested at the lot's point on surface, or the parcel point when there is no lot polygon.

alter table parcel_site
  add column transit_served text,          -- null, or what makes it transit-served: 'CTA station',
                                           -- 'Metra station', 'bus corridor: <street>' (city TSL map)
  add column adu_zone text,                -- city ADU zone ('Zone 1'..'Zone 10'); null = outside ADU areas
  add column adu_limits text,              -- the zone's limits, e.g. 'Annual Limits, Owner Occupancy Limits'
  add column special_district text,        -- zoning special district, e.g. 'Predominance of the Block (606) District'
  add column aro_area text,                -- Affordable Requirements Ordinance area type
  add column pedestrian_street text,
  add column enterprise_zone text,
  add column opportunity_zone_2018 text,   -- 2010 census tract GEOID of a 2018 Opportunity Zone
  add column fire_limits boolean;
