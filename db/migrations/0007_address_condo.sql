-- Property addresses (with taxpayer and owner mailing names) and condo unit characteristics.
create extension if not exists pg_trgm;

create table parcel_address (
  pin text primary key,
  tax_year integer not null,
  address text,                            -- e.g. 1244 N KEDZIE AVE
  zip text,
  mail_name text,                          -- taxpayer mailing name
  mail_address text,
  owner_name text,
  owner_address text,
  source_pull_id bigint not null references source_pull (id)
);
create index parcel_address_trgm on parcel_address using gin (address gin_trgm_ops);

create table condo_char (
  row_id text primary key,
  pin text not null,
  pin10 text not null,
  tax_year integer not null,
  unit_sqft integer,
  building_sqft integer,
  building_pins integer,
  bedrooms integer,
  year_built integer,
  is_parking_space boolean,
  is_common_area boolean,
  building_is_mixed_use boolean,
  tieback_key_pin text,                    -- groups the units of one building
  source_pull_id bigint not null references source_pull (id)
);
create index condo_char_pin on condo_char (pin, tax_year desc);
create index condo_char_building on condo_char (pin10, tax_year);
