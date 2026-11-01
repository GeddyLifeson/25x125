-- Sales of older 2-6 unit buildings (Assessor class 211, built before 2014). Where no new-construction comps sit
-- within 3 miles, the sale estimate reads the local median of these and converts it to a new-construction
-- price with the curve in data/rules/older_sale_fallback.json (engine/older_sales.py).
create table older_sale (
  sale_row_id text primary key,
  pin text not null,
  sale_date date not null,
  price numeric not null,
  units integer not null,
  price_per_unit numeric not null,
  year_built integer,
  community_area text,
  geom geometry(Point, 4326),
  built_at timestamptz not null default now()
);
create index older_sale_geom on older_sale using gist (geom);
create index older_sale_date on older_sale (sale_date);
