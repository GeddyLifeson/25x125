"""Load a Florida region from the Department of Revenue's free statewide tax roll files.

One file set per county and roll year, the same layout in all 67 counties:
- NAL (name, address, legal): one row per parcel with use code, just value, land value, lot and living area,
  year built, residential units, and the two most recent sales with price, month and qualification code.
- Parcel map: a shapefile of lot polygons keyed by parcel number.
Index and files: https://floridarevenue.com/property/Pages/DataPortal_RequestAssessmentRollGISData.aspx

A parcel belongs to the region when its taxing authority code is one of the county's `tax_auth_codes` in
region.json, or starts with one of its `tax_auth_prefixes` (the city's codes). With neither, the city name in
`city_filter` decides, and with no city filter every parcel in the county loads. Sale dates are known to
the month only, so each is stored as the first of its month. Qualification codes 01 and 02 are arm's-length
sales (Real Property Transfer Codes, floridarevenue.com/property/Documents/salequalcodes_aft01012025.pdf).

Run: python -m jobs.load_fl_dor [--nal file.csv --shapes file.shp] [--limit N]
Files download to data/raw/fl/ once and are reused.
"""

import argparse
import csv
import io
import json
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterator
from pathlib import Path

from core import region
from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import integer, num, text, upsert

HOST = "floridarevenue.com"
BASE = "https://floridarevenue.com/property/dataportal/Documents/PTO Data Portal/"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "fl"
QUALIFIED = ("01", "02")

# Department of Revenue land use codes (three digits): 000 vacant residential, 001 single family, 002 mobile
# home, 003 multi-family of 10 or more units, 004 condominium, 005 cooperative, 008 multi-family under 10 units.
USE_GROUPS = {"000": "vacant", "001": "single", "002": "single", "003": "multi", "004": "condo", "005": "condo",
              "008": "multi"}  # fmt: skip


def use_group(dor_uc: str | None) -> str:
    return USE_GROUPS.get((dor_uc or "").zfill(3), "other")


def nal_url(county: dict, roll: str) -> str:
    year = roll[:4]
    kind = "Final" if roll.endswith("F") else "Preliminary"
    name = f"{county['dor_name']} {county['dor_county_no']} {kind} NAL {year}.zip"
    return BASE + f"Tax Roll Data Files/NAL/{roll}/{name}"


def shapes_url(county: dict, roll: str) -> str:
    return BASE + f"Map Data/{roll}/{roll} PIN/{county['shape_name']}_{roll[:4]}pin.zip"


def fetch(url: str, opener=urllib.request.urlopen) -> Path:
    """Download once into data/raw/fl and unzip; return the folder."""
    name = url.rsplit("/", 1)[1]
    folder = RAW / name.removesuffix(".zip").replace(" ", "_")
    if folder.exists() and any(folder.iterdir()):
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    quoted = urllib.parse.quote(url, safe=":/")
    with opener(quoted, timeout=600) as resp:
        zipfile.ZipFile(io.BytesIO(resp.read())).extractall(folder)
    return folder


def in_region(row: dict, county: dict, cities: set[str]) -> bool:
    codes, prefixes = county.get("tax_auth_codes") or [], tuple(county.get("tax_auth_prefixes") or [])
    if codes or prefixes:
        code = (row.get("TAX_AUTH_CD") or "").strip()
        return code in codes or bool(prefixes and code.startswith(prefixes))
    return not cities or (row.get("PHY_CITY") or "").strip().upper() in cities


def sales_of(row: dict) -> Iterator[tuple]:
    """(n, date, price, doc, qualification, multi-parcel, vacant at sale) for the roll's two sales."""
    for n in ("1", "2"):
        price, year, month = (
            num(row.get("SALE_PRC" + n)),
            integer(row.get("SALE_YR" + n)),
            integer(row.get("SALE_MO" + n)),
        )
        if not price or not year or price <= 0:
            continue
        book, page = text(row.get("OR_BOOK" + n)), text(row.get("OR_PAGE" + n))
        doc = text(row.get("CLERK_NO" + n)) or (f"book {book} page {page}" if book and page else None)
        qual = (text(row.get("QUAL_CD" + n)) or "").zfill(2)
        vi = text(row.get("VI_CD" + n))
        yield (n, f"{year:04d}-{min(max(month or 1, 1), 12):02d}-01", price, doc, qual,
               bool(text(row.get("MULTI_PAR_SAL" + n))) or qual == "05", None if vi is None else vi == "V")  # fmt: skip


def read_nal(path: Path, county: dict, cities: set[str], limit: int | None = None) -> Iterator[dict]:
    with open(path, encoding="latin-1", newline="") as fh:
        n = 0
        for row in csv.DictReader(fh):
            if not text(row.get("PARCEL_ID")) or not in_region(row, county, cities):
                continue
            yield row
            n += 1
            if limit and n >= limit:
                return


