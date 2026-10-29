-- One row per Chicago PIN with what the rules engine needs: zoning, lot size and frontage.
-- Rebuilt by jobs/build_parcel_site.py after the nightly loads.

create table parcel_site (
  pin text primary key references parcel (pin),
  pin10 text not null,
  zone_class text,                         -- district covering the parcel point
  zone_share numeric,                      -- share of the lot inside that district (1.0 = whole lot)
  lot_sqft numeric,
  frontage_ft numeric,
  depth_ft numeric,
  lot_source text,                         -- e.g. 'polygon 2025', or 'assessor'
  built_at timestamptz not null default now()
);
create index parcel_site_zone on parcel_site (zone_class);
