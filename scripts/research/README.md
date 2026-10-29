# Research scripts

One-off scripts run on 2026-10-28 to build `data/reference/`. They shell out to curl and take file paths as arguments. Port the logic into `jobs/`; don't import these.

- `parse.py`: first pass on West Side permits, 2-6 unit counts by area.
- `citywide.py`: citywide 2-6 unit new-construction permits, filters out repairs, porches, demolitions and mixed-use, requires reported cost of $100,000 or more, writes the community-area cost index.
- `match_sales.py`: matches permit addresses to Cook County PINs (3723-97qp) and then to later sales (wvhk-k5uv) to build the test parcels.

Known limit: reported permit costs run low (sales median 2.3x reported cost), so the index sets how neighborhoods compare, not the dollar level.
