# 25x125

Development pipeline software for small, vertically integrated real estate companies in Illinois (brokerage through construction). Chicago first. Version 1 answers four questions for any Chicago parcel: what can be built, what it costs (with a dollar margin), which incentives apply, and whether it makes money.

Owner: Marlon (imarlonlee@gmail.com, GitHub GeddyLifeson).

## Read these first

- `docs/calibration-2026-10-29.md` records the cost and comp calibration; read it before touching defaults.
- `docs/v1-spec.md` is the build spec. If code and spec disagree, the spec wins until Marlon changes it.
- `TASKS.md` is the milestone checklist. Work one milestone at a time and tick items as they finish.
- `docs/plan.md` is the full business plan (all 8 pipeline stages, brands, incentives, legal). Use it for context, not as a build list.
- `docs/module-outlines.md` covers modules 1-11. Only modules 1 and 2 (site finder, feasibility) are in version 1.
- `mockups/` holds the four screen mockups (search, parcel, feasibility, deals) with Humboldt Park sample data. They need the canvas runtime to render; the live versions are at https://claude.ai/artifact/6DDPyW9FBpVud4X3ANfiU4. Read the HTML for layout, labels and copy.

The live, editable versions of the three docs are Claude Docs artifacts:
- Plan: https://claude.ai/artifact/P5vJ5Cgu14bcMuijpGP1y5
- Module outlines: https://claude.ai/artifact/Mqo3gVuyK3ofaVCDTmqCMF
- V1 spec: https://claude.ai/artifact/1Mrw49gFoYWLQ8cYo6Vtuv

The markdown copies in `docs/` were exported on 2026-10-28. If Marlon updates a live doc, re-export it rather than editing the copy by hand.

## Stack

- PostgreSQL with PostGIS. Run it locally in Docker.
- Python 3.12 for loaders and nightly jobs (`jobs/`).
- One Python engine for rules and feasibility (`engine/`), served by FastAPI. The nightly scorer and the live feasibility screen both call it, so results never drift.
- Next.js (TypeScript) web app with MapLibre GL (`web/`); parcels served as vector tiles (Martin or nightly PMTiles).
- Managed hosting later. GitHub for the repo.
- Marlon's machine is Windows. Keep scripts cross-platform: no bash-only steps in the main path, use `python` not `python3` in docs, and use Docker Compose for the database.

## Rules for the code

1. **Rules live in data, not code.** Zoning numbers, code thresholds, incentive programs, cost defaults and score weights sit in `data/rules/` (and later in database tables seeded from them). Each rule carries a source URL and a verified-on date. A rule change should be a data edit.
2. **Every number shows its source and date.** Each stored value keeps where it came from and when it was pulled. Any number on screen can show its source, its date and, for comps, how many comps it rests on.
3. **Costs are dollars with dollar margins.** Show `$1,375,000 (-$275,000 / +$413,000)`, never `±20%`. The margin depends on the estimate stage (see `data/rules/feasibility_defaults.json`). Widen it when data is thin and say so on screen.
4. **Price by neighborhood.** Never use a citywide number when a neighborhood number exists. Fall back from Assessor neighborhood, to community area, to neighboring community areas, and widen the margin at each step.
5. **Show the numbers, don't recommend.** The app presents the math. It doesn't tell users what to build or call something a good investment.
6. **Incentives show at maximum value with toggles.** Users switch off what doesn't apply to them. Label results as estimates, not tax, legal, zoning or appraisal advice.
7. **Everything is overridable.** Every default can be edited per deal, and the user's own job costs replace defaults over time.
8. **Import and export at every step.** CSV in and out from the start; PDF one-pager in version 1.
9. **Illinois only.** Chicago first, then Cook suburbs, then Lake, then McHenry, then the rest. Build geography as a data dimension (municipality, county) from day one, but load only Chicago now.
10. **Never query the portals live from the app.** Nightly jobs copy data into Postgres; screens read from Postgres.

## Data

