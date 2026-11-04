"""The map's background from the local Chicago file (jobs/build_basemap.py), so the map never waits on an outside
tile server. The file is opened once and opened again when the weekly copy replaces it."""

from __future__ import annotations

import mmap
import os
import threading
from pathlib import Path

from pmtiles.reader import Reader
from pmtiles.tile import Compression

DEFAULT_FILE = Path(__file__).resolve().parent.parent / "data" / "basemap" / "chicago.pmtiles"
_lock = threading.Lock()
_open: dict = {"key": None, "reader": None, "header": None, "meta": None, "mm": None}


def basemap_file() -> Path:
    return Path(os.environ.get("BASEMAP_FILE") or DEFAULT_FILE)


def _reader() -> tuple[Reader, dict, dict] | None:
    path = basemap_file()
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    key = (str(path), st.st_mtime_ns, st.st_size)
    with _lock:
        if _open["key"] != key:
            with open(path, "rb") as f:
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            reader = Reader(lambda offset, length: mm[offset : offset + length])
            _open.update(key=key, reader=reader, header=reader.header(), meta=reader.metadata(), mm=mm)
        return _open["reader"], _open["header"], _open["meta"]


def info() -> dict | None:
    """What the local file holds, or None when there is none (the map then uses the outside basemap)."""
    r = _reader()
    if r is None:
        return None
    _, h, meta = r
    return {
        "min_zoom": h["min_zoom"],
        "max_zoom": h["max_zoom"],
        "bounds": [
            h["min_lon_e7"] / 1e7,
            h["min_lat_e7"] / 1e7,
            h["max_lon_e7"] / 1e7,
            h["max_lat_e7"] / 1e7,
        ],
        "attribution": meta.get("attribution", "© OpenStreetMap contributors"),
        "source": meta.get("25x125_source"),
        "built_at": meta.get("25x125_built_at"),
    }


def tile(z: int, x: int, y: int) -> tuple[bytes, str | None] | None:
    """The tile's bytes as stored and their content encoding ('gzip' or None); None when the file has no tile."""
    r = _reader()
    if r is None:
        return None
    reader, h, _ = r
    if not h["min_zoom"] <= z <= h["max_zoom"]:
        return None
    data = reader.get(z, x, y)
    if not data:
        return None
    return bytes(data), "gzip" if h["tile_compression"] == Compression.GZIP else None
