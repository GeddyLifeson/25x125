-- Census ACS 5-year median gross rent (B25031 by bedrooms, B25064 all units), by census tract and ZIP area
-- (ZCTA), with the margin of error; and Zillow rent index growth by ZIP (internal use only: never shown).
create table acs_rent (
  geo_kind text not null,    -- 'tract' or 'zcta'
  geo_id text not null,
  vintage text not null,     -- e.g. '2020-2024'
  bedrooms text not null,    -- 'all', '0', '1', '2', '3', '4', '5+'
  median_rent numeric,       -- dollars per month, gross (rent plus utilities)
  moe numeric,
  source_pull_id bigint not null references source_pull (id),
  primary key (geo_kind, geo_id, vintage, bedrooms)
);

create table zori_growth (
  zip text not null,
  month date not null,
  zori numeric not null,     -- internal only: used for growth ratios, never displayed (CLAUDE.md)
  source_pull_id bigint not null references source_pull (id),
  primary key (zip, month)
);
