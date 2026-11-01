-- Feedback from people checking the app's numbers (the 2-week contractor trial, 2026-11). This is for the
-- product owner, not organization data: no row-level security, and the restricted role cannot read or write it.
-- The engine inserts as the database owner; only emails in ADMIN_EMAILS read it back (engine/feedback.py).
create table feedback (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  user_id text references account_user(id) on delete set null,
  email text check (email is null or (email = lower(email) and position('@' in email) > 1)),
  org_id text references org(id) on delete set null,
  page_path text,                       -- where the form was opened from, e.g. /parcels/<pin>/feasibility
  pin text,
  scenario text check (scenario is null or scenario in ('A', 'B', 'C')),
  screen text,                          -- feasibility, general, ...
  rating smallint check (rating between 1 and 5),   -- How close were the numbers to what you would expect?
  cost_per_sqft_own numeric check (cost_per_sqft_own >= 0),   -- their own hard cost per sq ft, dollars
  cost_total_own numeric check (cost_total_own >= 0),         -- their own total cost, dollars
  sale_per_unit_own numeric check (sale_per_unit_own >= 0),   -- their own sale price per unit, dollars
  numbers_wrong text,                   -- Which numbers looked wrong, and what should they be?
  outside_questions text,               -- What did you have to look up or answer outside the app?
  missing text,                         -- What was missing?
  minutes_spent integer check (minutes_spent between 0 and 1440),
  would_use text check (would_use in ('yes', 'maybe', 'no')),
  notes text,
  -- The app's figures on screen when the form was opened: total_cost, cost_per_unit, hard_cost_per_sqft,
  -- total_cost_per_sqft, sale_per_unit, profit, max_land_price, preset, cost_index, units, gross_sqft, exit, ...
  app_snapshot jsonb not null default '{}'
);
create index feedback_created on feedback (created_at desc);
create index feedback_pin on feedback (pin);
revoke all on feedback from x25_app;
revoke all on feedback_id_seq from x25_app;
