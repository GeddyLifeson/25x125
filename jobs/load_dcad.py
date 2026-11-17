"""Load Dallas from the Dallas Central Appraisal District's free certified data files.

One zip of comma-delimited files (dallascad.org/DataProducts.aspx; the link is in region.json under
appraisal_source). Used here:
- ACCOUNT_APPRL_YEAR.CSV: market value (TOT_VAL), land value, taxing city, state property code (SPTD_CODE)
- ACCOUNT_INFO.CSV: site address, ZIP, appraisal neighborhood
- RES_DETAIL.CSV: year built, living area and unit count, summed over an account's buildings
- LAND.CSV: land area, summed over an account's land lines
Accounts whose taxing city is in the region's city_filter load. Lot shapes come from the City of Dallas copy
of the DCAD tax parcels (`parcel_layer` in region.json), joined on the account number.
The files hold no sale prices (Texas Government Code 552.148).
Run: python -m jobs.load_dcad [--dir folder-with-the-csvs] [--limit N]
"""

import argparse
import csv
import io
import json
import urllib.request
import zipfile
from pathlib import Path

from core import region
from core.arcgis import ArcGIS
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import integer, num, text, upsert
from jobs.load_arcgis_parcels import GEOM, MERGE, group_for

HOST = "www.dallascad.org"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "dcad"
USE_GROUPS = {"A11": "single", "A12": "single", "A13": "condo", "A2": "single", "B11": "multi", "B12": "multi",
              "C11": "vacant", "C14": "vacant"}  # fmt: skip


def fetch(url: str, opener=urllib.request.urlopen) -> Path:
    if RAW.exists() and (RAW / "ACCOUNT_APPRL_YEAR.CSV").exists():
        return RAW
    RAW.mkdir(parents=True, exist_ok=True)
    with opener(url, timeout=1800) as resp:
        zipfile.ZipFile(io.BytesIO(resp.read())).extractall(RAW)
    return RAW


def _rows(path: Path):
    with open(path, encoding="latin-1", newline="") as fh:
        yield from csv.DictReader(fh)


def read(folder: Path, cities: set[str], limit: int | None = None) -> dict[str, dict]:
    acct: dict[str, dict] = {}
    for r in _rows(folder / "ACCOUNT_APPRL_YEAR.CSV"):
        if cities and (r["CITY_JURIS_DESC"] or "").strip().upper() not in cities:
            continue
        acct[r["ACCOUNT_NUM"].strip()] = {
            "year": integer(r["APPRAISAL_YR"]), "use": (r["SPTD_CODE"] or "").strip().upper(),
            "market": num(r["TOT_VAL"]), "land": num(r["LAND_VAL"]),
        }  # fmt: skip
        if limit and len(acct) >= limit:
            break
    for r in _rows(folder / "ACCOUNT_INFO.CSV"):
        a = acct.get(r["ACCOUNT_NUM"].strip())
        if a is None:
            continue
        street = " ".join(
            filter(None, (text(r["STREET_NUM"]), text(r["FULL_STREET_NAME"]), text(r["UNIT_ID"])))
        )
        a.update(address=" ".join(street.upper().split()) or None, zip=(text(r["PROPERTY_ZIPCODE"]) or "")[:5] or None,
                 nbhd=text(r["NBHD_CD"]))  # fmt: skip
    for r in _rows(folder / "RES_DETAIL.CSV"):
        a = acct.get(r["ACCOUNT_NUM"].strip())
        if a is None:
            continue
        a["living"] = a.get("living", 0) + (integer(r["TOT_LIVING_AREA_SF"]) or 0)
        a["units"] = a.get("units", 0) + (integer(r["NUM_UNITS"]) or 0)
        built = integer(r["YR_BUILT"]) or 0
        if built > 1700 and (integer(r["TOT_LIVING_AREA_SF"]) or 0) > 0:
            a["built"] = max(a.get("built", 0), built)
    for r in _rows(folder / "LAND.CSV"):
        a = acct.get(r["ACCOUNT_NUM"].strip())
        size = num(r["AREA_SIZE"])
        if a is None or not size:
            continue
        unit = r["AREA_UOM_DESC"].strip().upper()
        sqft = size if unit == "SQUARE FEET" else size * 43560 if unit == "ACRE" else 0
        a["land_sqft"] = a.get("land_sqft", 0) + sqft
    return acct


