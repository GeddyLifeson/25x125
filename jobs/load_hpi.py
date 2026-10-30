"""Load FHFA house price indexes for Illinois: annual by census tract and five-digit ZIP, quarterly by metro
division. Comp prices move to the estimate date with the tract index, then ZIP, then metro (the first with
values for both years). FHFA indexes are public domain and can be shown on screen.

Files: https://www.fhfa.gov/data/hpi/datasets (the ZIP5 file is an Excel workbook despite its .csv name).
Each run replaces the table. Run: python -m jobs.load_hpi
"""

import csv
import io
import tempfile
import urllib.request
from collections.abc import Callable, Iterator

from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import num, upsert

HOST = "www.fhfa.gov"
BASE = "https://www.fhfa.gov/hpi/download/"
FILES = {
    "tract": "annually/hpi_at_tract.csv",
    "zip": "annually/hpi_at_zip5.csv",
    "metro": "quarterly_datasets/hpi_at_metro.csv",
}
COLUMNS = ["geo_kind", "geo_id", "year", "quarter", "hpi", "source_pull_id"]


def tract_rows(fh: io.TextIOBase) -> Iterator[tuple]:
    for r in csv.DictReader(fh):
        if r["tract"].startswith("17") and (v := num(r["hpi"])):
            yield "tract", r["tract"], int(r["year"]), 0, v


def zip_rows(path: str) -> Iterator[tuple]:
    import openpyxl

    ws = openpyxl.load_workbook(path, read_only=True).active
    for r in ws.iter_rows(min_row=7, values_only=True):
        z, year, _, hpi = r[:4]
        # Illinois ZIP codes run 60001-62999.
        if z and str(z)[:2] in ("60", "61", "62") and isinstance(hpi, int | float):
            yield "zip", str(z), int(year), 0, float(hpi)


def metro_rows(fh: io.TextIOBase) -> Iterator[tuple]:
    for r in csv.reader(fh):
        if len(r) >= 5 and ", IL" in r[0] and (v := num(r[4].replace("-", ""))):
            yield "metro", r[1], int(r[2]), int(r[3]), v


def run(opener: Callable = urllib.request.urlopen, url: str | None = None) -> int:
    total = 0
    with connect(url) as conn:
        conn.execute("truncate hpi")
        for kind, path in FILES.items():
            pull_id = start_pull(conn, HOST, path)
            conn.commit()
            try:
                with opener(BASE + path, timeout=300) as resp:
                    if kind == "zip":
                        with tempfile.NamedTemporaryFile(suffix=".xlsx") as tmp:
                            tmp.write(resp.read())
                            tmp.flush()
                            rows = list(zip_rows(tmp.name))
                    else:
                        fh = io.TextIOWrapper(resp, encoding="utf-8", errors="replace")
                        rows = list(tract_rows(fh) if kind == "tract" else metro_rows(fh))
                n = upsert(
                    conn, "hpi", COLUMNS, "geo_kind, geo_id, year, quarter", (r + (pull_id,) for r in rows)
                )
                finish_pull(conn, pull_id, n)
                conn.commit()
                total += n
            except Exception as e:
                conn.rollback()
                finish_pull(conn, pull_id, total, "failed", str(e)[:500])
                conn.commit()
                raise
    return total


if __name__ == "__main__":
    print(f"index rows: {run():,}")
