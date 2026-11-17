"""Which market this install serves, and where its rules live.

One install (one database) serves one region. Chicago is the default and keeps its files in data/rules.
Another region keeps a region.json in data/regions/<id>/ and may override any rules file in
data/regions/<id>/rules/; files it does not override come from data/rules. Set REGION in the
environment (or .env) to switch, for example REGION=tampa.
"""

import json
from functools import cache
from pathlib import Path

from core.settings import settings

ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "data" / "rules"
REGIONS_DIR = ROOT / "data" / "regions"


@cache
def load(region_id: str | None = None) -> dict:
    """The region's settings (data/regions/<id>/region.json)."""
    rid = region_id or settings.region
    return json.loads((REGIONS_DIR / rid / "region.json").read_text())


def current() -> dict:
    return load(settings.region)


def region_id() -> str:
    return settings.region


def rules_dir(region_id: str | None = None) -> Path:
    """The region's own rules folder (may not exist)."""
    return REGIONS_DIR / (region_id or settings.region) / "rules"


def rules_file(name: str, region_id: str | None = None) -> Path:
    """The region's copy of a rules file when it has one, else the shared (Chicago) copy."""
    own = rules_dir(region_id) / name
    return own if own.exists() else RULES_DIR / name


def all_ids() -> list[str]:
    return sorted(p.name for p in REGIONS_DIR.iterdir() if (p / "region.json").exists())


def is_chicago() -> bool:
    return settings.region == "chicago"


def lot_id(parcel_id: str) -> str:
    """The lot a parcel ID belongs to. Cook County PINs are 14 digits and the first 10 name the lot (condo
    units share it). Everywhere else one parcel ID is one lot."""
    return parcel_id[:10] if is_chicago() else parcel_id


def valid_parcel_id(parcel_id: str) -> bool:
    if is_chicago():
        return parcel_id.isdigit() and len(parcel_id) in (10, 14)
    return 3 <= len(parcel_id) <= 40 and all(c.isalnum() or c in "-._ " for c in parcel_id)


def ensure_rows(conn) -> None:
    """Add this region's county and city rows (Chicago's come with the first migration)."""
    r = current()
    for c in r["counties"]:
        conn.execute(
            "insert into county (id, name, state) values (%s, %s, %s) on conflict (id) do nothing",
            (c["id"], c["name"], r["state"]),
        )
    conn.execute(
        "insert into municipality (id, name, county_id, loaded) values (%s, %s, %s, true)"
        " on conflict (id) do nothing",
        (r["id"], r["name"], r["counties"][0]["id"]),
    )
