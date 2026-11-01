# Deploying 25x125

Production runs on two services, chosen 2026-11-01 (prices checked that day):

- **Database:** Supabase Pro, region us-east-1 (Virginia), compute size Small (2 GB RAM).
- **Everything else:** Fly.io, region `iad` (Ashburn, Virginia, next to Supabase us-east-1).

One command deploys it: `python -m scripts.deploy`. This page covers the parts, the monthly cost, the first deploy, the nightly job, restores, rollbacks and alerts.

## How the parts fit

```
browser ──https──> x25x125-web (Fly, public)
                     │  /api/*  ──> x25x125-engine.internal:8080  (FastAPI, private)
                     │  /tiles/* ──> x25x125-tiles.internal:3000  (Martin, private)
                     │
x25x125-engine ─┐
x25x125-tiles  ─┼──TLS──> Supabase Postgres + PostGIS (direct connection, port 5432)
nightly Machine ┘
```

| Fly app | What runs | Image | Size | Public |
| --- | --- | --- | --- | --- |
| `x25x125-web` | Next.js standalone server | `deploy/web.Dockerfile` (Node 22.23.4) | shared-cpu-1x, 512 MB | yes (HTTPS) |
| `x25x125-engine` | FastAPI engine, 2 workers; runs migrations on each deploy | `deploy/engine.Dockerfile` (Python 3.12.16) | shared-cpu-1x, 512 MB | no |
| `x25x125-engine`, Machine `nightly` | `python -m jobs.nightly --skip-yearly`, daily, stops after the run | same image as the engine | shared-cpu-1x, 2 GB | no |
| `x25x125-tiles` | Martin v0.18.1 (same as `docker-compose.yml`) with `martin/config.yaml` | `deploy/tiles.Dockerfile` | shared-cpu-1x, 512 MB | no |

- The browser only talks to the web app. The web app reaches the engine and the tile server over Fly's private network (`.internal` names, IPv6). The engine and the tile server have no public address.
- Config per app: `deploy/fly.engine.toml`, `deploy/fly.web.toml`, `deploy/fly.tiles.toml`. Each lists its secrets by name; values live only in Fly.
- The basemap is still OpenFreeMap's public Positron style (no key, attribution on the map). Self-hosting the basemap is a later item. To change it, set `NEXT_PUBLIC_BASEMAP_STYLE` under `[build.args]` in `deploy/fly.web.toml`; it is read at build time.

### Sizes, from local measurements (2026-11-01)

| Measured | Peak memory | Time |
| --- | --- | --- |
| `python -m jobs.score_parcels`, 604,808 lots, 13,607 sale estimates | 1,609 MB | 216 s |
| `python -m jobs.build_parcel_site`, 881,586 parcels (work is in Postgres) | 46 MB | 775 s |
| `python -m jobs.build_lot_use`, 604,843 lots | 46 MB | 76 s |
| Engine container, after parcel, feasibility and health calls | 95 MB per worker | |
| Web container, after map, parcel and feasibility pages | 89 MB | |
| Martin container, serving a lot tile | 3 MB plus its tile cache (256 MB cap) | |

The scorer sets the nightly size: 1.6 GB peak, so the job Machine gets 2 GB. The engine at 512 MB has room for 2 workers (131 MB measured). The web app and Martin fit in 512 MB. The local database is 3.0 GB, which fits in Supabase Pro's 8 GB disk.

## Monthly cost

| Item | Plan | Per month |
| --- | --- | --- |
| Supabase | Pro: 8 GB disk, daily backups kept 7 days | $25 |
| Supabase compute | Small, 2 GB RAM: $15 less the $10 compute credit in Pro | $5 |
| Fly engine | shared-cpu-1x, 512 MB, always on | about $3.69 |
| Fly web | shared-cpu-1x, 512 MB, always on | about $3.50 |
| Fly tiles | shared-cpu-1x, 512 MB, always on | about $3.50 |
| Fly nightly job | 2 GB Machine, billed only while it runs (estimate: 30-60 minutes a day; locally the parcel-site build took 13 minutes and the score 4) | about $0.50-1 |
| Fly extras | stopped-Machine disk, image storage, outbound data | about $1-5 |
| **Fly total** | | **about $12-17** |
| Resend | Free: 3,000 emails a month, 100 a day | $0 |
| Sentry | Free Developer plan | $0 |
| UptimeRobot | Free: 50 monitors, 5-minute checks | $0 |
| Stripe | No monthly fee; 2.9% + 30¢ per card charge (a $129 Pro charge costs $4.04) | per charge |
| Domain | Any registrar | about $10-15 a year |
| **Total before Stripe fees** | | **about $42-47 a month, plus the domain** |

Upgrade later if needed: Supabase point-in-time restore is an add-on; Fly's dedicated IPv4 is $2 a month (the free shared IPv4 is enough for one site).

## First deploy

Do these once. Nothing here needs a terminal except steps 7-9.

