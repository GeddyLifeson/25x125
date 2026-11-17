-- Regions outside Illinois (docs/regions.md). One database serves one region; loaders add the region's
-- county and city rows from data/regions/<id>/region.json.
alter table county drop constraint if exists county_state_check;
alter table county alter column state drop default;
alter table county alter column state set default 'IL';

-- Where a price comes from: 'sale' (a recorded sale price) or 'appraisal' (an appraisal district's market
-- value, used in Texas where sale prices are not public). Screens label the two differently.
alter table comp add column if not exists basis text not null default 'sale';
alter table sale add column if not exists qualification text;   -- e.g. Florida DOR sale qualification code

-- Values straight from an appraiser's roll (Florida just value, Texas market value): no level of assessment.
alter table assessed_value alter column stage set default 'certified';
