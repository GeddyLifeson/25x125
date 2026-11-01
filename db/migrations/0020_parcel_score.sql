-- Development score per lot (data/rules/development_score.json), rebuilt nightly by jobs/score_parcels.py.
-- Points are stored by part so the screen can show each one and re-weight them per user.
create table parcel_score (
  pin10 text primary key,
  pin text not null,                -- the PIN priced (lowest PIN on the lot)
  score numeric not null,           -- 0-100 after penalties
  zoning_upside numeric not null,
  profit numeric not null,
  acquisition numeric not null,
  location numeric not null,
  incentives numeric not null,
  penalties numeric not null,
  units_now integer,
  by_right_units integer,
  units_priced integer,             -- 2-6 unit program priced by right, null when none fits
  sale_per_unit numeric,
  sale_comps integer,
  land numeric,
  total_cost numeric,
  profit_central numeric,
  profit_p25 numeric,
  return_on_cost numeric,
  return_on_cost_p25 numeric,
  max_land_price numeric,
  details jsonb not null default '{}',  -- which signals, programs and penalties scored, and why profit is missing
  computed_on date not null
);
create index parcel_score_score on parcel_score (score desc);
