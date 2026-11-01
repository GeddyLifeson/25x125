-- Deals: saved parcels, their stage, the feasibility edits saved with them, and the owner outreach log.
-- org_id stays empty until sign-in and organizations arrive (TASKS.md, SaaS setup); every deal will then carry one.
create table deal (
  id bigserial primary key,
  org_id text,
  pin text not null,                     -- 14-digit PIN the deal was saved from
  pin10 text not null,
  address text,
  stage text not null default 'lead'
    check (stage in ('lead', 'contacted', 'feasibility', 'under_contract', 'passed')),
  next_step text,
  next_step_on date,
  exit text check (exit in ('sell', 'hold')),
  target text,                           -- rezoning target picked on the feasibility screen, if any
  scenario integer,                      -- 0, 1 or 2: scenario A, B or C
  scenario_name text,
  overrides jsonb not null default '{}', -- the feasibility screen's edits, same shape the engine takes
  result jsonb,                          -- snapshot of the saved scenario's numbers, with the date it was run
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index deal_org on deal (org_id);
create index deal_pin10 on deal (pin10);

create table deal_event (
  id bigserial primary key,
  deal_id bigint not null references deal(id) on delete cascade,
  kind text not null check (kind in ('letter', 'call', 'text', 'email', 'visit', 'meeting', 'note', 'reminder')),
  event_on date not null default current_date,
  note text not null default '',
  created_at timestamptz not null default now()
);
create index deal_event_deal on deal_event (deal_id, event_on);
