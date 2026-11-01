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

Checks: `npm run typecheck`, `npm run build`, and with the engine, the tile server and the web app running, `node scripts/smoke.cjs http://localhost:3000` (needs the `playwright` package and Chromium; screenshots go to `web/screenshots/`, which git ignores). The smoke run deletes the deals it creates.

## Map, list and deals

- **Map and list** (`/map`): the scored lots from the nightly run, filtered by community area, zoning prefix, minimum score, minimum units by right, a signal, vacant land, city lots for sale and the fast path; sorted by score, return on cost (25th percentile), extra units by right or lot size. Each lot shows its points by part, its signals and penalties, and why it has no profit points when it has none. Filters stay in the address bar. "Export list as CSV" downloads up to 5,000 rows with the same filters (`GET /lots?format=csv`).
- The map draws lots coloured by score. From zoom 14 in it shows every lot's shape; farther out it shows points for lots scoring 20 or more (zoom 13), 40 or more (zoom 11-12) or 50 or more (zoom 10), so tiles stay small. Click a lot for its points, the by-right numbers and links to the parcel page and feasibility screen.
- Layers: fast-path lots, land value per lot sq ft (by Assessor neighborhood or community area, paler where fewer than 5 sales) and public lots for sale (City of Chicago ChiBlockBuilder and city land, Cook County Land Bank) with asking price, deadline and the apply link.
- Tiles come from Martin (`docker compose` service `tiles`, http://localhost:3100/catalog), which runs the PostGIS functions in `db/migrations/0022_map_tiles.sql`. The web app passes them through at `/tiles/...`; set `TILES_URL` if Martin runs elsewhere. The basemap is OpenFreeMap's Positron style (no key; attribution shows on the map). Set `NEXT_PUBLIC_BASEMAP_STYLE` to another style URL, or to `none` for a plain background, before `npm run build`.
- **Deals** (`/deals`): pipeline counts by stage (lead, contacted, feasibility, under contract, passed), the deal table, and the owner outreach log with the TCPA and CAN-SPAM note. Save a deal from the map panel, the parcel page or the feasibility screen; from feasibility the deal keeps the edits on screen, and the engine re-runs the scenario and stores its numbers with the date. "Feasibility" on a deal reopens it with those edits. CSV out: deals and the outreach log; CSV in: deals (a `pin` column, plus any of stage, next_step, next_step_on, notes, address, overrides; a row with an existing `id` updates that deal).
- Engine endpoints: `GET/POST /deals`, `GET/PATCH/DELETE /deals/{id}`, `POST /deals/{id}/rerun`, `GET/POST /deals/{id}/events`, `DELETE /deals/{id}/events/{event_id}`, `GET /deals/pipeline`, `GET /deals/events`, `POST /deals/import` (CSV body), `GET /lots/{pin10}`, `GET /community-areas`, `GET /community-areas/{num}/snapshot`.
- Sign-in and organizations come later; `deal.org_id` is stored but not enforced yet.
