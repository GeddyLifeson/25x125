import io

import psycopg

from db.migrate import migrate
from jobs import load_foreclosure_auctions as fa


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def table(header: list[str], rows: list[list[str]]) -> str:
    cells = lambda tag, r: "<tr>" + "".join(f"<{tag}>\n {c} </{tag}>" for c in r) + "</tr>"
    return f"<table><thead>{cells('th', header)}</thead><tbody>{''.join(cells('td', r) for r in rows)}</tbody></table>"


TJSC_HEADER = ["Sale Date", "Sale Time", "File Number", "Case Number", "Firm Name", "Address", "City", "County",
               "Zip Code", "Opening Bid", "Required % Down", "Sale Amount", "Continuance", "Sold To"]  # fmt: skip
SHERIFF_HEADER = ["CaseNumber", "FirmName", "Sheriff Number", "Property Address", "PropertyCity",
                  "PropertyZip Code", "Opening Bid", "SaleDate", "Case Status", "Closed Date", "Sold To", "Final Bid"]  # fmt: skip


def pages(upcoming_city: str) -> dict[str, str]:
    up = table(TJSC_HEADER, [
        ["11/2/2026", "10:30 AM", "46-1", "25 CH 1", "CODILIS", "4924 W. Potomac Ave., Unit 2", upcoming_city, "Cook",
         "60651", "$208,668.81", "25", "$0.00", "", ""],
        ["11/2/2026", "9:00 AM", "46-2", "25 FC 2", "NEVEL", "316 S. 16TH ST.", "BELLEVILLE", "St. Clair", "62220",
         "$60,676.42", "25", "$0.00", "", ""],
    ])  # fmt: skip
    sheriff = table(SHERIFF_HEADER, [
        ["2024CH07816", "", "260033_001F", "3935 WEST GLADYS AVENUE", "CHICAGO", "60624", "$400,000.00",
         "10/6/2026", "Completed", "", "", "$405,000.00"],
    ])  # fmt: skip
    return {
        "UpcomingSales": up,
        "CompletedSales": "<p>none</p>",
        "CancelledSales": "",
        "page=1": sheriff,
        "page=2": "",
    }


def opener_for(html: dict[str, str]):
    def opener(req, timeout):
        return FakeResponse(next(v for k, v in html.items() if req.full_url.endswith(k)).encode())

    return opener


def test_parses_lists_and_cleans_addresses():
    recs = fa.records(pages("CHICAGO")["UpcomingSales"])
    assert len(recs) == 2 and recs[0]["filenumber"] == "46-1"
    assert fa.clean_address("4924 W. Potomac Ave., Unit 2") == "4924 W POTOMAC AVE"
    assert fa.clean_address("3935 WEST GLADYS AVENUE") == "3935 W GLADYS AVE"
    row = fa.tjsc_row(recs[0], "upcoming", 1)
    assert row[1:6] == ("tjsc:46-1", "2026-11-02", "upcoming", "25 CH 1", "4924 W POTOMAC AVE")
    assert fa.tjsc_row(recs[1], "upcoming", 1) is None  # not Cook County


def test_rows_are_kept_between_runs(db_url):
    migrate(db_url)
    assert fa.run(opener=opener_for(pages("CHICAGO")), url=db_url, sheriff_pages=5) == 2
    # Next run: the TJSC sale has dropped off the list; its row stays.
    assert fa.run(opener=opener_for(pages("BERWYN")), url=db_url, sheriff_pages=5) == 1
    with psycopg.connect(db_url) as conn:
        rows = conn.execute(
            "select source_id, status, (attrs->>'sale_amount')::numeric from parcel_signal"
            " where kind = 'foreclosure_auction' order by 1"
        ).fetchall()
    assert [(s, st, a and float(a)) for s, st, a in rows] == [
        ("sheriff:260033_001F", "completed", 405000.0),
        ("tjsc:46-1", "upcoming", None),
    ]
