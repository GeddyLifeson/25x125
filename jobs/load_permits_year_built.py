"""Year built from finished new-construction permits, for regions whose parcel layer has no year built.

Atlanta's free parcel layer carries the appraised value and the number of units but not the year built, so the
comp pool (jobs/build_region.py, appraised values of 1-6 unit buildings built since `comps.built_since`) was
empty. The City of Atlanta publishes every building permit since 2019 with its status and a point. A parcel
whose lot holds a finished "Residential New" or "Multi Family New" permit gets that permit's status year as
its year built. Settings in region.json `permits_year_built`:

  url            CSV download
  types          record types that mean a new building
  done_statuses  statuses that mean the building is finished (CO issued, complete, closed)
  fields         {"type", "status", "status_date", "lat", "lon", "id"}
"""

import argparse
import csv
import io
import urllib.request
from datetime import datetime
from pathlib import Path

from core import region
from core.db import connect
from core.sources import finish_pull, start_pull


def finished(rows, cfg: dict) -> list[tuple[str, int, float, float]]:
    """(permit id, year finished, lat, lon) for finished new-building permits."""
    f = cfg["fields"]
    types, done = set(cfg["types"]), set(cfg["done_statuses"])
    out = []
    for r in rows:
        if r.get(f["type"]) not in types or r.get(f["status"]) not in done:
            continue
        try:
            year = datetime.strptime(r[f["status_date"]].strip(), cfg.get("date_format", "%m/%d/%Y")).year
            lat, lon = float(r[f["lat"]]), float(r[f["lon"]])
        except (KeyError, ValueError, AttributeError):
            continue
        out.append((r[f["id"]], year, lat, lon))
    return out


def run(text: str | None = None, url: str | None = None) -> dict:
    cfg = region.current()["permits_year_built"]
    if text is None:
        with urllib.request.urlopen(cfg["url"], timeout=300) as resp:
            text = resp.read().decode("utf-8-sig")
    permits = finished(csv.DictReader(io.StringIO(text)), cfg)
    with connect(url) as conn:
        pull_id = start_pull(conn, cfg["url"].split("/")[2], cfg["url"], "finished new-building permits")
        conn.execute(
            "create temp table permit_done (id text, year int, lat float8, lon float8) on commit drop"
        )
        with conn.cursor().copy("copy permit_done from stdin") as cp:
            for row in permits:
                cp.write_row(row)
        # Latest finished permit on each lot; the building's year built is the year it was finished.
        n = conn.execute(
            """
            with hit as (
              select distinct on (s.pin10) s.pin10, d.year
              from permit_done d
              join parcel_shape s on st_contains(s.geom, st_setsrid(st_makepoint(d.lon, d.lat), 4326))
              order by s.pin10, d.year desc
            )
            update building_char b set year_built = hit.year from hit
            where b.pin = hit.pin10 and (b.year_built is null or b.year_built < hit.year)
            """
        ).rowcount
        finish_pull(conn, pull_id, n)
    return {"finished permits": len(permits), "buildings dated": n}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", help="read a saved copy of the CSV instead of downloading it")
    a = ap.parse_args()
    print(run(Path(a.file).read_text(encoding="utf-8-sig") if a.file else None))
