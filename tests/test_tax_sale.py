import psycopg
import pytest

from db.migrate import migrate
from jobs import load_tax_sale
from jobs.load_tax_sale import ParseError, index, long_date, rows_from_report

LINE = (
    "MARIA SANCHEZ             2744 N SACRAMENTO AVE       2744 N SACRAMENTO AVE CHICAGO IL 606471716     529"
    "     13-25-303-023-0000     00        2023              $13,346.78            $14,925.59 WEST          Chicago"
    "        Residential                1             8            39            20                     Yes"
)
REPORT = (
    "Properties Currently Eligible for 2023 Annual Tax Sale in Ward 1\nTotal Delinquent PINs: 1\n"
    "Total amount due, including late interest, through Tuesday, December 1, 2026.\n\n" + LINE + "\n"
)
PAGE = (
    "<p>the Tax Year 2023 Annual Tax Sale that is scheduled for December 15, 2026.</p>"
    "<a href='https://reportingservices.cookcountytreasurer.com/x.aspx?type=A=&amp;id=1' target='_blank'>Ward 1</a>"
    "<a href='https://reportingservices.cookcountytreasurer.com/x.aspx?type=A=&amp;id=2' target='_blank'>Ward 2</a>"
)


def test_report_rows_drop_owner_and_check_the_total():
    rows, through = rows_from_report(REPORT)
    assert through == "2026-12-01"
    assert rows == [{
        "pin": "13253030230000", "pin10": "1325303023", "ward": 1, "property_address": "2744 N SACRAMENTO AVE",
        "volume": "529", "tax_type": "00", "tax_year": 2023, "total_tax_due": 13346.78, "total_due": 14925.59,
        "classification": "Residential",
    }]  # fmt: skip
    assert "MARIA" not in str(rows)
    with pytest.raises(ParseError):
        rows_from_report(REPORT.replace("PINs: 1", "PINs: 2"))


def test_index_reads_sale_date_and_ward_links():
    sale, wards = index(PAGE)
    assert sale == "2026-12-15" and long_date("March 3, 2027") == "2027-03-03"
    assert wards[1].endswith("type=A=&id=1") and len(wards) == 2


def test_run_replaces_the_sale_and_keeps_no_owner_fields(db_url, monkeypatch):
    migrate(db_url)
    page = PAGE + "".join(
        f"<a href='https://reportingservices.cookcountytreasurer.com/x.aspx?id={w}' target='_blank'>Ward {w}</a>"
        for w in range(3, 51)
    )
    monkeypatch.setattr(
        load_tax_sale, "fetch", lambda url, opener=None: page.encode() if "delinquent" in url else b""
    )
    monkeypatch.setattr(load_tax_sale, "pdf_text", lambda data: REPORT)
    monkeypatch.setattr(load_tax_sale, "INDEX", "https://www.cookcountytreasurer.com/delinquenttaxes.aspx")
    # every ward returns the same PIN; the key keeps one row
    assert load_tax_sale.run(db_url, pause=0) == 50
    assert load_tax_sale.run(db_url, pause=0) == 50
    with psycopg.connect(db_url) as conn:
        assert conn.execute("select count(*), max(sale_date)::text from tax_sale_list").fetchone() == (
            1,
            "2026-12-15",
        )
        cols = {r[0] for r in conn.execute(
            "select column_name from information_schema.columns where table_name = 'tax_sale_list'"
        )}  # fmt: skip
    assert not cols & {"taxpayer", "owner", "owner_name", "mailing_address"}
