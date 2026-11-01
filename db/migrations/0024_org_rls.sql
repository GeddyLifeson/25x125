-- Organizations on every deal, outreach entry, saved search and saved set of feasibility edits, with
-- row-level security keyed on the per-request setting app.org_id (the engine sets it from the signed request).

-- Existing deals go to the default organization.
insert into org (id, name)
  select distinct org_id, org_id from deal where org_id is not null and org_id not in (select id from org);
update deal set org_id = 'default' where org_id is null;
alter table deal
  alter column org_id set default current_setting('app.org_id', true),
  alter column org_id set not null,
  add constraint deal_org_fk foreign key (org_id) references org(id) on delete cascade,
  add constraint deal_id_org unique (id, org_id);

alter table deal_event add column org_id text;
update deal_event e set org_id = d.org_id from deal d where d.id = e.deal_id;
alter table deal_event
  alter column org_id set default current_setting('app.org_id', true),
  alter column org_id set not null,
  drop constraint deal_event_deal_id_fkey,
  add constraint deal_event_deal_org_fk foreign key (deal_id, org_id) references deal(id, org_id) on delete cascade;
create index deal_event_org on deal_event (org_id);

-- Map and list filters saved by name (alerts come in version 1.1).
create table saved_search (
  id bigserial primary key,
  org_id text not null default current_setting('app.org_id', true) references org(id) on delete cascade,
  user_id text references account_user(id) on delete set null,
  name text not null,
  params text not null,                  -- the map's query string, e.g. community_area=23&min_score=50
  created_at timestamptz not null default now()
);
create index saved_search_org on saved_search (org_id);

-- Feasibility edits saved to the account for a parcel (outside a deal), same JSON shape the engine takes.
create table saved_override (
  org_id text not null default current_setting('app.org_id', true) references org(id) on delete cascade,
  pin text not null,
  exit text check (exit in ('sell', 'hold')),
  target text,
  overrides jsonb not null default '{}',
  updated_by text references account_user(id) on delete set null,
  updated_at timestamptz not null default now(),
  primary key (org_id, pin)
);

do $$
declare t text;
begin
  foreach t in array array['deal', 'deal_event', 'saved_search', 'saved_override'] loop
    execute format('alter table %I enable row level security', t);
    execute format('alter table %I force row level security', t);
    execute format(
      'create policy org_rows on %I using (org_id = current_setting(''app.org_id'', true))'
      ' with check (org_id = current_setting(''app.org_id'', true))', t);
  end loop;
end
$$;

-- The restricted role reads the public data tables (feasibility runs inside a deal request) and changes only
-- organization rows. Sign-in tokens and sessions stay out of its reach.
grant select on all tables in schema public to x25_app;
alter default privileges in schema public grant select on tables to x25_app;
revoke all on auth_token, auth_session from x25_app;
grant insert, update, delete on deal, deal_event, saved_search, saved_override to x25_app;
grant usage on all sequences in schema public to x25_app;
alter default privileges in schema public grant usage on sequences to x25_app;
