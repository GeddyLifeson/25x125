-- Audit log (who, which organization, what, when) for saved edits, deal changes, exports and account changes;
-- token buckets for rate limits; a record of account deletions without personal data.
create table audit_log (
  id bigserial primary key,
  org_id text default current_setting('app.org_id', true) references org(id) on delete cascade,
  user_id text references account_user(id) on delete set null,
  action text not null,          -- e.g. deal.create, deal.update, override.save, export.pdf, invite.create
  target text,                   -- e.g. deal 12, PIN 16121020310000
  detail jsonb not null default '{}',
  ip text,
  created_at timestamptz not null default now()
);
create index audit_log_org on audit_log (org_id, created_at desc);
alter table audit_log enable row level security;
alter table audit_log force row level security;
-- Members add rows and read their organization's rows; nobody edits or removes them through the app.
create policy audit_read on audit_log for select using (org_id = current_setting('app.org_id', true));
create policy audit_add on audit_log for insert with check (org_id = current_setting('app.org_id', true));
grant insert on audit_log to x25_app;

create table rate_bucket (
  key text primary key,          -- bucket name and caller, e.g. search:user:<id> or export:ip:1.2.3.4
  tokens double precision not null,
  updated_at timestamptz not null default now()
);
revoke all on rate_bucket from x25_app;

create table deletion_log (
  id bigserial primary key,
  email_sha256 text not null,    -- to answer "was my account deleted?" without keeping the address
  orgs_deleted integer not null,
  rows_deleted jsonb not null default '{}',
  requested_by text not null,    -- self (account page) or admin (python -m jobs.delete_account)
  deleted_at timestamptz not null default now()
);
revoke all on deletion_log from x25_app;
