-- Cook County Assessor assessed values (uzyt-m557) for Chicago PINs, with the Assessor's market value
-- (assessed value / level of assessment from data/rules/assessment_levels.json). Used for the existing-use check.
create table assessed_value (
  pin text not null,                 -- 14 digits
  pin10 text not null,
  tax_year integer not null,
  class text,
  nbhd text,
  stage text not null,               -- best stage with a value: board, certified or mailed
  land_av numeric,
  bldg_av numeric,
  total_av numeric,
  level numeric,                     -- level of assessment used (0.10, 0.20, 0.25); null for exempt
  incentive_class boolean not null default false,
  market_value numeric,              -- total_av / level
  land_market_value numeric,         -- land_av / level
  source_pull_id bigint references source_pull (id),
  primary key (pin, tax_year)
);
create index on assessed_value (pin10);

-- One row per lot (10-digit PIN): the newest tax year with a final (board) value if there is one, else the
-- newest year at any stage, summed over the lot's PINs (condo units and multi-PIN lots).
create view lot_market_value as
with pick as (
  select distinct on (pin) *
  from assessed_value
  order by pin, (stage = 'board') desc, tax_year desc
)
select pin10,
       max(tax_year) as tax_year,
       min(tax_year) as oldest_tax_year,
       string_agg(distinct stage, ', ') as stages,
       count(*) as pins,
       count(*) filter (where market_value is null) as pins_without_value,
       sum(market_value) as market_value,
       sum(land_market_value) as land_market_value,
       sum(total_av) as total_av,
       bool_or(incentive_class) as any_incentive_class,
       max(source_pull_id) as source_pull_id
from pick
group by pin10;
