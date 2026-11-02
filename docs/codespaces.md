# 25x125 in GitHub Codespaces

Open the whole app in your browser from the GitHub repo. No accounts beyond your GitHub login, no hosting, no installer.

**Open it:** https://codespaces.new/GeddyLifeson/25x125?quickstart=1

The link reuses your codespace if you already have one, so your deals and edits are there next time.

## What happens

1. GitHub builds a small Linux machine for you (2 cores, 8 GB memory). The first time takes about 5 minutes: it installs the packages and builds the app.
2. The database is empty on the first start, so it downloads the data snapshot (every Chicago parcel, sales, permits, zoning, scores) from the repo's Releases page and restores it. About 5 to 15 minutes.
3. The engine and the app start. A new browser tab opens on the app. The editor's terminal shows each step and then the app's address.
4. Later starts take about 1 minute. If the data is more than 20 hours old, it pulls what is new from the portals in the background (5 to 20 minutes) while you use the app.

There is no sign-in. You are the owner, on Pro, with nothing to pay, the same as the Windows program. The app's address works only for your GitHub login.

If the browser blocks the new tab: in the editor, open the **Ports** tab and click the globe next to port 3000 ("25x125").

## Cost

Codespaces is free up to a monthly allowance on a personal GitHub Free account: 120 core-hours (60 hours on this 2-core machine) and 15 GB-month of storage. This codespace uses about 8 GB of disk.

- With no payment method on your GitHub account, GitHub stops the codespace when the allowance runs out. It never charges.
- With a payment method on file, use past the allowance costs $0.18 an hour and $0.07 per GB-month. Check or set a $0 budget at https://github.com/settings/billing.
- The codespace stops by itself after 30 minutes with no activity in the editor, which saves hours. If it stops while you use the app, raise the idle timeout at https://github.com/settings/codespaces (60 minutes is enough).
- GitHub deletes a codespace that hasn't been opened for 30 days. Your deals go with it. Export them as CSV from the deals page first, or open the codespace once a month.

## Where the data comes from

The workflow "Data snapshot" (`.github/workflows/data-snapshot.yml`) runs the full load from the public portals every Monday on a free GitHub runner and publishes the database dump on the release `data-snapshot`. It holds public data only. Run it by hand from the repo's **Actions** tab, "Data snapshot", **Run workflow**.

If there is no snapshot, the first start runs the full load from the portals instead (1 to 2 hours). Keep the editor tab open until the terminal says it finished.

## Commands

In the codespace's terminal:

| Command | What it does |
| --- | --- |
| `python scripts/codespace.py status` | What is running and the app's address |
| `python scripts/codespace.py update` | Pull what is new from the portals now (5-20 minutes) |
| `python scripts/codespace.py full-reload` | Reload everything from the portals (1-2 hours) |
| `python scripts/codespace.py restart` | Stop and start the engine and the app |

Logs are in `.codespace/` (`run.log`, `engine.log`, `web.log`).

On each start the codespace pulls new code from `main` and rebuilds the app when you have no local edits there.

## How it's built

- `.devcontainer/` defines the machine: a Postgres 16 + PostGIS container and a workspace with Python 3.12, Node.js 22 and the Postgres client tools.
- `scripts/codespace.py` restores the snapshot (only into an empty database; it never replaces one with parcels or saved deals), applies migrations, runs the engine with `LOCAL_MODE=1` on 127.0.0.1:8000 and the built Next.js app on port 3000, restarts either if it stops, and runs the daily update.
- Map tiles come from the engine (`/tiles/...`), as in the desktop program, so there is no Martin.
- The forwarded address differs from the Host header the app sees, so the launcher sets `APP_ORIGINS` for the same-origin check in `web/proxy.ts`.

Results are estimates, not tax, legal, zoning or appraisal advice.
