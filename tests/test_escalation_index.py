import io
from datetime import date

import openpyxl
import psycopg

from db.migrate import migrate
from jobs import load_cost_escalation


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def census_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Vertical"
    ws.append(["Price Indexes of New Single-Family Houses Under Construction"])
    ws.append(["Month", None, "Laspeyres\n (Fixed)", "Fisher\n (Deflator)"])
    ws.append([date(2025, 9, 1), None, 197.5, 195.0])
    ws.append([date(2026, 9, 1), "p", 200.7, 198.3])
    ws.append(["Source:  U.S. Census Bureau"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_loads_both_series_and_reports_the_12_month_change(db_url):
    migrate(db_url)
    fred = b"observation_date,WPUIP2311001\n2025-09-01,323.904\n2026-09-01,355.225\n2026-10-01,.\n"

    def opener(req, timeout):
        return FakeResponse(census_xlsx() if "census" in req.full_url else fred)

    assert load_cost_escalation.run(opener=opener, url=db_url) == {"census_uc": 2, "ppi_resi_inputs": 2}
    with psycopg.connect(db_url) as conn:
        rows = conn.execute(
            "select series, latest_month::text, status, change_12m from cost_escalation order by 1"
        ).fetchall()
    assert [(s, m, st, float(c)) for s, m, st, c in rows] == [
        ("census_uc", "2026-09-01", "p", 0.0162),
        ("ppi_resi_inputs", "2026-09-01", None, 0.0967),
    ]
