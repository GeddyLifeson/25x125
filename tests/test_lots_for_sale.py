import io
import json

import psycopg

from db.migrate import migrate
from jobs import load_lots_for_sale
from jobs.load_lots_for_sale import city_row, clean_pin, land_bank_row
from tests.test_loaders import FakeClient


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


CITY = {"id": "8638", "pin": "16-09-424-002-0000", "address": "4853 W WEST END AVE", "sales_status": "Apply",
        "land_value": "17989", "square_footage_city_estimate": "4497", "zoning_classification": "RT-4",
        "application_deadline": "2025-11-17T00:00:00.000", "offer_round": "Q4 2025",
        "application_url": {"url": "https://example.org/apply"}, "last_listed": "2025-10-01T00:00:00.000",
        "latitude": "41.8827", "longitude": "-87.7474"}  # fmt: skip
LAND_BANK = {"id": 88996, "parcelNumber": "20-18-217-023-0000", "city": "CHICAGO               ",
             "currentStatus": "Acquired", "propertyAddress1": "5706 S Wolcott Ave ", "askingPrice": 14500.0,
             "minimumBid": 4500.0, "parcelSquareFootage": 3720.0, "inventoryType": "Vacant Land",
             "latitude": 41.79, "longitude": -87.672}  # fmt: skip


def test_rows_clean_pins_and_flag_open_lots():
    assert clean_pin("16-09-424-002") == "16094240020000"
    c = city_row(CITY, 1)
    assert c[2:8] == ("16094240020000", "1609424002", "4853 W WEST END AVE", "Apply", True, None)
    assert c[13:16] == ("2025-11-17", "Q4 2025", "https://example.org/apply")
    assert city_row({**CITY, "sales_status": "Application Closed"}, 1)[6] is False
    lb = land_bank_row(LAND_BANK, 1)
    assert lb[2:9] == (
        "20182170230000",
        "2018217023",
        "5706 S Wolcott Ave",
        "Acquired",
        True,
        14500.0,
        4500.0,
    )
    assert land_bank_row({**LAND_BANK, "city": "MAYWOOD"}, 1) is None


def test_load_replaces_each_source(db_url):
    migrate(db_url)
    assert load_lots_for_sale.run_source("city", client=FakeClient([[CITY]]), url=db_url) == 1
    feed = json.dumps(
        {"success": True, "rows": [LAND_BANK, {**LAND_BANK, "id": 2, "city": "CICERO"}]}
    ).encode()
    opener = lambda u, timeout: FakeResponse(feed)
    assert load_lots_for_sale.run_source("land_bank", opener=opener, url=db_url) == 1
    assert load_lots_for_sale.run_source("land_bank", opener=opener, url=db_url) == 1
    with psycopg.connect(db_url) as conn:
        rows = conn.execute(
            "select source, for_sale, st_x(geom)::numeric(8,3) from lot_for_sale order by source"
        ).fetchall()
    assert [(s, f, float(x)) for s, f, x in rows] == [("city", True, -87.747), ("land_bank", True, -87.672)]
