-- Neighborhood construction cost index from new 2-6 unit building permits (jobs/build_cost_index.py), and
-- permit wait times by review path. Rebuilt monthly.
create table cost_index (
  community_area_num integer primary key,
  community_area text not null,
  permits integer not null,
  index_raw numeric,          -- weighted median of reported cost per unit / city median for the unit group
  p25 numeric,
  p75 numeric,
  index numeric not null,     -- after the thin-area blend with neighboring community areas
  neighbor_weight numeric not null,
  thin boolean not null,
  computed_on date not null
);

create table cost_permit (
  permit_id text primary key,
  community_area_num integer,
  issue_date date,
  units integer not null,
  reported_cost numeric not null,
  per_unit numeric not null,
  review_type text,
  processing_days integer,
  description text
);

create table permit_wait (
  review_type text primary key,
  permits integer not null,
  days_p25 numeric, days_median numeric, days_p75 numeric,
  computed_on date not null
);
