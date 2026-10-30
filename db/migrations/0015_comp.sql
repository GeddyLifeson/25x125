-- FHFA house price indexes (annual by census tract and ZIP, quarterly for the Chicago metro division), used to
-- move comp prices to the date of the estimate.
create table hpi (
  geo_kind text not null,     -- 'tract', 'zip', 'metro'
  geo_id text not null,
  year integer not null,
  quarter integer not null,   -- 0 for annual series
  hpi numeric not null,
  source_pull_id bigint not null references source_pull (id),
  primary key (geo_kind, geo_id, year, quarter)
);

-- The comp pool: first arm's-length sale of each 2-6 unit building or condo unit in a 2-6 unit building built
-- 2014 or later. Every candidate is kept; `excluded` names the filter that removed it, so screens and checks
-- can show what was dropped and why.
create table comp (
  sale_row_id text primary key,
  pin text not null,
  kind text not null,          -- 'building' or 'condo'
  building_id text not null,   -- pin10 for buildings, tieback PIN (or pin10) for condo units
  sale_date date not null,
  price numeric not null,
  units integer not null,      -- units in the building
  price_per_unit numeric not null,
  sqft numeric,                -- building sq ft, or the unit's sq ft for a condo
  price_per_sqft numeric,
  year_built integer,
  deed_type text,
  nbhd_code text,
  community_area text,
  tract_geoid text,
  zip text,
  geom geometry(Point, 4326),
  excluded text,
  built_at timestamptz not null default now()
);
create index comp_geom on comp using gist (geom);
create index comp_kept on comp (kind, sale_date) where excluded is null;
