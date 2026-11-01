-- Parcel universe and recorded sales, copied nightly from the Cook County data catalog.

create table parcel (
  pin text primary key,                    -- 14 digits
  pin10 text not null,
  tax_year integer not null,
  municipality_id text not null references municipality (id),
  class text,
  township_code text,
  nbhd_code text,                          -- Assessor neighborhood
  ward integer,
  community_area_num integer,
  community_area_name text,
  tract_geoid text,
  zip text,
  tif_district_num text,
  tif_district_name text,
  ssa_name text,
  flood_fema_sfha boolean,
  geom geometry(Point, 4326),
  source_pull_id bigint not null references source_pull (id)
);
create index parcel_pin10 on parcel (pin10);
create index parcel_nbhd on parcel (nbhd_code);
create index parcel_ca on parcel (community_area_num);
create index parcel_geom on parcel using gist (geom);

create table sale (
  row_id text primary key,                 -- Assessor's row id
  pin text not null,
  sale_date date not null,
  sale_price numeric not null,
  doc_no text,
  deed_type text,
  class text,
  township_code text,
  nbhd_code text,
  is_multisale boolean,
  num_parcels_sale integer,
  filter_same_sale_within_365 boolean,
  filter_less_than_10k boolean,
  filter_deed_type boolean,
  source_pull_id bigint not null references source_pull (id)
);
create index sale_pin_date on sale (pin, sale_date desc);
create index sale_date on sale (sale_date);
