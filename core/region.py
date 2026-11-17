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


SHARED_DIR = REGIONS_DIR / "_shared" / "rules"


def rules_file(name: str, region_id: str | None = None) -> Path:
    """The region's copy of a rules file when it has one; else, outside Chicago, the copy shared by the new
    regions (data/regions/_shared/rules); else the Chicago copy in data/rules."""
    rid = region_id or settings.region
    own = rules_dir(rid) / name
    if own.exists():
        return own
    shared = SHARED_DIR / name
    return shared if rid != "chicago" and shared.exists() else RULES_DIR / name


def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def rules_json(name: str, region_id: str | None = None) -> dict:
    """A JSON rules file with the region's changes applied. A file marked "extends": true holds only what
    differs; it is laid over the next copy down (region, then the new regions' shared copy, then Chicago's)."""
    rid = region_id or settings.region
    layers = [RULES_DIR / name]
    if rid != "chicago":
        layers += [SHARED_DIR / name, rules_dir(rid) / name]
    out: dict = {}
    for path in layers:
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        out = _merge(out, data) if data.get("extends") else data
    return out


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


def cities(r: dict | None = None) -> set[str]:
    """Upper-case city names whose parcels belong to the region (region.json city_filter)."""
    f = (r or current()).get("city_filter") or []
    values = f.get("values", []) if isinstance(f, dict) else f
    return {str(v).upper() for v in values}


STATE_ZIP_PREFIXES = {"IL": ("60", "61", "62"), "FL": ("32", "33", "34"), "GA": ("30", "31", "398", "399"),
                      "TX": ("75", "76", "77", "78", "79", "885")}  # fmt: skip
STATE_FIPS = {"IL": "17", "FL": "12", "GA": "13", "TX": "48"}


def clean_parcel_id(raw: str) -> str | None:
    """The parcel ID as stored, or None when it cannot be one. Cook PINs lose their dashes."""
    pid = raw.replace("-", "").strip() if is_chicago() else raw.strip()
    return pid if valid_parcel_id(pid) else None


def parcel_id_error() -> str:
    if is_chicago():
        return "PIN must be 10 or 14 digits"
    return f"{current().get('parcel_id_label', 'Parcel ID')} is not in a form this region uses"


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
