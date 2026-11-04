"""Cut the map's background for Chicago out of the Protomaps daily build of OpenStreetMap.

Writes data/basemap/chicago.pmtiles (about the areas and zooms in data/rules/basemap.json). The engine serves its
tiles at /tiles/basemap/{z}/{x}/{y}, so the map never waits on an outside tile server. Reads only the tiles it needs
from the remote file with HTTP range requests (a few thousand tiles, about 2 minutes).
Run: python -m jobs.build_basemap [--date YYYYMMDD] [--out path]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pmtiles.reader import Reader
from pmtiles.tile import zxy_to_tileid
from pmtiles.writer import Writer

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "data" / "rules" / "basemap.json"
OUT = ROOT / "data" / "basemap" / "chicago.pmtiles"
UA = "25x125-basemap/1.0"


def load_rules() -> dict:
    return json.loads(RULES.read_text())


def tile_range(bbox: list[float], z: int) -> tuple[range, range]:
    """Tile columns and rows covering a lon/lat box at zoom z (web mercator, XYZ)."""
    west, south, east, north = bbox
    n = 2**z

    def x(lon: float) -> int:
        return min(n - 1, max(0, int((lon + 180) / 360 * n)))

    def y(lat: float) -> int:
        r = math.radians(lat)
        return min(n - 1, max(0, int((1 - math.asinh(math.tan(r)) / math.pi) / 2 * n)))

    return range(x(west), x(east) + 1), range(y(north), y(south) + 1)


def wanted_tiles(areas: list[dict]) -> list[tuple[int, int, int]]:
    out: set[tuple[int, int, int]] = set()
    for a in areas:
        lo, hi = a["zooms"]
        for z in range(lo, hi + 1):
            xs, ys = tile_range(a["bbox"], z)
            out.update((z, x, y) for x in xs for y in ys)
    return sorted(out, key=lambda t: zxy_to_tileid(*t))


def http_source(url: str, retries: int = 4):
    """get_bytes for pmtiles.Reader over HTTP ranges, keeping the header and directories it has read."""
    cache: dict[tuple[int, int], bytes] = {}

    def fetch(offset: int, length: int) -> bytes:
        for attempt in range(retries):
            try:
                req = urllib.request.Request(
                    url, headers={"Range": f"bytes={offset}-{offset + length - 1}", "User-Agent": UA}
                )
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = r.read()
                if len(data) != length:
                    raise OSError(f"got {len(data)} bytes, wanted {length}")
                return data
            except (urllib.error.URLError, OSError):
                if attempt == retries - 1:
                    raise
                time.sleep(2**attempt)
        raise AssertionError("unreachable")

    def get_bytes(offset: int, length: int, keep: bool = True) -> bytes:
        key = (offset, length)
        if key in cache:
            return cache[key]
        data = fetch(offset, length)
        if keep:
            cache[key] = data
        return data

    return get_bytes


def latest_build(template: str, today: dt.date, days: int = 8) -> str:
    """The newest daily build that exists (the bucket keeps a week)."""
    for back in range(days):
        url = template.format(date=(today - dt.timedelta(days=back)).strftime("%Y%m%d"))
        req = urllib.request.Request(url, headers={"Range": "bytes=0-126", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status in (200, 206):
                    return url
        except urllib.error.URLError:
            continue
    raise RuntimeError(f"no Protomaps build found in the last {days} days ({template})")


def run(date: str | None = None, out: Path = OUT, workers: int = 16) -> dict:
    rules = load_rules()
    url = rules["source"].format(date=date) if date else latest_build(rules["source"], dt.date.today())
    t0 = time.time()
    directories = http_source(url)
    reader = Reader(directories)
    header, meta = reader.header(), reader.metadata()
    tiles = wanted_tiles(rules["areas"])

    # Directories are cached; tile bytes are not (each is read once).
    def one(t: tuple[int, int, int]) -> tuple[tuple[int, int, int], bytes | None]:
        return t, reader.get(*t)

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    found = 0
    with open(tmp, "wb") as f, ThreadPoolExecutor(workers) as pool:
        w = Writer(f)
        for (z, x, y), data in pool.map(one, tiles):  # map keeps the order, so the file stays clustered
            if data:
                w.write_tile(zxy_to_tileid(z, x, y), data)
                found += 1
        boxes = [a["bbox"] for a in rules["areas"]]
        west, south = min(b[0] for b in boxes), min(b[1] for b in boxes)
        east, north = max(b[2] for b in boxes), max(b[3] for b in boxes)
        zooms = [z for a in rules["areas"] for z in a["zooms"]]
        e7 = lambda v: int(v * 10_000_000)
        hdr = {
            "tile_type": header["tile_type"],
            "tile_compression": header["tile_compression"],
            "min_zoom": min(zooms),
            "max_zoom": max(zooms),
            "min_lon_e7": e7(west),
            "min_lat_e7": e7(south),
            "max_lon_e7": e7(east),
            "max_lat_e7": e7(north),
            "center_zoom": 11,
            "center_lon_e7": e7(-87.73),
            "center_lat_e7": e7(41.84),
        }
        meta = {
            **meta,
            "attribution": rules["attribution"],
            "25x125_source": url,
            "25x125_built_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        }
        w.finalize(hdr, meta)
    os.replace(tmp, out)
    res = {"source": url, "tiles": found, "asked": len(tiles), "bytes": out.stat().st_size,
           "seconds": round(time.time() - t0)}  # fmt: skip
    print(f"basemap: {found:,} tiles, {res['bytes'] / 1e6:.1f} MB from {url} in {res['seconds']} s -> {out}")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="Protomaps build date, YYYYMMDD (default: the newest)")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    run(a.date, a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
