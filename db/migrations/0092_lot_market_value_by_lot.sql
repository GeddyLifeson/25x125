-- Same rows as 0057's lot_market_value, but the per-PIN pick is keyed on (pin10, pin), so a lookup for one lot
-- (where pin10 = ...) reads that lot's rows through the pin10 index. The old view sorted every assessed value in
-- the county first: 1.2 seconds per parcel page and feasibility run.
create or replace view lot_market_value as
with pick as (
  select distinct on (pin10, pin) *
  from assessed_value
  order by pin10, pin, (stage = 'board') desc, tax_year desc
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
