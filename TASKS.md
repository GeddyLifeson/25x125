# Tasks

Nine steps from `docs/v1-spec.md` (Build plan), revised 2026-10-29. Finish and test each one before starting the next. Calibration results so far are in `docs/calibration-2026-10-29.md`. Full schedule to paid launch (23 working weeks from 2026-11-02, launch week of 2027-04-19): https://claude.ai/artifact/SxJ23K1yPFYBrRnMY4h4Jj

## Step 0: Setup and calibration inputs

- [x] Repo layout: `jobs/` (Python loaders and nightly jobs), `engine/` (Python rules and feasibility, FastAPI), `web/` (Next.js + MapLibre), `db/` (migrations), `data/`, `docs/`, `tests/`.
- [x] `docker-compose.yml` with PostgreSQL 16 + PostGIS. One command to start it on Windows and Mac.
- [x] `.env.example` filled in; settings loaded from env (`core/settings.py`).
- [x] Query every dataset in `data/sources/datasets.csv` once (done 2026-10-29; all answer).
- [x] Source the layers that are not on the data portals: transit-served areas, fire limits, 606/Pilsen surcharge districts, the ADU eligibility map, Opportunity Zone tracts, a current parcel polygon year. Done 2026-10-30: all but the fire limits are on the city's own GIS server (gisapps.chicago.gov ExternalApps/Zoning and operational map services), Opportunity Zones from the U.S. DOT copy of the Treasury list, fire limits traced from Municipal Code 13-116-010. The ADU request email in `docs/launch/city-request-adu-map.md` is no longer needed.
- [x] Construction $/sq ft from published sources (docs/construction-costs-2026-10-29.md); contractor data replaces it when available.
- [x] Run 10 real parcels through the spec math; questions in `docs/hand-run-10-parcels-2026-10-29.md` (Marlon to add his).

## Step 1: Data foundation

