"""Load public land offered for sale into lot_for_sale (step 6 map layer).

- city: City-Owned Land Inventory (aksk-kvfp), lots the city owns. ChiBlockBuilder sells from this list;
  `for_sale` is true for the statuses that take applications now.
- land_bank: Cook County Land Bank Authority public property feed (ePropertyPlus), Chicago only.
  https://public-cclba.epropertyplus.com/landmgmtpub/app/base/propertySearch

Each source is replaced on every run. Run: python -m jobs.load_lots_for_sale [--source city]
"""

import argparse
import json
import urllib.request
from collections.abc import Callable

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import num, text, upsert

CITY_DATASET = "aksk-kvfp"
CITY_OPEN = ("Apply", "Offered", "Application(s) Received", "Application Received")
LAND_BANK_HOST = "public-cclba.epropertyplus.com"
LAND_BANK_URL = (
    "https://public-cclba.epropertyplus.com/landmgmtpub/remote/public/property/getPublishedProperties"
    "?json=%7B%22criterias%22%3A%5B%5D%7D&start=0&limit=5000&page=1"
)
LAND_BANK_OPEN = ("Acquired",)  # published and not yet in rehab or sold
COLUMNS = [
    "source", "source_id", "pin", "pin10", "address", "status", "for_sale", "asking_price", "minimum_bid",
    "city_land_value", "lot_sqft", "property_type", "zoning", "deadline", "offer_round", "apply_url", "comments",
    "listed_on", "lon", "lat", "source_pull_id",
]  # fmt: skip
GEOM = {"geom": "case when lon is not null then st_setsrid(st_makepoint(lon, lat), 4326) end"}
# Tie each lot to a parcel by PIN; where the PIN is missing, use the lot under the point.
AFTER = """
update lot_for_sale l set pin10 = coalesce(l.pin10,
  (select s.pin10 from parcel_shape s where l.geom is not null and st_contains(s.geom, l.geom) limit 1))
where l.source = %s
"""


def clean_pin(v) -> str | None:
    digits = "".join(c for c in (text(v) or "") if c.isdigit())
    if len(digits) == 10:
        digits += "0000"
    return digits if len(digits) == 14 else None


def day(v) -> str | None:
    d = (text(v) or "")[:10]
    return d or None


def city_row(r: dict, pull_id: int) -> tuple | None:
    if not text(r.get("id")):
        return None
    pin = clean_pin(r.get("pin"))
    url = r.get("application_url")
    status = text(r.get("sales_status"))
    return (
        "city", text(r["id"]), pin, pin[:10] if pin else None, text(r.get("address")), status,
        status in CITY_OPEN, None, None, num(r.get("land_value")),
        num(r.get("square_footage_city_estimate")) or num(r.get("sq_ft")) or None,
        text(r.get("application_use")), text(r.get("zoning_classification")), day(r.get("application_deadline")),
        text(r.get("offer_round")), url.get("url") if isinstance(url, dict) else text(url),
        text(r.get("sale_offering_status")), day(r.get("last_listed")),
        num(r.get("longitude")), num(r.get("latitude")), pull_id,
    )  # fmt: skip


def land_bank_row(r: dict, pull_id: int) -> tuple | None:
    if (r.get("city") or "").strip().upper() != "CHICAGO" or r.get("id") is None:
        return None
    pin = clean_pin(r.get("parcelNumber"))
    status = text(r.get("currentStatus"))
    return (
        "land_bank", str(r["id"]), pin, pin[:10] if pin else None, text(r.get("propertyAddress1")), status,
        status in LAND_BANK_OPEN, num(r.get("askingPrice")), num(r.get("minimumBid")), None,
        num(r.get("parcelSquareFootage")), text(r.get("inventoryType")), None, None, None,
        "https://public-cclba.epropertyplus.com/landmgmtpub/app/base/propertySearch", text(r.get("comments")),
        None, num(r.get("longitude")), num(r.get("latitude")), pull_id,
    )  # fmt: skip


def fetch_land_bank(opener: Callable = urllib.request.urlopen) -> list[dict]:
    with opener(LAND_BANK_URL, timeout=120) as resp:
        data = json.load(resp)
    if not data.get("success"):
        raise ValueError("land bank feed returned success=false")
    return data["rows"]


def run_source(
    name: str,
    client: Socrata | None = None,
    opener: Callable = urllib.request.urlopen,
    url: str | None = None,
) -> int:
    with connect(url) as conn:
        if name == "city":
            client = client or Socrata(CHICAGO)
            where = "property_status = 'Owned by City'"
            pull_id = start_pull(conn, CHICAGO, CITY_DATASET, where)
        else:
            pull_id = start_pull(conn, LAND_BANK_HOST, LAND_BANK_URL)
        conn.commit()
        try:
            if name == "city":
                rows = [row for page in client.pages(CITY_DATASET, order="id", where=where)
                        for r in page if (row := city_row(r, pull_id))]  # fmt: skip
            else:
                rows = [row for r in fetch_land_bank(opener) if (row := land_bank_row(r, pull_id))]
            conn.execute("delete from lot_for_sale where source = %s", (name,))
            n = upsert(conn, "lot_for_sale", COLUMNS, "source, source_id", rows, GEOM)
            conn.execute(AFTER, (name,))
            finish_pull(conn, pull_id, n)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
            conn.commit()
            raise
    return n


def run(url: str | None = None) -> dict[str, int]:
    return {name: run_source(name, url=url) for name in ("city", "land_bank")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["city", "land_bank"])
    a = ap.parse_args()
    for name in [a.source] if a.source else ["city", "land_bank"]:
        print(f"{name}: {run_source(name):,}", flush=True)