def save(conn, acct: dict[str, dict], rid: str, pull_id: int, group=None) -> None:
    group = group or (lambda use: group_for(use, USE_GROUPS))
    parcels, addresses, buildings, values = [], [], [], []
    for pin, a in acct.items():
        zip5, use = a.get("zip"), a["use"]
        parcels.append((pin, pin, a["year"], rid, use or None, a.get("nbhd"), zip5,
                        int(zip5) if zip5 and zip5.isdigit() else None, zip5, group(use), pull_id))  # fmt: skip
        addresses.append((pin, a["year"], a.get("address"), zip5, pull_id))
        if a.get("living"):
            buildings.append((pin, pin, a["year"], 1, use or None, a.get("units") or None, a["living"],
                              round(a["land_sqft"]) if a.get("land_sqft") else None, a.get("built") or None, pull_id))  # fmt: skip
        if a["market"] or a["land"]:
            values.append(
                (
                    pin,
                    pin,
                    a["year"],
                    use or None,
                    a.get("nbhd"),
                    "certified",
                    a["market"],
                    a["land"],
                    pull_id,
                )
            )
    upsert(conn, "parcel", ["pin", "pin10", "tax_year", "municipality_id", "class", "nbhd_code", "zip",
                            "community_area_num", "community_area_name", "use_group", "source_pull_id"], "pin", parcels)  # fmt: skip
    upsert(conn, "parcel_address", ["pin", "tax_year", "address", "zip", "source_pull_id"], "pin", addresses)
    upsert(conn, "building_char", ["row_id", "pin", "tax_year", "card", "class", "apartments", "building_sqft",
                                   "land_sqft", "year_built", "source_pull_id"], "row_id", buildings)  # fmt: skip
    upsert(conn, "assessed_value", ["pin", "pin10", "tax_year", "class", "nbhd", "stage", "market_value",
                                    "land_market_value", "source_pull_id"], "pin, tax_year", values)  # fmt: skip


def load_shapes(conn, layer: dict, wanted: set[str], vintage: int, client: ArcGIS | None = None) -> int:
    client = client or ArcGIS(layer["url"], timeout=180)
    field = layer.get("id_field", "ACCT")
    pull_id = start_pull(
        conn, client.host, layer["url"].split("/rest/services/")[-1], layer.get("where", "1=1")
    )
    total = 0
    for page in client.features(
        layer.get("where", "1=1"),
        out_fields=field,
        key=layer.get("key", "OBJECTID"),
        page_size=layer.get("page_size", 2000),
    ):
        rows = []
        for f in page:
            raw = (f.get("properties") or {}).get(field)
            pin, g = text(int(raw) if isinstance(raw, float) and raw.is_integer() else raw), f.get("geometry")
            if pin in wanted and g and g.get("type") in ("Polygon", "MultiPolygon"):
                rows.append((pin, vintage, json.dumps(g), pull_id))
        total += upsert(conn, "parcel_shape", ["pin10", "vintage", "the_geom", "source_pull_id"], "pin10", rows, GEOM,
                        on_conflict=MERGE)  # fmt: skip
        conn.commit()
    conn.execute(
        "update parcel_shape s set lot_sqft = round(m.area_sqft), frontage_ft = round(m.short_ft, 1),"
        " depth_ft = round(m.long_ft, 1) from parcel_shape t, lateral lot_measures(t.geom) m"
        " where s.pin10 = t.pin10 and s.source_pull_id = %s",
        (pull_id,),
    )
    conn.execute(
        "update parcel p set geom = st_pointonsurface(s.geom) from parcel_shape s"
        " where s.pin10 = p.pin10 and s.source_pull_id = %s",
        (pull_id,),
    )
    finish_pull(conn, pull_id, total)
    return total


def run(
    folder: str | None = None, limit: int | None = None, url: str | None = None, shapes: bool = True
) -> dict:
    r = region.current()
    src = r["appraisal_source"]
    path = Path(folder) if folder else fetch(src["download_url"])
    with connect(url) as conn:
        region.ensure_rows(conn)
        pull_id = start_pull(
            conn, HOST, src.get("name", "DCAD certified data files"), ",".join(sorted(region.cities(r)))
        )
        conn.commit()
        try:
            acct = read(path, region.cities(r), limit)
            save(conn, acct, r["id"], pull_id)
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
    ap.add_argument("--dir", help="folder holding the unzipped DCAD csv files")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    print(run(a.dir, a.limit))
