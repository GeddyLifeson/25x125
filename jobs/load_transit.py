"""Load rail stations: CTA from the Chicago Data Portal (8pix-ypme), Metra from Metra's GTFS feed.

Run: python -m jobs.load_transit
"""

import csv
import io
import urllib.request
import zipfile

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import num, text, upsert

CTA_DATASET = "8pix-ypme"
METRA_GTFS = "https://schedules.metrarail.com/gtfs/schedule.zip"
COLUMNS = ["mode", "station_id", "name", "lines", "lon", "lat", "source_pull_id"]
GEOM = {"geom": "st_setsrid(st_makepoint(lon::float8, lat::float8), 4326)"}
CTA_LINES = {"red": "Red", "blue": "Blue", "g": "Green", "brn": "Brown", "p": "Purple", "y": "Yellow",
             "pnk": "Pink", "o": "Orange"}  # fmt: skip


def cta_stations(rows: list[dict]) -> dict[str, tuple]:
    """The portal lists one row per platform direction; keep one per station (map_id) with all its lines."""
    out: dict[str, tuple] = {}
    for r in rows:
        loc = r.get("location") or {}
        sid = text(r.get("map_id"))
        if not sid or num(loc.get("latitude")) is None:
            continue
        lines = {name for k, name in CTA_LINES.items() if str(r.get(k)).lower() == "true"}
        prev = out.get(sid)
        if prev:
            lines |= set(prev[3].split(", ")) if prev[3] else set()
        name = text(r.get("station_descriptive_name")) or text(r.get("station_name"))
        out[sid] = ("cta", sid, name, ", ".join(sorted(lines)), loc["longitude"], loc["latitude"])
    return out


def metra_stations(gtfs_zip: bytes) -> list[tuple]:
    with zipfile.ZipFile(io.BytesIO(gtfs_zip)) as z:
        reader = csv.DictReader(io.TextIOWrapper(z.open("stops.txt"), encoding="utf-8-sig"))
        rows = [{k.strip(): (v or "").strip() for k, v in r.items()} for r in reader]
    return [
        ("metra", r["stop_id"], r["stop_name"], None, r["stop_lon"], r["stop_lat"])
        for r in rows
        if r.get("stop_lat")
    ]


def run(socrata: Socrata | None = None, gtfs: bytes | None = None, url: str | None = None) -> dict[str, int]:
    socrata = socrata or Socrata(CHICAGO)
    counts = {}
    with connect(url) as conn:
        pull_id = start_pull(conn, CHICAGO, CTA_DATASET)
        rows = [r for page in socrata.pages(CTA_DATASET, order=":id") for r in page]
        stations = cta_stations(rows)
        conn.execute("delete from transit_station where mode = 'cta'")
        counts["cta"] = upsert(
            conn,
            "transit_station",
            COLUMNS,
            "mode, station_id",
            (s + (pull_id,) for s in stations.values()),
            GEOM,
        )
        finish_pull(conn, pull_id, counts["cta"])

        pull_id = start_pull(conn, "schedules.metrarail.com", "gtfs/stops.txt")
        if gtfs is None:
            with urllib.request.urlopen(METRA_GTFS, timeout=120) as resp:
                gtfs = resp.read()
        conn.execute("delete from transit_station where mode = 'metra'")
        counts["metra"] = upsert(
            conn,
            "transit_station",
            COLUMNS,
            "mode, station_id",
            (s + (pull_id,) for s in metra_stations(gtfs)),
            GEOM,
        )
        finish_pull(conn, pull_id, counts["metra"])
    return counts


if __name__ == "__main__":
    for mode, n in run().items():
        print(f"{mode} stations: {n:,}")