1. **Supabase.** Sign up at supabase.com, upgrade the organization to Pro, create a project in **East US (North Virginia), us-east-1**. Save the database password. In Project Settings > Compute and Disk choose **Small**.
   - Don't turn on PostGIS from the dashboard; the first migration creates `postgis` and `pg_trgm`.
   - Copy the connection string from **Connect > Direct connection** (port 5432) and add `?sslmode=require`. This goes in `DATABASE_URL`.
   - The direct host is IPv6 only. Fly has IPv6, so the engine, tile server, migrations and nightly job connect directly. If a deploy log shows `Network is unreachable`, switch `DATABASE_URL` to **Connect > Session pooler** (also port 5432, IPv4 and IPv6, user `postgres.<project ref>`). Never use the transaction pooler (port 6543).
   - Optional: Project Settings > Data API, turn it off. The app never uses it, and migration `0090_hosted_lockdown.sql` already takes the `anon` and `authenticated` roles' access away from every table.
2. **Fly.io.** Sign up at fly.io and add a card. Install flyctl. On Windows, in PowerShell: `iwr https://fly.io/install.ps1 -useb | iex`. Then run `fly auth login`.
3. **Resend.** Sign up at resend.com. Add and verify your sending domain under Domains (it gives DNS records to add at your registrar). Create an API key with sending access. Then `EMAIL_SERVER=smtps://resend:<api key>@smtp.resend.com:465` and `EMAIL_FROM=25x125 <sign-in@yourdomain.com>`.
4. **Sentry.** Sign up at sentry.io, create one project, copy its DSN into `SENTRY_DSN`. The engine, the nightly job and the web app all use it.
5. **Stripe** (can wait; the trial works without it). Use test-mode keys first. Copy the secret key into `STRIPE_SECRET_KEY`. Create the two prices (Pro $129 a month, founding $79 a month) and copy their ids into `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_FOUNDING_MONTHLY`. Add a webhook endpoint at `<APP_URL>/api/billing/webhook` for `checkout.session.completed` and `customer.subscription.*` events, and copy its signing secret into `STRIPE_WEBHOOK_SECRET`.
6. **Secrets file.** Copy `.env.production.example` to `.env.production` (git ignores it) and fill it in. Make `ENGINE_SHARED_SECRET` with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Leave `APP_URL=https://x25x125-web.fly.dev` until a domain is attached.
7. **Dry run.** `python -m scripts.deploy --dry-run` prints every command and checks the secrets file. It changes nothing.
8. **Deploy and load.** `python -m scripts.deploy --first-load`. In order, it:
   1. checks that flyctl is installed and signed in;
   2. checks `.env.production` (required values, port 5432, `sslmode`, `https`);
   3. creates `x25x125-engine`, `x25x125-tiles` and `x25x125-web` if they don't exist (Fly app names are global; if one is taken, change `app` in the matching `deploy/fly.*.toml` and `APPS` in `scripts/deploy.py`);
   4. stages each app's secrets with `fly secrets import --stage`, through stdin, so values never show on screen or in the process list;
   5. deploys the engine; its release command runs `python -m db.migrate` against `DATABASE_URL` on Fly's network before the new version starts, and a failed migration stops the deploy;
   6. deploys the tile server, then the web app (remote builder, one Machine each);
   7. starts the one-off full load, yearly steps included, on a 2 GB Machine that deletes itself when it exits;
   8. creates the `nightly` Machine (daily schedule, 2 GB, stops after each run), or moves it to the new image on later deploys.
9. **Check.** Open `https://x25x125-web.fly.dev/api/health`. Follow the full load with `fly logs --app x25x125-engine`. Until it finishes, screens show the stale-data note and the map is empty.
10. **Domain.** `fly certs add app.yourdomain.com --app x25x125-web`, add the DNS records it prints, then set `APP_URL=https://app.yourdomain.com` in `.env.production` and run `python -m scripts.deploy --only web`. Update the Stripe webhook URL to match.
11. **Uptime.** In UptimeRobot add a Keyword monitor on `<APP_URL>/api/health`, every 5 minutes, alert when the keyword `"status":"ok"` **does not exist**. That one monitor catches a down site, a down engine or database (503) and stale data (`"status":"stale"`).
12. **Deploys from GitHub** (optional). Run `fly tokens create org` (an organization token, because it deploys three apps) and save it as the repository secret `FLY_API_TOKEN` (Settings > Secrets and variables > Actions). After that, every push to main that passes CI deploys the code (`.github/workflows/deploy.yml`, which runs `python -m scripts.deploy --ci`). Without the secret the workflow skips and passes. Secrets and the first load still come from your machine.

Later deploys: `python -m scripts.deploy` (all parts) or `--only engine,web` (some parts). The engine always migrates first.

### Database role on Supabase

Supabase's `postgres` role is not a superuser: it has CREATEROLE, CREATEDB and BYPASSRLS. Migration `0023_account.sql` creates the restricted role `x25_app` and grants it to the login role; the engine runs `set local role x25_app` for organization data, so row-level security applies even though `postgres` bypasses it.

