import io
import json

import psycopg

from db.migrate import migrate
from jobs import load_rezonings
from jobs.load_rezonings import parse_title


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_title_gives_map_address_and_application():
    p = parse_title("Zoning Reclassification Map No. 7-L at 2900-2912 N Cicero Ave - App  No. 17079T1")
    assert (p["map_no"], p["app_no"], p["type1"], p["address"]) == (
        "7-L",
        "17079T1",
        True,
        "2900 N CICERO AVE",
    )
    p = parse_title(
        "Zoning Reclassification Map Nos. 16-C and 18-C at 2132-2238 E 71st St and 2135 E 71st St - A-9115"
    )
    assert (p["map_no"], p["alderman_filed"], p["addresses"]) == (
        "16-C, 18-C",
        True,
        "2132-2238 E 71st St; 2135 E 71st St",
    )
    assert parse_title("Zoning Reclassificationat App No. 17148 at 2144-2146 N Leavitt St - Map No. 5-H")[
        "address"
    ] == ("2144 N LEAVITT ST")


def test_load_pages_through_search_and_keeps_rezonings_only(db_url):
    migrate(db_url)
    matter = {"matterId": "M1", "recordNumber": "O2026-1", "title": "Zoning Reclassification Map No. 93-B at 1828 W Race Ave - App No. 23178T1",
              "introductionDate": "2026-10-14T15:00:00+00:00", "finalActionDate": None, "status": "4-In Committee",
              "subStatus": "Referred"}  # fmt: skip
    other = {**matter, "matterId": "M2", "recordNumber": "O2026-2", "title": "Appointment of Jane Doe to ZBA"}
    pages = [{"data": [matter], "meta": {"count": 2}}, {"data": [other], "meta": {"count": 2}}]
    seen = []

    def opener(req, timeout):
        seen.append(req.full_url)
        return FakeResponse(json.dumps(pages[len(seen) - 1]).encode())

    assert load_rezonings.run(opener=opener, url=db_url) == 1
    assert "skip=1" in seen[1]
    with psycopg.connect(db_url) as conn:
        assert conn.execute("select record_number, type1, intro_date::text from rezoning").fetchall() == [
            ("O2026-1", True, "2026-10-14")
        ]
        assert conn.execute("select address from parcel_signal where kind = 'rezoning'").fetchone() == (
            "1828 W RACE AVE",
        )
