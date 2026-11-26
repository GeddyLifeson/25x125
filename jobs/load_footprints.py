"""Floor area and year built from county building footprints, for regions whose parcel layer has neither.

Atlanta's comps are appraised values with no floor area, so the size adjustment cannot run (42.7% median error
on 2026-11-19). Fulton County publishes every building footprint with its footprint area, stories, year built,
living units and parcel ID. Floor area = footprint area x stories (1 when stories is blank), summed over the
residential buildings on each parcel. It counts attached garages and covered porches, so it runs above the
heated living area. A blank year built in building_char takes the footprint's year. Settings in region.json
`footprints`:

  url     the footprint layer
  where   filter (residential buildings)
  fields  {"pin", "area", "stories", "year", "units"}

Run: python -m jobs.load_footprints   (REGION set; after the parcel loader)
"""

from collections import defaultdict

from core import region
from core.arcgis import ArcGIS
from core.db import connect
from core.sources import finish_pull, start_pull


def per_parcel(features, f: dict) -> dict[str, dict]:
    """{pin: {"sqft": floor area, "year": newest year built, "units": living units}} from footprint features."""
    out: dict[str, dict] = defaultdict(lambda: {"sqft": 0.0, "year": None, "units": 0})
    for feat in features:
        a = feat.get("properties") or {}
        pin = (a.get(f["pin"]) or "").strip()
        area = a.get(f["area"]) or 0
        if not pin or area <= 0:
            continue
        stories = a.get(f["stories"]) or 1
        rec = out[pin]
        rec["sqft"] += float(area) * float(stories)
        rec["units"] += int(a.get(f["units"]) or 0)
        try:
            year = int(str(a.get(f["year"]) or "").strip()[:4])
        except ValueError:
            year = None
        if year and 1800 < year < 2100:
            rec["year"] = max(rec["year"] or 0, year)
    return dict(out)


def run(url: str | None = None) -> dict:
    cfg = region.current().get("footprints")
    if not cfg:
        raise SystemExit(f"region {region.region_id()}: no footprints layer in region.json")
    layer = ArcGIS(cfg["url"])
    f = cfg["fields"]
    fields = ",".join(f[k] for k in ("pin", "area", "stories", "year", "units"))
    feats = [x for page in layer.features(cfg.get("where", "1=1"), fields, extra={"returnGeometry": "false"})
             for x in page]  # fmt: skip
    recs = per_parcel(feats, f)
    with connect(url) as conn:
        pull_id = start_pull(conn, layer.host, cfg["url"], "building footprints (floor area, year built)")
        conn.execute("create temp table fp (pin text primary key, sqft numeric, year int, units int)")
        with conn.cursor() as cur:
            cur.executemany(
                "insert into fp values (%s, %s, %s, %s)",
                [(p, round(r["sqft"]), r["year"], r["units"]) for p, r in recs.items()],
            )
        n_sqft = conn.execute(
            "update building_char b set building_sqft = fp.sqft from fp where fp.pin = b.pin"
            " and coalesce(b.building_sqft, 0) = 0 and fp.sqft > 0"
        ).rowcount
        n_year = conn.execute(
            "update building_char b set year_built = fp.year from fp where fp.pin = b.pin"
            " and b.year_built is null and fp.year is not null"
        ).rowcount
        finish_pull(conn, pull_id, len(recs))
        conn.commit()
    return {
        "footprints": len(feats),
        "parcels": len(recs),
        "floor area set": n_sqft,
        "year built set": n_year,
    }


if __name__ == "__main__":
    print(run())
