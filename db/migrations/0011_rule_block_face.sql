-- Rule tables seeded from data/rules (jobs.seed_rules), and block faces for the block-face tests in
-- RS-3 (17-2-0303-B), the 606 district (17-7-0593) and the Pilsen district (17-7-0583).

create table rule (
  rule_set text not null,                  -- 'zoning_district', 'zoning_height', 'zoning_step', 'special_district', ...
  rule_key text not null,
  municipality_id text not null default 'chicago' references municipality (id),
  value jsonb not null,
  section text,                            -- code section or other citation
  source_url text,
  source_file text not null,               -- the data/rules file it was seeded from
  effective_from date,
  effective_to date,
  verified_on date,
  seeded_at timestamptz not null default now(),
  primary key (rule_set, rule_key, municipality_id)
);

-- What stands on each lot now. units_now counts dwelling units: condo unit PINs, Assessor apartments for
-- 2-6 unit buildings, 1 for houses and townhouses, at least 7 for 7+ unit classes.
create table lot_use (
  pin10 text primary key,
  use_now text not null,                   -- 'vacant', 'single', 'multi', 'other'
  units_now integer,
  block_face text,                         -- '<dir> <street>|<even/odd>|<hundred block>'
  built_at timestamptz not null default now()
);
create index lot_use_block_face on lot_use (block_face);

create view block_face as
select block_face,
       count(*) as lots,
       count(*) filter (where use_now = 'multi') as multi_lots,
       count(*) filter (where use_now = 'single') as single_lots,
       count(*) filter (where use_now = 'multi' and units_now = 2) as two_flat_lots,
       count(*) filter (where use_now = 'vacant') as vacant_lots,
       count(*) filter (where use_now = 'other') as other_lots
from lot_use where block_face is not null group by block_face;
