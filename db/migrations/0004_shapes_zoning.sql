-- Parcel polygons (Cook County) and zoning districts (City of Chicago), with lot measures.

create table parcel_shape (
  pin10 text primary key,
  vintage integer not null,                -- year of the polygon layer (77tz-riq7 is 2021)
  geom geometry(MultiPolygon, 4326) not null,
  lot_sqft numeric,                        -- area in State Plane feet
  frontage_ft numeric,                     -- short side of the oriented bounding box; an estimate
  depth_ft numeric,                        -- long side of the same box
  source_pull_id bigint not null references source_pull (id)
);
create index parcel_shape_geom on parcel_shape using gist (geom);

create table zoning_district_area (
  objectid text primary key,
  zone_class text not null,                -- e.g. RT-4, B2-3, PD 717
  zone_type integer,
  pd_num integer,
  edit_date date,
  geom geometry(MultiPolygon, 4326) not null,
  source_pull_id bigint not null references source_pull (id)
);
create index zoning_district_area_geom on zoning_district_area using gist (geom);
create index zoning_district_area_class on zoning_district_area (zone_class);

-- Lot measures from a polygon, in feet (EPSG:3435, Illinois State Plane East).
create function lot_measures(g geometry, out area_sqft numeric, out short_ft numeric, out long_ft numeric)
language sql immutable as $$
  with p as (select st_transform(g, 3435) as g),
       e as (select st_exteriorring(st_orientedenvelope(g)) as r, st_area(g) as a from p)
  select a::numeric,
         least(st_distance(st_pointn(r, 1), st_pointn(r, 2)), st_distance(st_pointn(r, 2), st_pointn(r, 3)))::numeric,
         greatest(st_distance(st_pointn(r, 1), st_pointn(r, 2)), st_distance(st_pointn(r, 2), st_pointn(r, 3)))::numeric
  from e
$$;
