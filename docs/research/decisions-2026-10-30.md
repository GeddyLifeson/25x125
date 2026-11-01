# Methods review decisions, 2026-10-30

The full review is `docs/research/reports/Methods review for V1 build.md` (66 numbered decisions with sources). This file records which ones are in the code now, which are queued for the step they belong to, and which need Marlon or counsel. Numbers in brackets are the report's decision numbers.

## Applied on 2026-10-30

| # | Change | Where | Effect |
|---|---|---|---|
| 19 | Neighborhood cost index applies to the production preset only, index capped at 1.3; standard and high presets use 1.0, because the index already picks them. This is the rule the calibration used. | `data/rules/feasibility_defaults.json` | Lincoln Park 3-flat: $368 to $250 per sq ft |
| 18 | The high cost figure is labeled "high case (about P90)", not P80 | `feasibility_defaults.json` | Label only; a computed P80 comes with step 4 |
| 20 | The index caveat now says what the data shows: 69% of permit costs are exact multiples of $50,000 and the permit fee does not depend on them | `feasibility_defaults.json` | Text |
| 14 | Spec acceptance lines read 24 of 35 and 20 of 35 | `docs/v1-spec.md` | Text |
| 42 | The 10% administrative adjustment keeps the practice reading (lot area per unit), labeled as disputed with both sources; the code text says minimum lot area | `zoning_steps.json`, `engine/zoning.py` | 4 test buildings depend on it |
| 43 | The +10% height adjustment carries the abutting-building condition (17-13-1003-L-3) | same | Note on the path |
| 44 | Parking by district from 17-10-0207: 2 per unit in RS, 1.5 per unit for an RS-3 two-flat, 1 elsewhere, 0.6 after the 100th unit in -5 districts; Metra-only transit-served lots get 50% off by right; narrow-lot (33 ft) exemption noted; cites O2025-0015577 | same | RS-3 two-flat: 3 spaces, not 2 |
| 49 | ADUs in RS and RT-3.5 need an administrative adjustment (17-13-1003-QQ), with the yearly block-face cap (1, 2, 3) and owner occupancy shown | same | Approval label and notes |
| 47 | Zoning is the district with the largest share of the lot; the second district and its share are kept (slivers under 2% ignored) | `jobs/build_parcel_site.py`, migration 0012 | Split lots on arterials get the right district |
| 50 | Signals match by source PIN, then exact address, then point in lot, then nearest lot within 15 m; the method is stored per record | same, migration 0014 | Fewer violations pinned to the neighbor |
| 51 | Units on a lot sum all building cards (coach houses count); condo parking and common-area PINs count 0 | `jobs/build_lot_use.py` | 68,113 parking PINs dropped from unit counts |
| 48 | Block faces come from street centerline segments (pr57-gg9e) by address range and side; the hundred block is the fallback | `jobs/load_streets.py`, `build_lot_use.py`, migration 0013 | 575,353 lots on a true block face, 25,961 on the fallback |

Tests: 5 new zoning tests (parking ratios, Metra-only, narrow lot, ADU approval, split-zone flag); 44 pass.

## Queued for the step they belong to

- Step 3 (comps and cost): [3] size adjustment, [4] condo vs building, [5] FHFA time index, [6] 5-year cap, [7] empirical-Bayes blend, [9] Assessor outlier flags, [10] timing and LLC-seller flags, [11] LightGBM shadow check, [12] assessed-value gap flag, [13] the new accuracy targets (now in TASKS.md), [23] escalation to the build midpoint, [35] land value map method.
- Step 4 (feasibility): [25] exact residual formula, [28] pre-permit land carry, [30] sell-period loan balance, [33] comp value beside income value, [34] existing-use check, [36] Missing Middle price cap, [38] bonus depreciation as deferral, [39] Enterprise Zone savings before financing, [56] sensitivity grid, [59] score backtest, [60] score copy.
- Later in step 1-2: [45] Type A exclusion and conversion bonus, [46] street-aware frontage, [41] envelope check flag.
- Step 5 (screens): [52] range display, [53] public accuracy table, [61] estimate disclaimers.

## Decided on 2026-10-30 (Marlon asked that open questions be settled here unless only he can answer them)

Each is a data edit and can be changed back in one line.

| # | Decision | Where | Why |
|---|---|---|---|
| 26 | Default target return 20% on cost; 15%, 20% and 25% shown as reference lines, plus margin on net sale | `feasibility_defaults.json` sell | 15% is the low end of RICS and PPG benchmarks; with a residual that moves 29% on a 5% sale miss, the default should not sit at the floor. Lowers the stylized residual about $50,000. |
| 16, 17 | Cost high margins: feasibility +35%, layout +25%, bids +10% (drawings +15% unchanged) | `margins_by_stage` | ASTM E2516 / AACE class ranges and the Alberta series. Refit from the contractor's job costs after 20 jobs. |
| 8 | Sale range is a calibrated 80% band from leave-one-out errors by ring and kind, about x0.74 to x1.36 today | `sale_value_range` | The 25th-75th range covered 49% of test sales. |
| 25 | Residual solved exactly: net sale / ((1 + target) x (1 + finance share)) - other costs | `residual` | The current formula ignores finance on the land; +$15,800 on the Humboldt Park 3-flat. |
| 54-56 | Seeded 10,000-draw Monte Carlo in V1 with P10, P50, P90 and the share of draws at a loss; the low-sale, high-cost corner labeled "stress case"; sale-to-cost correlation 0.3, editable; a 5 x 5 dollar grid beside it | `range_method` | Corner math overstates the downside (stylized P10 -$122,632 vs corner -$265,650). Seeded, so a rerun gives the same answer. |
| 31 | Explicit property-tax line in the hold scenario; value = NOI before tax / (cap rate + effective tax rate) | `hold.property_tax` | Taxes are 24-32% of NOI in Chicago; Assessor practice. |
| 58 | Location points: transit-served 5, comp depth (6+ comps within 0.75 mi) 5; profit points use the 25th-percentile return; score labeled as a sorting aid | `development_score.json` | Area sale prices already drive profit, so they were counted twice. |
| 29 | Loan origination fee 1% of the loan, labeled a placeholder | `financing` | Common range; replace with a lender quote when Marlon has one. |
| 22 | The 22% soft cost is split into named lines in step 4 from the published shares (New Mexico MFA 2025, HUD MAP), summing to 22% | step 4 | The contractor's split replaces it when it arrives. |
| 42 | The 10% administrative adjustment keeps the practice reading (lot area per unit), labeled as disputed on screen | `zoning_steps.json` | 4 permitted test buildings match the practice reading; the label covers the code-text risk. |

## Needs counsel (only Marlon can hire one)

- [42] Which reading of 17-13-1003-A the Zoning Administrator applies.
- [62, 63] Whether showing automated values needs an appraisal license under 225 ILCS 458, given the section 5-5 exemption repeal on 2027-01-01, and broker use as a BPO.
- [37] Opportunity Zone dates and the 2027 tract list.
- [64] Terms that bar credit-decision use.
