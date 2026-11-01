-- Plans and Stripe billing on the organization. Plan prices and features live in data/rules/plans.json.
alter table org
  add column plan text not null default 'free' check (plan in ('free', 'pro')),
  -- none: never subscribed; trialing: 14-day Pro trial; active, past_due, canceled, unpaid, incomplete: Stripe's
  -- subscription status; comp: Pro at no charge, set by hand (the default organization, testers).
  add column plan_status text not null default 'none'
    check (plan_status in ('none', 'trialing', 'active', 'past_due', 'canceled', 'unpaid', 'incomplete',
                           'incomplete_expired', 'paused', 'comp')),
  add column trial_ends_at timestamptz,
  add column current_period_end timestamptz,
  add column founding boolean not null default false,   -- founding price ($79) instead of the list price
  add column stripe_customer_id text unique,
  add column stripe_subscription_id text,
  add column stripe_price_id text,
  add column plan_updated_at timestamptz;
update org set plan = 'pro', plan_status = 'comp', plan_updated_at = now() where id = 'default';

-- Stripe webhook events already handled, so a resent event changes nothing twice.
create table stripe_event (
  id text primary key,
  type text not null,
  org_id text,
  received_at timestamptz not null default now()
);
revoke all on stripe_event from x25_app;
