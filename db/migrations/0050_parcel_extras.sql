-- Free depth channels from the October 30, 2026 channel audit: the Assessor's parcel proximity measures,
-- Assessor permits, tax-exempt parcels, and the city's building footprints.

create table parcel_proximity (
  pin10 text primary key,
  tax_year integer not null,
  foreclosures_half_mile_5y integer,       -- foreclosure filings within half a mile, past 5 years
  foreclosures_per_1000_pins numeric,
  pins_half_mile integer,
  nearest_new_construction_pin10 text,
  nearest_new_construction_ft numeric,
  nearest_vacant_land_pin10 text,
  nearest_vacant_land_ft numeric,
  airport_noise_dnl numeric,
  nearest_cta_stop_ft numeric,
  nearest_metra_stop_ft numeric,
  arterial_daily_traffic numeric,
  schools_half_mile integer,
  source_pull_id bigint not null references source_pull (id)
);

create table assessor_permit (
  row_id text primary key,
  pin text not null,
  permit_number text,
  local_permit_number text,                -- the city's permit number where the Assessor recorded it
  date_issued date,
  status text,                             -- CLOSED, OPEN, PENDING, RECHECK, MANAGER REVIEW
  assessable text,
  amount numeric,
  job_code text,
  work_description text,
  improvement_code text,
  source_pull_id bigint not null references source_pull (id)
);
create index assessor_permit_pin on assessor_permit (pin);

create table exempt_parcel (
  pin text primary key,
  tax_year integer not null,
  class text,
  owner_name text,
  owner_num text,
  address text,
  source_pull_id bigint not null references source_pull (id)
);

create table building_footprint (
  bldg_id text primary key,
  status text,                             -- ACTIVE or PROPOSED
  stories integer,
  units integer,
  year_built integer,
  building_sqft numeric,
  footprint_sqft numeric,
  address text,
  pin10 text,                              -- the lot holding the footprint's interior point
  geom geometry(MultiPolygon, 4326),
  source_pull_id bigint not null references source_pull (id)
);
create index building_footprint_geom on building_footprint using gist (geom);
create index building_footprint_pin10 on building_footprint (pin10);