def load_nal(conn, path: Path, county: dict, pull_id: int, limit: int | None = None) -> int:
    r = region.current()
    cities = region.cities(r)
    parcels, addresses, buildings, sales, values = [], [], [], [], []
    for row in read_nal(path, county, cities, limit):
        pin = text(row["PARCEL_ID"])
        year = integer(row.get("ASMNT_YR")) or int(r.get("roll", "2026F")[:4])
        uc = (text(row.get("DOR_UC")) or "").zfill(3)
        zip5 = (text(row.get("PHY_ZIPCD")) or "")[:5] or None
        tract = (text(row.get("CENSUS_BK")) or "")[:11]
        nbhd = text(row.get("NBRHD_CD"))
        parcels.append((pin, pin, year, r["id"], uc, nbhd, tract if len(tract) == 11 else None, zip5,
                        int(zip5) if zip5 and zip5.isdigit() else None, zip5, use_group(uc), pull_id))  # fmt: skip
        owner_addr = " ".join(
            filter(
                None,
                (text(row.get(k)) for k in ("OWN_ADDR1", "OWN_ADDR2", "OWN_CITY", "OWN_STATE", "OWN_ZIPCD")),
            )
        )
        addresses.append((pin, year, " ".join((text(row.get("PHY_ADDR1")) or "").upper().split()) or None, zip5,
                          text(row.get("OWN_NAME")), owner_addr or None, pull_id))  # fmt: skip
        living, units = integer(row.get("TOT_LVG_AREA")), integer(row.get("NO_RES_UNTS"))
        if living or units or integer(row.get("NO_BULDNG")):
            buildings.append((pin, pin, year, 1, uc, units, living, integer(row.get("LND_SQFOOT")),
                              integer(row.get("ACT_YR_BLT")) or None, pull_id))  # fmt: skip
        for n, d, price, doc, qual, multi, vacant in sales_of(row):
            sales.append(
                (f"{pin}-{d[:7]}-{n}", pin, d, price, doc, uc, nbhd, multi, qual, vacant, "month", pull_id)
            )
        values.append(
            (pin, pin, year, uc, nbhd, "final", num(row.get("JV")), num(row.get("LND_VAL")), pull_id)
        )
    upsert(conn, "parcel", ["pin", "pin10", "tax_year", "municipality_id", "class", "nbhd_code", "tract_geoid", "zip",
                            "community_area_num", "community_area_name", "use_group", "source_pull_id"], "pin", parcels)  # fmt: skip
    upsert(conn, "parcel_address", ["pin", "tax_year", "address", "zip", "owner_name", "owner_address",
                                    "source_pull_id"], "pin", addresses)  # fmt: skip
    upsert(conn, "building_char", ["row_id", "pin", "tax_year", "card", "class", "apartments", "building_sqft",
                                   "land_sqft", "year_built", "source_pull_id"], "row_id", buildings)  # fmt: skip
    upsert(conn, "sale", ["row_id", "pin", "sale_date", "sale_price", "doc_no", "class", "nbhd_code", "is_multisale",
                          "qualification", "vacant_at_sale", "date_precision", "source_pull_id"], "row_id", sales)  # fmt: skip
    upsert(conn, "assessed_value", ["pin", "pin10", "tax_year", "class", "nbhd", "stage", "market_value",
                                    "land_market_value", "source_pull_id"], "pin, tax_year", values)  # fmt: skip
    return len(parcels)


SHAPE_COLUMNS = ["pin10", "vintage", "the_geom", "source_pull_id"]


def shape_rows(shp_path: Path, wanted: set[str], vintage: int, pull_id: int) -> Iterator[tuple]:
    import shapefile  # pyshp

    with shapefile.Reader(str(shp_path)) as sf:
        field = next(f[0] for f in sf.fields[1:] if f[0].upper() in ("PARCELNO", "PARCEL_ID", "PARCELID"))
        seen: dict[str, dict] = {}
        for sr in sf.iterShapeRecords():
            pin = text(sr.record[field])
            if not pin or pin not in wanted or not sr.shape.points:
                continue
            g = sr.shape.__geo_interface__
            polys = [g["coordinates"]] if g["type"] == "Polygon" else list(g["coordinates"])
            seen.setdefault(pin, {"type": "MultiPolygon", "coordinates": []})["coordinates"].extend(polys)
        for pin, geom in seen.items():
            yield (pin, vintage, json.dumps(geom), pull_id)


def load_shapes(conn, shp_path: Path, epsg: int, vintage: int, pull_id: int) -> int:
    wanted = {r[0] for r in conn.execute("select pin from parcel where source_pull_id is not null")}
    geom = {"geom": "st_multi(st_collectionextract(st_makevalid(st_transform(st_setsrid("
                    f"st_geomfromgeojson(the_geom), {int(epsg)}), 4326)), 3))"}  # fmt: skip
    n = upsert(
        conn, "parcel_shape", SHAPE_COLUMNS, "pin10", shape_rows(shp_path, wanted, vintage, pull_id), geom
    )
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
    return n


def run(
    nal: str | None = None, shapes: str | None = None, limit: int | None = None, url: str | None = None
) -> dict:
    r = region.current()
    roll = r.get("roll", "2026F")
    out = {"parcels": 0, "shapes": 0}
    with connect(url) as conn:
        region.ensure_rows(conn)
        for county in r["counties"]:
            nal_path = Path(nal) if nal else next(fetch(nal_url(county, roll)).glob("*.csv"))
            pull_id = start_pull(
                conn, HOST, f"NAL {roll} {county['dor_name']}", ",".join(county.get("tax_auth_codes") or [])
            )
            conn.commit()
            try:
                n = load_nal(conn, nal_path, county, pull_id, limit)
                finish_pull(conn, pull_id, n)
                conn.commit()
                out["parcels"] += n
                shp = Path(shapes) if shapes else next(fetch(shapes_url(county, roll)).glob("*.shp"))
                shape_pull = start_pull(conn, HOST, f"parcel map {roll} {county['dor_name']}")
                n = load_shapes(conn, shp, county["shape_epsg"], int(roll[:4]), shape_pull)
                finish_pull(conn, shape_pull, n)
                conn.commit()
                out["shapes"] += n
            except Exception as e:
                conn.rollback()
                finish_pull(conn, pull_id, out["parcels"], "failed", str(e)[:500])
                conn.commit()
                raise
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--nal", help="a NAL csv already on disk")
    ap.add_argument("--shapes", help="a parcel .shp already on disk")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    print(run(a.nal, a.shapes, a.limit))