This was checked on 2026-11-01 against a copy of that setup: PostgreSQL 17 with PostGIS 3.5, a superuser standing in for `supabase_admin`, and a non-superuser `postgres` with Supabase's attributes. All migrations applied, and all 116 tests passed against it, including the tests that one organization can't read, change or insert another's rows. On PostgreSQL 16 and later, a CREATEROLE role that creates a role gets admin rights on it but not the right to switch to it; the explicit `grant x25_app to current_user` in 0023 adds that right. No migration change was needed. Migration `0090_hosted_lockdown.sql` removes Supabase's default grants to `anon`, `authenticated` and `service_role`. It does nothing on local Docker or in CI, where those roles don't exist.

## Nightly job

- The `nightly` Machine runs `python -m jobs.nightly --skip-yearly` once a day and stops when it's done. Fly picks the hour; the schedule is daily, not a set time.
- Only one run at a time. `jobs/nightly.py` takes a Postgres lock first; a second run that starts while one is going prints `another nightly run is in progress` and exits.
- Run it now: `fly machine start <id> --app x25x125-engine` (`fly machine list --app x25x125-engine` shows the id of `nightly`).
- Run the yearly reloads (new tax year, or to start over): `python -m scripts.deploy --only nightly --first-load`, or by hand:
  `fly machine run registry.fly.io/x25x125-engine:<label> --app x25x125-engine --vm-memory 2048 --restart no --rm -- python -m jobs.nightly`
  Image labels: `fly releases --app x25x125-engine --image`.
- One step by hand, e.g. the score: `fly ssh console --app x25x125-engine -C "python -m jobs.score_parcels"` (runs on the engine Machine, which has 512 MB; use a 2 GB `fly machine run` like the one above for the score or the full load).
- Logs: `fly logs --app x25x125-engine`. A failed step goes to Sentry with the step name; the report at the end of each run lists every source and row count.

## Restore from a Supabase backup

Supabase Pro takes a backup every day and keeps 7.

1. Supabase dashboard > Database > Backups. Pick the day.
2. Either **restore to a new project** (safer: the live database keeps running; point `DATABASE_URL` at the new project and redeploy), or **restore in place** (the project is offline for the restore and loses everything after that backup).
3. After an in-place restore, run the nightly job (above) so the sources catch up. Deals, accounts and saved edits made after the backup are gone; Stripe still has the subscriptions, and its webhook events will set plans again as they arrive.
4. If you moved to a new project: put its connection string in `.env.production`, then `python -m scripts.deploy`. Migrations that the backup already has are skipped.

Test a restore before launch (TASKS.md SaaS setup asks for one): restore yesterday's backup to a new project, point a local engine at it (`DATABASE_URL=... python -m uvicorn engine.app:app`), check `/health` and a parcel page, then delete the project.

## Roll back

- List versions: `fly releases --app x25x125-web --image` (same for `x25x125-engine`, `x25x125-tiles`).
- Go back to one: `fly deploy --app x25x125-web --config deploy/fly.web.toml --image registry.fly.io/x25x125-web:<label>`. No build; it takes about a minute.
- The engine: same command with `deploy/fly.engine.toml`. Its release command runs again but finds nothing new. Migrations only go forward: rolling the engine back past a migration works only if the old code still runs on the new tables. If not, fix forward or restore the database (above).
- The nightly Machine keeps the image it was given. After an engine rollback: `fly machine update <nightly id> --app x25x125-engine --image registry.fly.io/x25x125-engine:<label>`.

## Alerts and the stale-data check

- `GET /api/health` on the web app returns the engine's `/health`: database, PostGIS, and the latest finished pull per source. `status` is `ok`, `stale` when a nightly source is over 36 hours old (`data/rules/freshness.json`), or `degraded` with HTTP 503 when the engine or database is down. Every screen shows a note naming stale sources.
- `GET /api/health?scope=web` answers 200 while the web app runs. Fly uses it for the web app's own check, so an engine outage doesn't take the site offline; the screens say what's wrong instead.
- Fly checks the engine's `/health` and Martin's `/health` every 30 seconds and holds a rolling deploy until they pass.
- UptimeRobot (step 11) emails you when `"status":"ok"` is missing, which means down, degraded or stale. A nightly run that fails outright shows up here within 36 hours, and in Sentry at once.

## Building the images locally

From the repo root (Docker Desktop on Windows works the same):

```
docker build -f deploy/engine.Dockerfile -t x25x125-engine .
docker build -f deploy/web.Dockerfile -t x25x125-web .
docker build -f deploy/tiles.Dockerfile -t x25x125-tiles .
```

Run the engine against the local database: `docker run --rm -p 8091:8080 -e HOST=0.0.0.0 -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/x25x125 -e ENGINE_SHARED_SECRET=<any 32+ characters> x25x125-engine`, then open http://localhost:8091/health. `HOST=0.0.0.0` is for machines where Docker has no IPv6; on Fly it is `::`. The web image takes `-e HOSTNAME=0.0.0.0` for the same reason, plus `ENGINE_URL`, `TILES_URL` and `ENGINE_SHARED_SECRET`. If Docker Hub refuses a pull (rate limit), add `--build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.12.16-slim-bookworm` or `--build-arg NODE_IMAGE=mirror.gcr.io/library/node:22.23.4-bookworm-slim`.
