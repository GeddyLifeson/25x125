# Tasks

Nine steps from `docs/v1-spec.md` (Build plan), revised 2026-10-29. Finish and test each one before starting the next. Calibration results so far are in `docs/calibration-2026-10-29.md`.

## Step 0: Setup and calibration inputs

- [ ] Repo layout: `jobs/` (Python loaders and nightly jobs), `engine/` (Python rules and feasibility, FastAPI), `web/` (Next.js + MapLibre), `db/` (migrations), `data/`, `docs/`, `tests/`.
- [ ] `docker-compose.yml` with PostgreSQL 16 + PostGIS. One command to start it on Windows and Mac.
- [ ] `.env.example` filled in; settings loaded from env.
- [x] Query every dataset in `data/sources/datasets.csv` once (done 2026-10-29; all answer).
- [ ] Source the layers that are not on the data portals: transit-served areas, fire limits, 606/Pilsen surcharge districts, ADU areas, Opportunity Zone tracts, a current parcel polygon year.
- [ ] Partner contractor session: actual $/sq ft and gross area on recent 2-6 flats, entered as cost records.
- [ ] Run 10 real parcels through the spec math by hand; note every question answered outside the tool.

## Step 1: Data foundation

- [ ] Migrations for: `parcel`, `parcel_signal`, `sale`, `permit`, `building_char` (residential and condo), `zoning_district_area`, `overlay` (TIF, Enterprise Zone, OZ, historic, landmark, fire limits, 606/Pilsen, ADU areas), `transit_station`, `boundary`, `rule` tables, `source_pull` (dataset, pulled_at, row count).
- [ ] Every value table has `source` and `pulled_at` columns (or a link to `source_pull`).
- [ ] Shared Socrata client: paging, app token, retries, incremental pulls by a date column. Note: Assessor year values after 2023 end in `.0` (`year='2026.0'`).
- [ ] Loaders: parcel universe (pabr-t5kh, which already carries ward, community area, tract, Assessor neighborhood, TIF), addresses (3723-97qp), sales (wvhk-k5uv), assessed values (uzyt-m557), residential characteristics (x54s-btds), condo characteristics (3r7i-mrz4), parcel polygons, zoning (dj47-wfun).
- [ ] Layer loaders: TIF (eejr-xtfb), Enterprise Zones (64xf-pyvh), historic (2u8t-236p, uct4-hrvh), CTA (8pix-ypme), Metra, boundaries (igwz-8jzy, p293-wvbd, 7qjk-677h, pcdw-pxtg), plus the step 0 layers.
- [ ] Nightly jobs: permits (ydr8-5enu), violations (22u3-xenr), 311 vacant building/lot (v6vf-nfxy), scofflaw (rz4d-qp2m), city land (aksk-kvfp), demolition notices (qhb4-qx8k).
- [ ] Spatial joins: zoning district, overlays, distance to nearest CTA/Metra station, lot area and frontage from polygons.
- [ ] Condo handling: group unit PINs under the building's base PIN.
- [ ] Test: all 37 test parcels resolve to a parcel with zoning, lot area and frontage.
- [ ] Load report: row counts per table, pull dates, failed rows.

## Step 2: Rules engine

- [ ] Seed rule tables from `data/rules/zoning_districts.csv` and `zoning_steps.json`.
- [ ] Load the full B/C height-by-frontage table from the code.
- [ ] Implement the 10 calculation steps, with user-picked rezoning targets and the RS-3 block-face test.
- [ ] One rule schema: rule, location reference, effective from/to, citation, verified-on (Dutch and UK practice; docs/international-practices.md).
- [ ] Output per parcel and path: units, floor area, height, parking, flags, rule citation.
- [ ] Hand-checked set: about 20 parcels Marlon knows (B/C-3, mixed use, RS-3, a 606 lot, a historic building).
- [ ] Test: units by right on each test lot are at least the units built, or the result names the approval path used; hand-checked set matches.

## Step 3: Comps and cost calibration

