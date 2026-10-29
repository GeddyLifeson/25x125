-- Building permits (City of Chicago) and residential building characteristics (Assessor).

create table permit (
  id text primary key,                     -- portal row id
  permit_no text not null,
  permit_type text,
  review_type text,
  permit_status text,
  permit_milestone text,
  application_start_date date,
  issue_date date,
  processing_days integer,
  address text,
  work_type text,
  work_description text,
  reported_cost numeric,
  total_fee numeric,
  ward integer,
  community_area_num integer,
  census_tract text,
  pins text[],                             -- 14-digit PINs from pin_list
  geom geometry(Point, 4326),
  source_pull_id bigint not null references source_pull (id)
);
create index permit_issue on permit (issue_date);
create index permit_type on permit (permit_type, issue_date);
create index permit_pins on permit using gin (pins);
create index permit_geom on permit using gist (geom);

create table building_char (
  row_id text primary key,                 -- Assessor's row id (one per PIN, card and year)
  pin text not null,
  tax_year integer not null,
  card integer,
  class text,
  apartments integer,                      -- char_apts, converted from words
  building_sqft integer,
  land_sqft integer,
  year_built integer,
  rooms integer,
  beds integer,
  full_baths integer,
  half_baths integer,
  basement text,
  ext_wall text,
  source_pull_id bigint not null references source_pull (id)
);
create index building_char_pin on building_char (pin, tax_year desc);
