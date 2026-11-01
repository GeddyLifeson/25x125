"""Load the monthly price indexes that escalate cost presets (decision 23).

- census_uc: Census price index of new single-family houses under construction, constant quality (Laspeyres),
  monthly since 1964. https://www.census.gov/construction/nrs/xls/price_uc_cust.xlsx
- ppi_resi_inputs: BLS PPI net inputs to residential construction, goods, via FRED (no key needed).
  https://fred.stlouisfed.org/series/WPUIP2311001

Presets carry a base month (`build_spec_presets.escalation` in feasibility_defaults.json). The engine scales a
preset by latest / base, then by the trailing 12-month change over half the build period (the build midpoint).
Each run replaces both series. Run: python -m jobs.load_cost_escalation
"""

import csv
import io
import tempfile
import urllib.request
from collections.abc import Callable, Iterator
from datetime import date, datetime

from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import num, upsert

COLUMNS = ["series", "month", "value", "status", "source_pull_id"]
# Census refuses Python's default user agent; name the loader instead.
USER_AGENT = "25x125-data-loader/1.0 (+https://github.com/GeddyLifeson/25x125)"
SOURCES = {
    "census_uc": ("www.census.gov", "https://www.census.gov/construction/nrs/xls/price_uc_cust.xlsx"),
    "ppi_resi_inputs": (
        "fred.stlouisfed.org",
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WPUIP2311001",
    ),
}


def census_rows(path: str) -> Iterator[tuple]:
    """Sheet 'Vertical': month, status flag, Laspeyres (fixed) index, Fisher deflator."""
    import openpyxl

    ws = openpyxl.load_workbook(path, read_only=True)["Vertical"]
    for r in ws.iter_rows(values_only=True):
        if isinstance(r[0], datetime) and isinstance(r[2], int | float):
            yield "census_uc", r[0].date().replace(day=1), float(r[2]), (r[1] or "").strip() or None


def fred_rows(fh: io.TextIOBase) -> Iterator[tuple]:
    for r in csv.DictReader(fh):
        if r.get("WPUIP2311001") not in (None, "", ".") and (v := num(r["WPUIP2311001"])) is not None:
            yield "ppi_resi_inputs", date.fromisoformat(r["observation_date"]).replace(day=1), v, None


def run(opener: Callable = urllib.request.urlopen, url: str | None = None) -> dict[str, int]:
    counts = {}
    with connect(url) as conn:
        for series, (host, src) in SOURCES.items():
            pull_id = start_pull(conn, host, src)
            conn.commit()
            try:
                with opener(
                    urllib.request.Request(src, headers={"User-Agent": USER_AGENT}), timeout=120
                ) as resp:
                    if series == "census_uc":
                        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
                            tmp.write(resp.read())
                            tmp.flush()
                            rows = list(census_rows(tmp.name))
                    else:
                        rows = list(fred_rows(io.TextIOWrapper(resp, encoding="utf-8")))
                if not rows:
                    raise ValueError(f"{series}: no rows parsed")
                conn.execute("delete from cost_escalation_index where series = %s", (series,))
                n = upsert(
                    conn, "cost_escalation_index", COLUMNS, "series, month", (r + (pull_id,) for r in rows)
                )
                finish_pull(conn, pull_id, n)
                conn.commit()
                counts[series] = n
            except Exception as e:
                conn.rollback()
                finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
                conn.commit()
                raise
    return counts


if __name__ == "__main__":
    for k, v in run().items():
        print(f"{k}: {v:,} months")
