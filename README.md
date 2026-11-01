# 25x125

Development pipeline software for small real estate companies in Illinois, starting with Chicago. For any parcel it shows what zoning allows, what a 2-6 unit or small mixed-use building would cost there (in dollars, with dollar margins), which incentives apply, and whether the project makes money as a sale or a hold.

Named for the standard Chicago lot: 25 by 125 feet.

## Status

Planning and calibration are done (2026-10-29). Step 0 (setup) is in place: database, engine skeleton, web skeleton, migrations, tests and CI. Next is Step 1 in `TASKS.md`.

## What's here

| Path | What it is |
| --- | --- |
| `CLAUDE.md` | Project instructions for Claude Code: stack, rules, data, MLS and legal limits |
| `KICKOFF.md` | First prompt to paste into Claude Code |
| `TASKS.md` | Steps 0-8 to V1, then V1.1, as checklists |
| `docs/calibration-2026-10-29.md` | Cost and comp calibration against the test set |
| `docs/international-practices.md` | Practices from other countries adopted into the plan |
| `docs/v1-spec.md` | Version 1 build spec |
| `docs/plan.md` | Full business plan, all pipeline stages and brands |
| `docs/module-outlines.md` | Outlines for modules 1-11 |
| `data/rules/` | Zoning table and steps, feasibility defaults, score weights, incentives, each with sources |
| `data/sources/datasets.csv` | Every public dataset ID and endpoint |
| `data/reference/` | Test parcels, neighborhood cost index, cleaned permit rows (pulled 2026-10-28) |
| `scripts/research/` | Scripts that produced the reference data |
| `mockups/` | Search, parcel, feasibility and deals screen mockups |
| `martin/` | Tile server config for the map's vector tiles |

## Getting started

Works the same on Windows, Mac and Linux. Install Git, Docker Desktop, Python 3.12 and Node 22.

1. Copy `.env.example` to `.env`. No keys are needed to start.
2. Start the database and the map tile server: `docker compose up -d` (the tile server, Martin, restarts until step 4 has created its functions)
3. Install the Python side: `python -m venv .venv`, activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` elsewhere), then `python -m pip install -e ".[dev]"`
4. Create the tables: `python -m db.migrate`
5. Run the tests: `python -m pytest`
6. Start the engine: `python -m uvicorn engine.app:app --port 8000`, then open http://localhost:8000/health
7. Start the web app: `cd web`, `npm install`, `npm run dev`, then open http://localhost:3000

| Folder | What it is |
| --- | --- |
| `core/` | Shared settings, database access, source tracking, Socrata client |
| `db/` | SQL migrations and the runner |
| `engine/` | Rules and feasibility engine (FastAPI) |
| `jobs/` | Loaders and nightly jobs |
| `web/` | Next.js app |
| `tests/` | Python tests; the database tests skip unless the database from step 2 is running |

## Data

Version 1 uses free public data from the Chicago Data Portal, the Cook County data catalog, the Census Bureau and HUD. MLS data from MRED comes later under a separate license.

Results are estimates. They are not zoning, legal, tax or appraisal advice.

## Web app

The web app in `web/` reads everything through the engine; it never calls the data portals.

1. Start the engine: `python -m uvicorn engine.app:app --port 8000`
2. In another terminal: `cd web`, `npm install`, `npm run dev`, then open http://localhost:3000
3. To point the app at an engine on another port, set `ENGINE_URL` first (PowerShell: `$env:ENGINE_URL="http://localhost:8010"`; Mac and Linux: `export ENGINE_URL=http://localhost:8010`).

Screens: the map and list (`/map`), address or PIN search (`/`), deals (`/deals`), the parcel page (`/parcels/<pin>`) and the feasibility screen (`/parcels/<pin>/feasibility`). On the feasibility screen every assumption can be edited and re-run; edits are kept in the browser per parcel. Exports: a one-page PDF (`/parcels/<pin>/report.pdf`), the lines as CSV (`/parcels/<pin>/feasibility.csv`), and the assumptions as a `scenario,field,value` CSV that can be imported again (example: `web/scripts/sample-overrides.csv`).

