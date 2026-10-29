# 25x125

Development pipeline software for small real estate companies in Illinois, starting with Chicago. For any parcel it shows what zoning allows, what a 2-6 unit or small mixed-use building would cost there (in dollars, with dollar margins), which incentives apply, and whether the project makes money as a sale or a hold.

Named for the standard Chicago lot: 25 by 125 feet.

## Status

Planning and the first calibration run are done (2026-10-29). Code starts at Step 0 in `TASKS.md`.

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

## Getting started

1. Install Git, Docker Desktop, Python 3.12 and Node 20+.
2. Copy `.env.example` to `.env` and add keys as you get them (none are needed to start).
3. Open this folder in Claude Code and paste the prompt from `KICKOFF.md`.

## Data

Version 1 uses free public data from the Chicago Data Portal, the Cook County data catalog, the Census Bureau and HUD. MLS data from MRED comes later under a separate license.

Results are estimates. They are not zoning, legal, tax or appraisal advice.