- [ ] Port `scripts/research/2026-10-29/` into jobs: comp pool from year built (211 + condo), first arm's-length sale, weighted median per unit, 25th-75th range, time adjustment.
- [ ] Cost index job within unit-count groups, monthly (logic in `idx.py`); blend thin areas with neighbors.
- [ ] Recency weights by quarter (1.00, 0.75, 0.56, 0.42) and side-of-city blending for thin areas.
- [ ] Land value map: vacant-land and teardown sales, per sq ft of lot and per buildable sq ft, by Assessor neighborhood, with counts.
- [ ] Build-spec presets refit with the contractor's numbers.
- [ ] Rent estimate: ACS B25031/B25064 + 25% premium, ZORI growth, HUD SAFMR floor, csik-bsws cross-check.
- [ ] Test: sale estimate within 15% for at least 70% of test parcels (65% on 2026-10-29). Report the hit rate and median error.
- [ ] Test: at actual sale and $60,000 land, at least 60% of test buildings show profit of $0 or more (57% on 2026-10-29).
- [ ] Test: standard 3-flat total cost within -20%/+30% of $308,000-365,000 per unit.

## Step 4: Feasibility engine and score

- [ ] All formulas from the spec for sell and hold, with the exact financing formula and margins that exclude land.
- [ ] Incentives v1 from `data/rules/incentives_v1.csv` (OZ $0 for sell; bonus depreciation as deferral).
- [ ] Pattern library scenarios from `data/rules/building_patterns.json`, checked against each zoning path.
- [ ] Residual land value, profit as percent of value and cost, existing-use check; cost at P50 and P80.
- [ ] Eligibility questions from `data/rules/incentive_questions.json` drive incentive toggles.
- [ ] Fast-path flag per parcel (definition in `feasibility_defaults.json`).
- [ ] Every output number carries source, date and comp count.
- [ ] Nightly by-right run for every parcel; development score with points breakdown.
- [ ] Unit tests on every formula.

## Step 5: Parcel report (first real use)

- [ ] Address and PIN search; parcel page matching `mockups/Parcel.dc.html`.
- [ ] Feasibility screen matching `mockups/Feasibility.dc.html`, every assumption editable.
- [ ] One-page PDF.
- [ ] Marlon and the contractor use it on live deals for 2 weeks; contractor checks five runs.

## Step 6: Map search and deals

- [ ] Parcel vector tiles; map and list matching `mockups/Main.dc.html`; filters and sorts; under 2 seconds.
- [ ] Fast-path filter and land value map layer.
- [ ] Deals screen matching `mockups/Deals.dc.html`: pipeline counts, deal table, outreach log, CSV export.
- [ ] Email sign-in.

## Step 7: Private test

- [ ] Staging host; family company and 5-10 brokers on real parcels; report-an-error button.
- [ ] Fix list closed; at least 3 testers say they would pay.

## Step 8: Launch

- [ ] Billing, terms of use (lawyer reviewed), support inbox.
- [ ] Landing page, free address check, community-area pages.
- [ ] First paying users.

## Version 1.1 (after launch)

- [ ] Saved searches with alerts; CSV import; teams and shared deals; comps drawer; sensitivity sliders; lender Excel export.

## Later, from the international review

- [ ] Permit-ready plan sets for the pattern library with partner architects (Phase 2).
- [ ] Entitlement tracker as gateways with one consolidated comment list per round (Phase 2a).
- [ ] Refit cost margins from actual job costs, P50/P80 (Phase 4).
- [ ] Policy mode: rerun all parcels under a proposed ordinance (after V1.1).

## Business setup (Marlon, alongside)

- [ ] LLC to own the product.
- [ ] Trademark and domain search for 25x125.
- [ ] Hosting account; free Socrata app tokens; free Census API key.
- [ ] Errors and omissions insurance quote before launch.
- [ ] MRED feed (steps in `docs/v1-spec.md`, MRED section).

## Open items to verify (from the plan)

- [ ] 2026 Chicago building code text (window percentages, corridor widths, travel distances).
- [ ] Building permit fee tables (residential construction factor is a $0.50/sf placeholder).
- [ ] Opportunity Zone 2027 certified tract list.
- [ ] Enterprise Zone residential eligibility.
- [ ] Film credit qualified expenditures (Interim, later).