Checks: `npm run typecheck`, `npm run build`, and with the engine, the tile server and the web app running, `node scripts/smoke.cjs http://localhost:3000` (needs the `playwright` package and Chromium; screenshots go to `web/screenshots/`, which git ignores). Set `ENGINE_URL` for the smoke run too. It signs in as `smoke-test@example.com` through dev mode (keep `EMAIL_SERVER` empty), and at the end deletes its deals, its feedback entries and its own account. For the feedback admin check, start the engine with `ADMIN_EMAILS=smoke-test@example.com`.

## Map, list and deals

- **Map and list** (`/map`): the scored lots from the nightly run, filtered by community area, zoning prefix, minimum score, minimum units by right, a signal, vacant land, city lots for sale and the fast path; sorted by score, return on cost (25th percentile), extra units by right or lot size. Each lot shows its points by part, its signals and penalties, and why it has no profit points when it has none. Filters stay in the address bar. "Export list as CSV" downloads up to 5,000 rows with the same filters (`GET /lots?format=csv`).
- The map draws lots coloured by score. From zoom 14 in it shows every lot's shape; farther out it shows points for lots scoring 20 or more (zoom 13), 40 or more (zoom 11-12) or 50 or more (zoom 10), so tiles stay small. Click a lot for its points, the by-right numbers and links to the parcel page and feasibility screen.
- Layers: fast-path lots, land value per lot sq ft (by Assessor neighborhood or community area, paler where fewer than 5 sales) and public lots for sale (City of Chicago ChiBlockBuilder and city land, Cook County Land Bank) with asking price, deadline and the apply link.
- Tiles come from Martin (`docker compose` service `tiles`, http://localhost:3100/catalog), which runs the PostGIS functions in `db/migrations/0022_map_tiles.sql`. The web app passes them through at `/tiles/...`; set `TILES_URL` if Martin runs elsewhere. The basemap is OpenFreeMap's Positron style (no key; attribution shows on the map). Set `NEXT_PUBLIC_BASEMAP_STYLE` to another style URL, or to `none` for a plain background, before `npm run build`.
- **Deals** (`/deals`): pipeline counts by stage (lead, contacted, feasibility, under contract, passed), the deal table, and the owner outreach log with the TCPA and CAN-SPAM note. Save a deal from the map panel, the parcel page or the feasibility screen; from feasibility the deal keeps the edits on screen, and the engine re-runs the scenario and stores its numbers with the date. "Feasibility" on a deal reopens it with those edits. CSV out: deals and the outreach log; CSV in: deals (a `pin` column, plus any of stage, next_step, next_step_on, notes, address, overrides; a row with an existing `id` updates that deal).
- Engine endpoints: `GET/POST /deals`, `GET/PATCH/DELETE /deals/{id}`, `POST /deals/{id}/rerun`, `GET/POST /deals/{id}/events`, `DELETE /deals/{id}/events/{event_id}`, `GET /deals/pipeline`, `GET /deals/events`, `POST /deals/import` (CSV body), `GET /lots/{pin10}`, `GET /community-areas`, `GET /community-areas/{num}/snapshot`.
- Deals belong to an organization and need sign-in and a plan with deals (Pro or the trial); see below.

## Accounts, plans and operations

**Sign-in.** Email link only, no passwords (`/signin`). The engine stores users, organizations, memberships, invites, one-use sign-in links (30 minutes) and 30-day sessions in Postgres (`db/migrations/0023_account.sql`); tokens are kept as SHA-256 hashes. The web app holds the session in an http-only cookie (`x25_session`).

- Dev mode: with `EMAIL_SERVER` empty on the engine, no email is sent. The link prints in the engine console and is saved in `.dev-mail/<email>.txt` in the repo folder, and the sign-in page says so. With `APP_ENV=production` the engine refuses to run without `EMAIL_SERVER`.
- To send real email set `EMAIL_SERVER` (any SMTP provider; for now Gmail with an app password, see docs/deploy.md) and `EMAIL_FROM` on the engine, and `APP_URL` on the web app.
- Signed out, these work: address search, the parcel page, the map and list, and the feasibility screen (edits stay in the browser). Deals, edits saved to the account, saved searches, PDF and CSV exports, and teammates need sign-in and Pro.

**Organizations.** The first sign-in creates an organization with the user as owner and a 14-day Pro trial (one trial per person). The owner invites teammates by email on `/account`; they join when they sign in with that address. One owner per organization. Deals, the outreach log, saved searches (`saved_search`) and saved feasibility edits (`saved_override`) carry `org_id`, and Postgres row-level security limits every query to the caller's organization (`0024_org_rls.sql`). Deals saved before sign-in existed are in the `default` organization (Pro at no charge).

**How the engine knows who is calling.** The web app signs a short claim (user, organization, client IP, 60-second expiry) with HMAC-SHA256 and `ENGINE_SHARED_SECRET`, in the `X-25x125-Claim` header. Organization routes refuse calls without a valid claim, check the membership in the database, then switch to the restricted `x25_app` role and set `app.org_id` for that transaction. Set the same `ENGINE_SHARED_SECRET` on both; empty uses a dev-only value, which production refuses.

**Plans and Stripe.** Prices and features are data: `data/rules/plans.json` (Free; Pro $129 a month; founding price $79 a month, set per organization with `org.founding`). Engine routes: `GET /billing/plans`, `POST /billing/checkout` (Stripe Checkout with Stripe Tax on; time left on the trial carries over), `POST /billing/portal`, `POST /billing/webhook` (signature checked with `STRIPE_WEBHOOK_SECRET`; sets the organization's plan and status; each event handled once). The web app forwards Stripe's webhook from `/api/billing/webhook`. Without `STRIPE_SECRET_KEY` the buttons are off and the trial still works. Local webhook test: `stripe listen --forward-to localhost:3000/api/billing/webhook` (Stripe CLI, test mode).

**Feedback on the numbers.** For the contractor trial: "Check these numbers" on the feasibility screen (one per scenario, and on the cost card) opens `/feedback?pin=...&scenario=A` with that scenario's figures as shown: total cost, cost per unit, hard and total cost per sq ft, sale price per unit, profit, max land price at 20%, preset and cost index. They are read-only, next to boxes for the person's own hard cost per sq ft, total cost and sale price per unit, with the difference in dollars and as a ratio. Then a 1-5 rating, what looked wrong, what they looked up elsewhere, what was missing, minutes spent and whether they would use it. "Feedback" in the nav opens the same form without figures. Signed out, the form asks for an email. Entries go to the `feedback` table (`db/migrations/0027_feedback.sql`) with the figures as `app_snapshot`; it is product data, not organization data, and the restricted role cannot read it.

- Admins are the emails in `ADMIN_EMAILS` on the engine (comma-separated). They see `/admin/feedback`: the entries, the summary (count, median rating, and for cost per sq ft, total cost and sale per unit the median and range of their figure / the app's, and of the difference in dollars, with n) and a CSV download. Everyone else gets a 404 there; the nav link shows only to admins.
- Engine routes: `POST /feedback` (rate limited, bucket `feedback`; audit-logged when signed in), and for admins `GET /feedback`, `GET /feedback/summary`, `GET /feedback.csv` (logged as an export) and `DELETE /feedback/{id}`. Deleting an account keeps its feedback without the email.

**Operations.**

- Rate limits: token buckets in Postgres (`rate_bucket`) per signed-in user, or per IP when signed out, for search and the list, exports, sign-in emails and invites. Limits in `data/rules/rate_limits.json`; over the limit the engine answers 429 with `Retry-After`.
- Audit log (`audit_log`): sign-ins, deal changes, saved edits, saved searches, invites, member changes and every export, with who, organization, what and when. The owner sees the last 50 on `/account`; `GET /account/audit` returns more.
- `GET /health`: database, PostGIS, and the latest finished pull per source; nightly sources over 36 hours old (`data/rules/freshness.json`) set `status` to `stale`, and every screen shows a note naming them. 503 when the database is down.
- Error tracking: set `SENTRY_DSN` on the engine and the web app. Engine errors, nightly-job failures and web server errors go to Sentry; empty means they are only logged.
- Data deletion on request: "Delete my account" on `/account`, or `python -m jobs.delete_account person@example.com` (add `--confirm` to delete). Organizations the person owns go with all their data; the Stripe subscription is canceled when billing is set up; other members keep their sign-in. `deletion_log` records each deletion without the email address.
- CI runs `pip-audit` and `npm audit` (job `dependency-scan`).

**Hosting.** Supabase (Postgres with PostGIS) and Fly.io (engine, web app, tile server, nightly job). Copy `.env.production.example` to `.env.production`, fill it in, then `python -m scripts.deploy --dry-run` and `python -m scripts.deploy --first-load`. Steps, costs, restores and rollbacks: `docs/deploy.md`.
