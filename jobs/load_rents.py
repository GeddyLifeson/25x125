"""Load rent inputs: Census ACS 5-year median gross rent by bedrooms (B25031) and overall (B25064) for
Illinois tracts and ZIP areas, from the keyless table-based summary files, and the Zillow observed rent index
(ZORI) by Illinois ZIP for growth since the ACS period.

ZORI is used only as a growth ratio inside the engine. Its values are never displayed (CLAUDE.md data rules).
Run: python -m jobs.load_rents [--vintage 2024]
"""

import argparse
import csv
import io
import urllib.request
from collections.abc import Callable, Iterator
from datetime import date

from core.db import connect
from core.sources import finish_pull, start_pull
from jobs.common import num, upsert

ACS_HOST = "www2.census.gov"
ACS_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/{y}/table-based-SF/data/5YRData/acsdt5y{y}-{t}.dat"
ZORI_HOST = "files.zillowstatic.com"
ZORI_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"
B25031 = {"001": "all", "002": "0", "003": "1", "004": "2", "005": "3", "006": "4", "007": "5+"}
PREFIX = {"1400000US17": "tract", "860Z200US6": "zcta"}  # Illinois tracts; ZCTAs 60xxx-62xxx


def acs_rows(fh, table: str, vintage: str) -> Iterator[tuple]:
    reader = csv.reader(fh, delimiter="|")
    head = next(reader)
    for r in reader:
        geo = r[0]
        kind = next((k for p, k in PREFIX.items() if geo.startswith(p)), None)
        if not kind:
            continue
        geo_id = geo.split("US", 1)[1]
        if kind == "zcta" and geo_id[:2] not in ("60", "61", "62"):
            continue
        rec = dict(zip(head, r, strict=False))
        codes = B25031 if table == "b25031" else {"001": "all"}
        for code, beds in codes.items():
            if table == "b25064" or code != "001":
                e = num(rec.get(f"{table.upper()}_E{code}"))
                m = num(rec.get(f"{table.upper()}_M{code}"))
                if e is not None and e > 0:  # negative values are Census annotation codes
                    yield kind, geo_id, vintage, beds, e, m if m and m > 0 else None


def zori_rows(fh) -> Iterator[tuple]:
    reader = csv.DictReader(fh)
    for r in reader:
        if r.get("State") != "IL":
            continue
        for k, v in r.items():
            if k[:2] == "20" and len(k) == 10 and (x := num(v)):
                yield r["RegionName"].zfill(5), date.fromisoformat(k).replace(day=1), x


def run(vintage_year: int = 2024, opener: Callable = urllib.request.urlopen, url: str | None = None) -> dict:
    vintage = f"{vintage_year - 4}-{vintage_year}"
    out = {}
    with connect(url) as conn:
        for table in ("b25031", "b25064"):
            src = ACS_URL.format(y=vintage_year, t=table)
            pull_id = start_pull(conn, ACS_HOST, src)
            conn.commit()
            try:
                with opener(src, timeout=300) as resp:
                    rows = list(acs_rows(io.TextIOWrapper(resp, encoding="utf-8"), table, vintage))
                n = upsert(conn, "acs_rent", ["geo_kind", "geo_id", "vintage", "bedrooms", "median_rent", "moe",
                           "source_pull_id"], "geo_kind, geo_id, vintage, bedrooms",
                           (r + (pull_id,) for r in rows))  # fmt: skip
                finish_pull(conn, pull_id, n)
                conn.commit()
                out[table] = n
            except Exception as e:
                conn.rollback()
                finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
                conn.commit()
                raise
        pull_id = start_pull(conn, ZORI_HOST, ZORI_URL)
        conn.commit()
        try:
            with opener(ZORI_URL, timeout=300) as resp:
                rows = list(zori_rows(io.TextIOWrapper(resp, encoding="utf-8")))
            conn.execute("truncate zori_growth")
            n = upsert(conn, "zori_growth", ["zip", "month", "zori", "source_pull_id"], "zip, month",
                       (r + (pull_id,) for r in rows))  # fmt: skip
            finish_pull(conn, pull_id, n)
            out["zori"] = n
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, 0, "failed", str(e)[:500])
            conn.commit()
            raise
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vintage", type=int, default=2024, help="last year of the ACS 5-year period")
    print(run(ap.parse_args().vintage))
