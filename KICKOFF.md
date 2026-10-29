# Kickoff prompt

Paste this into Claude Code as the first message, from inside this folder.

---

Read CLAUDE.md, TASKS.md and docs/v1-spec.md in full before doing anything. Then skim docs/plan.md and the files in data/.

We're starting Step 0 and Step 1 in TASKS.md. Read docs/calibration-2026-10-29.md too. Before writing code:

1. Tell me the repo layout (jobs/, engine/ with FastAPI, web/ with Next.js), in a short list.
2. Check that Docker and Python are available on this machine, and tell me what's missing.
3. Datasets were checked on 2026-10-29. Re-run a one-row query on each and report any that changed.

Then build Step 1 in this order: docker-compose with PostGIS, migrations, the shared Socrata client, the Cook County loaders, the Chicago layer loaders, the nightly signal jobs, and the spatial joins. Commit after each piece with a plain commit message.

Finish by running the Step 1 test (all 37 test parcels resolve to a parcel with zoning, lot area and frontage) and show me the load report. Stop there and wait for me before starting Step 2.

End your reply with any questions you have for me.
