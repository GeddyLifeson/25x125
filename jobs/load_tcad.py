"""Load Austin from the Travis Central Appraisal District's free certified appraisal export.

One zip (traviscad.org/publicinformation; the link is in region.json under appraisal_source) of fixed-width
text files, read straight from the zip. Column positions are from the district's "Legacy 8.0.33 Appraisal
Export Layout" (same page). Used here:
- PROP.TXT: property id, type, site address and ZIP, neighborhood, state codes, land value, market value
- IMP_DET.TXT: one row per building segment; living area is the sum of the floor segments (1ST, 2ND, 3RD,
  4TH, 1/2), year built is the newest of them
- LAND_DET.TXT: land square feet, summed over land segments
Only real property (type R) loads. The export's site city is blank, so every Travis County parcel loads and
the City of Austin zoning layer decides which lots have rules. Lot shapes come from the City of Austin copy
of the TCAD parcels (`parcel_layer` in region.json), joined on the property id.
The export holds no sale prices (Texas Government Code 552.148).
Run: python -m jobs.load_tcad [--zip file.zip] [--limit N]
"""

import argparse
import io
import urllib.request
import zipfile
from pathlib import Path

from core import region
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.load_arcgis_parcels import group_for
from jobs.load_dcad import load_shapes, save

HOST = "traviscad.org"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "tcad"
USE_GROUPS = {"A1": "single", "A2": "single", "A3": "single", "A4": "condo", "A5": "condo", "B1": "multi",
              "B2": "multi", "B3": "multi", "B4": "multi", "B5": "multi", "C1": "vacant"}  # fmt: skip
UNITS = {"B2": 2, "B3": 3, "B4": 4}
FLOORS = {"1ST", "2ND", "3RD", "4TH", "1/2"}


def col(line: str, start: int, end: int) -> str:
    """Columns as the layout numbers them: 1-based, inclusive."""
    return line[start - 1 : end].strip()


def _int(s: str) -> int:
    try:
        return int(s or 0)
    except ValueError:
        return 0


def fetch(url: str, opener=urllib.request.urlopen) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / "tcad.zip"
    if not path.exists():
        with opener(url, timeout=3600) as resp, open(path, "wb") as out:
            while chunk := resp.read(1 << 20):
                out.write(chunk)
    return path


def _lines(z: zipfile.ZipFile, name: str):
    member = next(n for n in z.namelist() if n.upper().endswith(name))
    with z.open(member) as fh:
        yield from io.TextIOWrapper(fh, encoding="latin-1")


def prop_row(line: str) -> tuple[str, dict] | None:
    if col(line, 13, 17) != "R":
        return None
    imprv, land = col(line, 2732, 2741).upper(), col(line, 2742, 2751).upper()
    street = " ".join(filter(None, (col(line, 4460, 4474), col(line, 1040, 1049), col(line, 1050, 1099),
                                    col(line, 1100, 1109), col(line, 4475, 4479))))  # fmt: skip
    return str(_int(col(line, 1, 12))), {
        "year": _int(col(line, 18, 22)), "use": imprv or land, "market": float(_int(col(line, 4214, 4227))) or None,
        "land": float(_int(col(line, 1796, 1810)) + _int(col(line, 1811, 1825))) or None,
        "address": " ".join(street.upper().split()) or None, "zip": col(line, 1140, 1149)[:5] or None,
        "nbhd": col(line, 1686, 1695) or None,
    }  # fmt: skip


def read(z: zipfile.ZipFile, limit: int | None = None) -> dict[str, dict]:
    acct: dict[str, dict] = {}
    for line in _lines(z, "PROP.TXT"):
        row = prop_row(line)
        if row and row[0] not in acct:  # one line per owner; the first is enough
            acct[row[0]] = row[1]
            if limit and len(acct) >= limit:
                break
    for line in _lines(z, "IMP_DET.TXT"):
        a = acct.get(str(_int(col(line, 1, 12))))
        if a is None or col(line, 41, 50).upper() not in FLOORS:
            continue
        a["living"] = a.get("living", 0) + round(float(col(line, 94, 108) or 0))
        built = _int(col(line, 86, 89))
        if built > 1700:
            a["built"] = max(a.get("built", 0), built)
    for line in _lines(z, "LAND_DET.TXT"):
        a = acct.get(str(_int(col(line, 1, 12))))
        if a is not None:
            a["land_sqft"] = a.get("land_sqft", 0) + float(col(line, 84, 97) or 0)
    for a in acct.values():
        a["units"] = UNITS.get(a["use"])
    return acct


def run(
    zip_path: str | None = None, limit: int | None = None, url: str | None = None, shapes: bool = True
) -> dict:
    r = region.current()
    src = r["appraisal_source"]
    path = Path(zip_path) if zip_path else fetch(src["url"])
    with connect(url) as conn:
        region.ensure_rows(conn)
        pull_id = start_pull(conn, HOST, "certified appraisal export", path.name)
        conn.commit()
        try:
            with zipfile.ZipFile(path) as z:
                acct = read(z, limit)
            save(conn, acct, r["id"], pull_id, lambda use: group_for(use, USE_GROUPS))
            finish_pull(conn, pull_id, len(acct))
            conn.commit()
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
            conn.commit()
            raise
        year = next(iter(acct.values()))["year"] if acct else 0
        n = load_shapes(conn, r["parcel_layer"], set(acct), year) if shapes else 0
    return {"parcels": len(acct), "shapes": n}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", help="the export zip already on disk")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    print(run(a.zip, a.limit))
