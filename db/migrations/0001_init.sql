-- Base schema: PostGIS, geography as a data dimension, and source tracking.
create extension if not exists postgis;

-- Illinois only. Chicago is loaded first; suburbs and other counties come later as rows, not code.
create table county (
  id text primary key,            -- e.g. 'cook'
  name text not null,
  state text not null default 'IL' check (state = 'IL')
);

create table municipality (
  id text primary key,            -- e.g. 'chicago'
  name text not null,
  county_id text not null references county (id),
  loaded boolean not null default false
);

insert into county (id, name) values ('cook', 'Cook');
insert into municipality (id, name, county_id, loaded) values ('chicago', 'Chicago', 'cook', true);

-- One row per pull from an outside source. Every value table links here.
create table source_pull (
  id bigserial primary key,
  host text not null,             -- e.g. data.cityofchicago.org
  dataset_id text not null,       -- e.g. ydr8-5enu
  query text not null default '',
  started_at timestamptz not null,
  finished_at timestamptz,
  row_count integer,
  status text not null check (status in ('running', 'ok', 'failed')),
  note text not null default ''
);
create index source_pull_dataset on source_pull (dataset_id, started_at desc);
