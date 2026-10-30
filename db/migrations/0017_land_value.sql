-- Land sales (vacant lots and teardowns) and the land value map built from them (jobs/build_land_values.py).
create table land_sale (
  sale_row_id text primary key,
  pin text not null,
  pin10 text not null,
  kind text not null,             -- 'vacant' or 'teardown'
  sale_date date not null,
  price numeric not null,
  lot_sqft numeric not null,
  far numeric,
  per_lot_sqft numeric not null,
  per_lot_sqft_std numeric not null,   -- price moved to a 3,125 sq ft lot with the lot-size elasticity, per sq ft
  per_buildable_sqft numeric,
  nbhd_code text,
  community_area_num integer,
  evidence text                   -- for teardowns: the permit that followed the sale
);

create table land_value (
  geo_kind text not null,         -- 'nbhd' or 'community_area'
  geo_id text not null,
  kind text not null,             -- 'vacant', 'teardown', 'all'
  sales integer not null,
  median_per_lot_sqft numeric,
  median_per_lot_sqft_std numeric,
  median_per_buildable_sqft numeric,
  first_sale date,
  last_sale date,
  computed_on date not null,
  primary key (geo_kind, geo_id, kind)
);