- Free public data only for version 1. No RSMeans, no paid feeds yet.
- Chicago Data Portal and Cook County data catalog are Socrata APIs: `https://data.cityofchicago.org/resource/<id>.json` and `https://datacatalog.cookcountyil.gov/resource/<id>.json`, queried with SoQL (`$select`, `$where`, `$limit`, `$offset`). Both worked without a key on 2026-10-28. Use a free app token in production (`SOCRATA_APP_TOKEN`).
- Dataset IDs are in `data/sources/datasets.csv`.
- Census ACS needs a free key (`CENSUS_API_KEY`).
- Zillow ZORI: use growth rates internally only. Never display Zillow figures in the product without written permission.
- Reference data from research on 2026-10-28 is in `data/reference/`:
  - `test_parcels.csv`: 35 real buildings (permit matched to later sale; 2 removed on 2026-10-29, see `test_parcels_removed.csv`). This is the acceptance test set.
  - `new_construction_sales.csv`: 2,450 first sales of 2-6 unit buildings and condo units built 2014 or later (pulled 2026-10-29); the comp pool.
  - `cost_index_by_area_v2.csv`: cost index computed within unit-count groups; replaces the v1 file.
  - `cost_index_by_area.csv`: neighborhood cost index from 836 permits; city median $166,667 per unit.
  - `permits_2to6_clean_city.json`: the cleaned permit rows behind the index.
- `scripts/research/` holds the throwaway scripts that built those files. Port the logic into proper jobs; don't import them.

## AI tooling for the build

- Marlon wants Claude API credits and a model router used to speed up building V1 (2026-11-01). No local models.
- Keys: `ANTHROPIC_API_KEY` and `OPENROUTER_API_KEY` (the router; change the name if Marlon uses a different one). Locally they go in `.env` (placeholders in `.env.example`); in cloud sessions they are environment secrets in project settings. Never commit a key or paste one in chat.
- Use the cheapest model that does the job: the Batch API and the small model for bulk extraction (scanned ordinances, permit text), larger models only where accuracy needs it.
- Before any run likely to cost more than about $5, post a rough estimate (calls x tokens x price) and wait for Marlon's go-ahead. Log each run's model, row count and cost in `docs/ai-runs.md`.
- AI output is data to check, not a source: store which model produced each value and spot-check a sample against the original before it reaches a screen. Every number still shows its source and date (rule 2).
- MLS data never goes to any model (see MLS rules).

## MLS (MRED) rules

MRED data isn't in version 1. Marlon is handling the license separately. Don't build anything that uses MLS data until he says the feed is approved. When it comes in (via MLS Grid, `api.mlsgrid.com/v2`):

- No AI training on MLS data, no stored embeddings or retrieval indexes past one session, no caching beyond a single query.
- Attribution on every MLS figure: "Listings courtesy of MRED as distributed by MLS GRID".
- Honor seller opt-outs. Delete records MLS Grid marks as no longer viewable.
- Never filter or rank listings by broker or brokerage.
- Broker-only fields never reach customers.
- Sold comps only to users with a registered broker-client relationship.

## Legal guardrails that touch code

- Investor network (later phase): no success fees, no handling of funds, no ranking of deals as good investments.
- Wholesale tools (separate brand, later): warn at 2+ contract assignments in 12 months (Illinois requires a license).
- Any outreach feature: TCPA for calls and texts, CAN-SPAM for email.
- The layout planner (later) produces a starting design only. An Illinois-licensed architect must stamp drawings for 3+ units.

## Brands

25x125 is the development pipeline. Interim (short-term space for film productions and pop-up stores) and the wholesale tools are separate brands with their own names, sites and pricing on a shared account system. Keep them apart in code (separate app routes or apps, shared core packages). None of them are in version 1.

## Writing

Anything user-facing (UI copy, README, docs, commit messages) is plain English. No filler, no hype, no "not X, it's Y" phrasing. Short sentences. Numbers over adjectives.

## How to work with Marlon

- He wants detail and the numbers shown.
- End each reply with a short list of open questions for him.
- Anything written on his behalf to other people (emails, messages) must not mention AI and is signed as him.
- Before a milestone is marked done, run its tests and show the results.
