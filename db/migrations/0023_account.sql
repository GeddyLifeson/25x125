-- Accounts: users, organizations, memberships, invites, sign-in links and sessions (TASKS.md step 6, SaaS setup).
-- Sign-in is by emailed link only; no passwords are stored. Tokens are stored as SHA-256 hashes, never in the clear.

-- The restricted role the engine switches to for organization data, so row-level security applies even when the
-- engine logs in as the database owner (owners and superusers skip row-level security otherwise).
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'x25_app') then
    create role x25_app nologin;
  end if;
end
$$;
grant x25_app to current_user;
grant usage on schema public to x25_app;

create table account_user (
  id text primary key default gen_random_uuid()::text,
  email text not null unique check (email = lower(email) and position('@' in email) > 1),
  name text,
  trial_used boolean not null default false,   -- one free Pro trial per person
  created_at timestamptz not null default now(),
  last_sign_in_at timestamptz
);

create table org (
  id text primary key default gen_random_uuid()::text,
  name text not null,
  created_at timestamptz not null default now()
);
-- Deals saved before sign-in existed move to this organization (0024).
insert into org (id, name) values ('default', 'Default organization');

create table membership (
  org_id text not null references org(id) on delete cascade,
  user_id text not null references account_user(id) on delete cascade,
  role text not null check (role in ('owner', 'member')),
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);
-- One owner per team (docs/v1-spec.md, Accounts).
create unique index membership_one_owner on membership (org_id) where role = 'owner';
create index membership_user on membership (user_id);

create table org_invite (
  id bigserial primary key,
  org_id text not null references org(id) on delete cascade,
  email text not null check (email = lower(email)),
  role text not null default 'member' check (role = 'member'),
  invited_by text references account_user(id) on delete set null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default now() + interval '14 days',
  accepted_at timestamptz,
  unique (org_id, email)
);
create index org_invite_email on org_invite (email) where accepted_at is null;

-- One-use sign-in links.
create table auth_token (
  token_hash text primary key,
  email text not null,
  next_path text,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz
);
create index auth_token_email on auth_token (email, created_at desc);

create table auth_session (
  token_hash text primary key,
  user_id text not null references account_user(id) on delete cascade,
  org_id text references org(id) on delete set null,   -- the organization the user is working in
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  last_seen_at timestamptz not null default now()
);
create index auth_session_user on auth_session (user_id);
