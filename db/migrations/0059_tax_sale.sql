-- Properties in the Cook County Annual Tax Sale, from the Treasurer's free per-ward lists
-- (https://www.cookcountytreasurer.com/delinquenttaxes.aspx). Owner names and mailing addresses are not stored.
create table tax_sale_list (
  sale_date date not null,           -- first day of the sale the list is for
  pin text not null,                 -- 14 digits
  pin10 text not null,
  ward integer,
  property_address text,
  volume text,
  tax_type text,
  tax_year integer,                  -- delinquent tax year
  total_tax_due numeric,
  total_due numeric,                 -- including interest, as of listed_through
  classification text,
  listed_through date,               -- the date the Treasurer's amounts run to
  source_url text,
  source_pull_id bigint references source_pull (id),
  primary key (sale_date, pin, tax_type, tax_year)   -- a PIN can owe several years or a special assessment
);
create index on tax_sale_list (pin10);

-- The flag on the lot shows only until the sale starts (build_parcel_site sets it for sale dates today or later).
alter table parcel_site
  add column tax_sale_date date,
  add column tax_sale_due numeric,     -- sum over the lot's PINs on the list
  add column tax_sale_pins integer;
