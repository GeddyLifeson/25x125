-- Monthly construction price indexes for escalating cost presets (decision 23, docs/research/decisions-2026-10-30.md).
-- census_uc: Census constant-quality (Laspeyres) price index of new single-family houses under construction, 2005 = 100.
--   The primary escalator: it prices whole houses, labor and margin included.
-- ppi_resi_inputs: BLS PPI net inputs to residential construction, goods (WPUIP2311001). Materials only; a signal.
create table cost_escalation_index (
  series text not null,
  month date not null,            -- first day of the month
  value numeric not null,
  status text,                    -- 'p' preliminary, 'r' revised, null final
  source_pull_id bigint references source_pull (id),
  primary key (series, month)
);

-- Latest month per series, the change since the presets' base month, and the trailing 12-month rate used to
-- escalate costs to the build midpoint.
create view cost_escalation as
select i.series, i.month as latest_month, i.value as latest_value, i.status,
       y.value as value_12m_ago, round(i.value / y.value - 1, 4) as change_12m
from cost_escalation_index i
left join cost_escalation_index y on y.series = i.series and y.month = (i.month - interval '12 months')::date
where i.month = (select max(month) from cost_escalation_index x where x.series = i.series);
