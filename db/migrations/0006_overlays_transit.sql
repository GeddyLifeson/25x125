-- Map overlays (TIF districts, historic survey ratings, landmarks) and transit stations.

create table overlay (
  kind text not null,                      -- 'tif', 'historic_survey', 'landmark'
  source_id text not null,                 -- id within the source layer
  name text,
  rating text,                             -- historic survey color (Red, Orange, ...) where it applies
  attrs jsonb not null default '{}',
  geom geometry(MultiPolygon, 4326) not null,
  source_pull_id bigint not null references source_pull (id),
  primary key (kind, source_id)
);
create index overlay_geom on overlay using gist (geom);

create table transit_station (
  mode text not null,                      -- 'cta' or 'metra'
  station_id text not null,
  name text not null,
  lines text,
  geom geometry(Point, 4326) not null,
  source_pull_id bigint not null references source_pull (id),
  primary key (mode, station_id)
);
create index transit_station_geom on transit_station using gist (geom);

alter table parcel_site
  add column historic_rating text,         -- Red or Orange: 90-day demolition hold
  add column landmark_name text,
  add column tif_name text,
  add column cta_rail_ft integer,          -- straight-line feet to the nearest CTA rail station
  add column metra_ft integer;             -- straight-line feet to the nearest Metra station in Chicago or nearby
