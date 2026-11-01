-- Parcel signals: building violations, 311 vacant building and lot requests, the scofflaw list,
-- city-owned land and demolition notices. Each row is one source record with a point; pin10 is the lot
-- the point falls on, set by jobs.build_parcel_site.

create table parcel_signal (
  kind text not null,                      -- 'violation', 'vacant_building_311', 'vacant_lot_311',
                                           -- 'scofflaw', 'city_owned', 'demolition_notice'
  source_id text not null,
  signal_date date,
  status text,
  detail text,
  address text,
  pin text,                                -- only where the source gives one (city-owned land)
  pin10 text,
  attrs jsonb not null default '{}',
  geom geometry(Point, 4326),
  source_pull_id bigint not null references source_pull (id),
  primary key (kind, source_id)
);
create index parcel_signal_geom on parcel_signal using gist (geom);
create index parcel_signal_pin10 on parcel_signal (pin10, kind);

alter table parcel_site
  add column open_violations integer,      -- open building violations recorded since 2021
  add column last_violation_date date,
  add column vacant_building_311 integer,  -- vacant or abandoned building complaints, last 3 years
  add column vacant_lot_311 integer,       -- vacant lot cleaning requests, last 3 years
  add column scofflaw boolean,
  add column city_owned_status text,       -- property status from the city land inventory
  add column demolition_notice_date date;  -- latest demolition notice of intent since 2021