- [x] Migrations for: `parcel`, `parcel_signal`, `sale`, `permit`, `building_char` (residential and condo), `zoning_district_area`, `overlay` (TIF, Enterprise Zone, OZ, historic, landmark, fire limits, 606/Pilsen, ADU areas), `transit_station`, `boundary`, `rule` tables, `source_pull` (dataset, pulled_at, row count). Done 2026-10-30 (migrations 0001-0010) except the `rule` tables, which move to step 2.
- [x] Every value table has `source` and `pulled_at` columns (or a link to `source_pull`). Done for `parcel` and `sale`; keep it for each new table.
- [x] Shared Socrata client: paging, app token, retries, incremental pulls by a date column (`core/socrata.py`). Note: Assessor year values after 2023 end in `.0` (`year='2026.0'`).
- [x] Loaders (all in `jobs/`, run together by `python -m jobs.nightly`): parcel universe (pabr-t5kh, which already carries ward, community area, tract, Assessor neighborhood, TIF), addresses (3723-97qp), sales (wvhk-k5uv), assessed values (uzyt-m557), residential characteristics (x54s-btds), condo characteristics (3r7i-mrz4), parcel polygons, zoning (dj47-wfun).
- [x] Layer loaders: TIF (eejr-xtfb), Enterprise Zones (64xf-pyvh), historic (2u8t-236p, uct4-hrvh), CTA (8pix-ypme), Metra, boundaries (igwz-8jzy, p293-wvbd, 7qjk-677h, pcdw-pxtg), plus the step 0 layers. Done 2026-10-30. Boundaries (`python -m jobs.load_boundaries`): 77 community areas, 50 wards, 789 tracts, 191 Assessor neighborhoods in the Chicago townships; `community_area_neighbor` lists the community areas that share an edge, for the pricing fallback. 1,533 parcels carry Assessor placeholder codes (x999) with no neighborhood shape.
- [x] Nightly jobs: permits (ydr8-5enu), violations (22u3-xenr), 311 vacant building/lot (v6vf-nfxy), scofflaw (rz4d-qp2m), city land (aksk-kvfp), demolition notices (qhb4-qx8k). Done 2026-10-29 (`python -m jobs.load_signals`, part of the nightly run): 299,661 violations since 2021, 33,878 vacant building and 30,614 vacant lot 311 requests since 2021, 42 scofflaw buildings, 20,781 city land records, 4,328 demolition notices since 2021. 98.7-100% tie to a lot (point on the lot, else nearest lot within 15 m). `parcel_site` now carries open violations (120,658 PINs), 311 vacant building (14,091) and lot (21,757) counts for the last 3 years, scofflaw, city land status (13,374 owned or leased) and latest demolition notice (6,351).
- [x] Spatial joins: zoning district, overlays, distance to nearest CTA/Metra station, lot area and frontage from polygons. Done: zoning, lot area, frontage and depth (`parcel_site`); 15,466 parcels are split-zoned (under 90% in one district). Done: historic survey Red/Orange, landmarks, TIF, feet to nearest CTA rail and Metra station (Metra from its GTFS feed; the portal's nqm8-q2ym now returns 403). Done 2026-10-30 (`python -m jobs.load_city_layers`, rules in `data/rules/special_districts.json`): transit-served from the city's TSL map (757,600 PINs; 358,497 by CTA station, 117,731 by Metra, 281,372 by bus corridor), ADU zone (447,945), 606 district (31,169), Pilsen district (4,349), ARO area, Enterprise Zone (194,100), 2018 Opportunity Zone (112,783), fire limits (82,803), pedestrian street frontage (30,142).
- [x] Condo handling: unit PINs share the building's first 10 digits (`pin10`) and `tieback_key_pin` in `condo_char`.
- [x] Test: all 35 test parcels resolve to a parcel with zoning, lot area and frontage (`python -m jobs.check_test_parcels`, 35 of 35 on 2026-10-29, on the county's 2025 parcel polygons; 6150 and 6152 S Champlain now show 3,059 and 3,060 sq ft).
- [x] Newer parcel polygons: Cook County GIS Parcel 2025 layer (613,510 Chicago lots; every 2026 PIN now has a polygon).
- [x] Checked Assessor Parcel Proximity (ydue-e5u3): no transit fields; distances computed from station points instead.
- [x] Enterprise Zones (64xf-pyvh) returns empty geometry on 2026-10-29; find another source. Done: city GIS operational/MapServer/73, 6 zones.
- [x] Load report: row counts per table, latest pull per source, failed pulls in the last 7 days (`python -m jobs.report`).
- [x] Depth channels from the channel audit (https://claude.ai/artifact/KDGRZ9tKEgCwC2cUYq5Ydg): Assessor parcel proximity (ydue-e5u3), Assessor permits (6yjf-dfxs), tax-exempt parcels (vgzx-68gb), building footprints (syp8-uezg) in `jobs/load_parcel_extras.py`; environmental holds (6gqn-e2ij), hearing fines (6br9-quuz), vacant-building fines (kc9i-wq85), foreclosed rentals (yhcw-iu53) as signal kinds. Live load on 2026-10-30: 174,846 Chicago Assessor permits; 49,650 exempt PINs; 1,417,544 proximity rows (2025, county-wide; trimmed to Chicago lots when parcels are loaded); 820,596 footprints (stories on 427,998, units on 409,313; the city last updated this file in 2015, so newer buildings are missing); 1,850 environmental holds; 85,745 hearing cases since 2021; 4,482 vacant-building cases (5,012 rows, some share a violation number); 585 foreclosed rentals.
- [x] Add the depth channels to `parcel_site` (migration 0051, `jobs/build_parcel_site.py`): foreclosures within half a mile, feet to nearest new construction, stories and units from footprints, hearing fines in the last 3 years, vacant-building fines owed, latest environmental hold, foreclosed-rental date, exempt owner. Tested in `tests/test_parcel_extras.py`; counts on the full city appear after the next full nightly run.

## Step 2: Rules engine

- [x] Seed rule tables from `data/rules/zoning_districts.csv` and `zoning_steps.json`. Done 2026-10-30 (`python -m jobs.seed_rules`, part of the nightly run): 60 rules. Districts now cover RS-1 to RM-6.5 and B/C -1 to -5, checked against the code text; D, M, PMD, PD, POS and T districts return 'not covered'.
- [x] Load the full B/C height-by-frontage table from the code. Done: `data/rules/zoning_heights.csv` (17-3-0408-A, with and without ground-floor commercial; RM-4.5/RM-5/RM-5.5 frontage steps from 17-2-0311-A).
- [x] Implement the 10 calculation steps, with user-picked rezoning targets and the RS-3 block-face test. Done: `engine/zoning.py`; block faces from `jobs/build_lot_use.py` (street, side and hundred block); rezoning target via `?target=`. The transit-served density bonus applies to B3-3 and C3-3 only, as the code says (the spec says all -3 districts).
- [x] One rule schema: rule, location reference, effective from/to, citation, verified-on (Dutch and UK practice; docs/international-practices.md). Done: `rule` table (migration 0011).
- [x] Output per parcel and path: units, floor area, height, parking, flags, rule citation. Done: `GET /parcels/{pin}/zoning`.
- [ ] Hand-checked set: about 20 parcels Marlon knows (B/C-3, mixed use, RS-3, a 606 lot, a historic building). 19 parcels from recent permits are in `data/reference/hand_check_parcels.csv` with an expected result each; Marlon to add the ones he knows.
- [x] Test: units by right on each test lot are at least the units built, or the result names the approval path used; hand-checked set matches. Done 2026-10-30 (`python -m jobs.check_zoning`): 35 of 35 test buildings fit a path (28 by right, 1 by the RS-3 block-face rule, 4 by the 10% lot-area adjustment, 2 with an ADU unit); 19 of 19 hand-checked parcels as expected.

## Methods review (2026-10-30)

- [x] Weigh every V1 method against papers, standards and practice: `docs/research/reports/Methods review for V1 build.md` (66 decisions), notes in `docs/research/research_notes/`. What was applied and what waits on Marlon: `docs/research/decisions-2026-10-30.md`.
- [x] Steps 1-2 redone from the review: parking by district (17-10-0207), Metra-only lots at 50% by right, ADU approvals in RS districts, administrative-adjustment reading labeled as disputed, zoning by largest share of the lot with the second district kept, signals matched by address first with the method stored, units summed over all building cards, condo parking PINs dropped, block faces from street centerline segments (pr57-gg9e).
- [ ] Marlon: decide the spec proposals listed in the decisions file.

## Step 3: Comps and cost calibration

- [x] Port `scripts/research/2026-10-29/` into jobs. Done 2026-10-30: `python -m jobs.build_comps` (2,234 kept comps, dropped sales tagged with the reason), `python -m jobs.load_hpi` (FHFA tract, ZIP and metro), `engine/comps.py`, `GET /parcels/{pin}/sale-value`. Method chosen on an out-of-time holdout: metro index, condo size elasticity 0.50, 3-year window, ring fallback, 0.70 factor on condo comps for whole-building estimates; calibrated 80% range in `data/rules/sale_band.json`. Details in `docs/research/step3-comps-2026-10-30.md`.
- [x] Cost index job within unit-count groups, monthly (logic in `idx.py`); blend thin areas with neighbors. Done 2026-10-30: `python -m jobs.build_cost_index` (part of the nightly run): 861 permits from the last 5 years, recency weights by quarter, 57 of 77 community areas under 10 permits blended with their neighbors. Lincoln Park 1.89, Lake View 2.06, Humboldt Park 0.78.
- [ ] Permit wait by review path from `processing_time` (self-cert 50 days, standard 85, medians); FHFA tract HPI time adjustment; PPI escalation of presets (round 2 of docs/international-practices.md). Done 2026-10-30: permit waits (`permit_wait`: self-cert median 48.5 days, standard 83) and the FHFA index (`python -m jobs.load_hpi`; metro chosen over tract, see `docs/research/step3-comps-2026-10-30.md`). Open: escalation of presets.
- [x] Recency weights by quarter (1.00, 0.75, 0.56, 0.42) and side-of-city blending for thin areas. Done in the cost index job; thin areas blend with neighboring community areas instead of a side of the city (CLAUDE.md rule 4).
- [x] Land value map: vacant-land and teardown sales, per sq ft of lot and per buildable sq ft, by Assessor neighborhood, with counts. Done 2026-10-30: `python -m jobs.build_land_values` (part of the nightly run): 664 vacant and 407 teardown sales in 36 months; teardown = sale followed by a demolition or new construction permit within 24 months; also per sq ft moved to a 3,125 sq ft lot (elasticity 0.858). Humboldt Park $16 per lot sq ft (50 sales), Logan Square $169 (46), Lincoln Park $414 (51).
- [x] Build-spec presets set from published evidence (production $165/$170).
- [ ] Rent estimate: ACS B25031/B25064 + 25% premium, ZORI growth, HUD SAFMR floor, csik-bsws cross-check. Done 2026-10-30 except the HUD floor: `python -m jobs.load_rents` (ACS from the keyless Census summary files, so no Census key is needed; ZORI by ZIP, growth only), `engine/rents.py`, `GET /parcels/{pin}/rent`. The 25% premium was measured with `python -m jobs.check_rents` against 171 Assessor income worksheets for apartments built 2014 or later: new buildings rent at 0.98 of ACS gross rent grown to 2024 (80% range 0.79-1.43), older ones at 0.85, so the factor is now 0.98. Open: HUD Small Area FMR floor (the HUD site blocks automated downloads; the HUD API needs a free token).
- [x] Comp filters from `sale_comps.filters` (deed type, repeat price, pre-completion sales). Done in `jobs/build_comps.py`; dropped sales stay in `comp` with the reason.
- [ ] Test: sale estimate within 15% for at least 70% of test parcels (69%, 24 of 35, after cleanup on 2026-10-29). Report the hit rate and median error, with a 95% interval. Added by the methods review: out-of-time holdout on the 2,450-sale pool at 55% or more within 15% and median error 13% or less; COD 20 or less for buildings and 15 or less for condo units; PRB interval overlapping -0.10 to +0.10; 80% band covering 75-85% of holdout sales. Status 2026-10-30 (`python -m jobs.check_comps`): test set 69% (24 of 35, 52-81%), median error 7.4%; holdout 57% within 15%, median error 12.4%, PRB -0.13 (-0.18 to -0.08), range coverage 76%; COD 24.8 buildings and 16.3 condo units miss their targets.
- [ ] Test: at actual sale and $60,000 land, at least 60% of test buildings show profit of $0 or more (57%, 20 of 35, on 2026-10-29). Status 2026-10-30 (`python -m jobs.check_costs`, `engine/costs.py`, each building on its real lot and current cost index): 51% (18 of 35). Misses cluster in Woodlawn (0 of 10) and Grand Boulevard (4 of 8). Next: check whether those sales were city-program homes with capped prices (decision 36).
- [x] Test: standard 3-flat total cost within -20%/+30% of $308,000-365,000 per unit. Done 2026-10-30 (`python -m jobs.check_costs`): $306,230 per unit, range $248,984 to $406,410 at -20%/+35%, which covers $308,000-365,000.

## Step 4: Feasibility engine and score

- [ ] All formulas from the spec for sell and hold, with the exact financing formula and margins that exclude land.
- [ ] Incentives v1 from `data/rules/incentives_v1.csv` (OZ $0 for sell; bonus depreciation as deferral).
- [ ] Pattern library scenarios from `data/rules/building_patterns.json`, checked against each zoning path.
- [ ] Residual land value, profit as percent of value and cost, existing-use check; cost at P50 and P80.
- [ ] Eligibility questions from `data/rules/incentive_questions.json` drive incentive toggles.
- [ ] Reference lines: margin on cost 15-20%, spread over cap rate 1.0 pt, DSCR 1.3; buyer financing class (2-4 residential vs 5+ commercial) and FHA limit flag; Open Space Impact Fee line.
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
- [ ] Fast-path filter, land value map layer, and city lots for sale (ChiBlockBuilder) layer.
- [ ] Deals screen matching `mockups/Deals.dc.html`: pipeline counts, deal table, outreach log, CSV export.
- [ ] Email sign-in.

## SaaS setup (weeks 8-17, alongside steps 4-6)

- [ ] Organizations from day one: org id on deals, saved searches and overrides; Postgres row-level security; owner and member roles.
- [ ] Stripe Checkout, customer portal, plan webhook, 14-day Pro trial, Stripe Tax.
- [ ] Chicago cloud tax (lease transaction tax, 15% since 2026-01-01) on invoices; accountant confirms registration.
- [ ] Hosting: managed Postgres with PostGIS and point-in-time restore, engine and jobs host, front-end host, PMTiles on object storage and CDN; staging and production.
- [ ] Error tracking, uptime checks, nightly-job alerts (failed pull or count drop over 10%), stale-data note on screen, tested restore.
- [ ] Security: secrets out of the repo, rate limits on search and PDF, audit log of overrides and exports, dependency scanning in CI, data deletion on request.
- [ ] Data licensing review: attribution for portals and basemap, Zillow internal only, no MLS.
- [ ] Onboarding: free address check, guided first parcel, sample deal, help pages, 2-minute video, support inbox.

## Step 7: Private test

- [ ] Staging host; family company and 5-10 brokers on real parcels; report-an-error button.
- [ ] Fix list closed; at least 3 testers say they would pay.

## Step 8: Launch

- [ ] Billing, terms of use (lawyer reviewed), support inbox.
- [ ] Landing page, free address check, community-area pages.
- [ ] First paying users.

## Version 1.1 (after launch)

- [ ] Saved searches with alerts; CSV import; teams and shared deals; comps drawer; sensitivity sliders; lender Excel export.
- [ ] Rezoning history near each parcel from City Council ordinances since 2011 (DataMade nightly database, chicago-council-scrapers), shown as facts: map amendments within half a mile in 5 years, share passed, median days to pass.
- [ ] Appeals (y282-6ig3, 7pny-nedm), HMDA lending on 2-4 unit buildings by tract, CPS attendance zones (x72b-38qv, xg7c-d8rm), incentive awards nearby (mex4-ppfc, wy5s-xrw5, rym7-49n8), RentCast per-address rents.
- [ ] Records from the FOIA requests in `docs/launch/foia-requests.md` (permit applications, map amendments, ZBA log, tax sale lists, Clerk recordings index, land bank inventory), once they arrive.

## Later, from the international review

- [ ] Permit-ready plan sets for the pattern library with partner architects (Phase 2).
- [ ] Entitlement tracker as gateways with one consolidated comment list per round (Phase 2a).
- [ ] Refit cost margins from actual job costs, P50/P80 (Phase 4).
- [ ] Policy mode: rerun all parcels under a proposed ordinance (after V1.1); seeded from `data/rules/pending_rules.json`.
- [ ] Assembly finder (land readjustment idea), fee-simple townhome scenario, appraisal-gap check from FHFA UAD (V1.1).

## Business setup (Marlon, alongside)

- [ ] LLC to own the product.
- [ ] Trademark and domain search for 25x125.
- [ ] Hosting account; free Socrata app tokens; free Census API key.
- [ ] Errors and omissions insurance quote before launch.
- [ ] MRED feed (steps in `docs/v1-spec.md`, MRED section).
- [ ] Send the five FOIA requests in `docs/launch/foia-requests.md` (commercial purpose stated).

## Open items to verify (from the plan)

- [ ] 2026 Chicago building code text (window percentages, corridor widths, travel distances).
- [ ] Building permit fee tables (residential construction factor is a $0.50/sf placeholder).
- [ ] Opportunity Zone 2027 certified tract list.
- [ ] Enterprise Zone residential eligibility.
- [ ] Film credit qualified expenditures (Interim, later).
