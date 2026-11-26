"""New-building rent factor for a region outside Chicago, from Census data alone.

Chicago's factor comes from the Assessor's income worksheets (jobs/check_rents.py). The other regions have no
public rent rolls, so the factor here is the ratio, tract by tract, of the ACS median gross rent of units built
2020 or later (B25111; 2010 to 2019 where fewer than 30 tracts report the newest group) to the median of all
rented units (B25064), over the tracts that hold the region's lots. Both figures are gross rents from the same
survey, so utilities cancel out.
--write saves the factor and its 10th-90th percentile range to data/regions/<id>/rules/feasibility_defaults.json.
Run: python -m jobs.check_rents_acs [--write]   (REGION set; jobs.load_tracts first)
"""

import argparse
import csv
import io
import json
import statistics as st
import urllib.request
from collections.abc import Callable
from datetime import date

from core import region
from core.db import connect
from jobs.common import num
from jobs.load_rents import ACS_URL

MIN_TRACTS = 30


def medians(fh, table: str, codes: list[str], tracts: set[str]) -> dict[str, dict[str, float]]:
    """{tract: {code: median}} for the given tracts; Census annotation codes (negative) are skipped."""
    reader = csv.reader(fh, delimiter="|")
    head = next(reader)
    out: dict[str, dict[str, float]] = {}
    for r in reader:
        if not r[0].startswith("1400000US"):
            continue
        t = r[0].split("US", 1)[1]
        if t not in tracts:
            continue
        rec = dict(zip(head, r, strict=False))
        for c in codes:
            v = num(rec.get(f"{table.upper()}_E{c}"))
            if v is not None and v > 0:
                out.setdefault(t, {})[c] = v
    return out


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, round(p * (len(xs) - 1))))]


def factor(by_year: dict, overall: dict) -> dict:
    """Units built 2020 or later set the factor when at least MIN_TRACTS tracts report them; else 2010-2019."""
    ratios = {
        c: [v[c] / overall[t]["001"] for t, v in by_year.items() if c in v and t in overall]
        for c in ("002", "003")
    }
    stats = {
        label: {"tracts": len(ratios[c]), "median": round(st.median(ratios[c]), 3) if ratios[c] else None}
        for c, label in (("002", "built_2020_or_later"), ("003", "built_2010_2019"))
    }
    code = "002" if len(ratios["002"]) >= MIN_TRACTS else "003"
    xs = ratios[code]
    if len(xs) < MIN_TRACTS:
        return {**stats, "missing": f"fewer than {MIN_TRACTS} tracts report rents of units built since 2010"}
    return {
        **stats,
        "basis": "built_2020_or_later" if code == "002" else "built_2010_2019",
        "tracts": len(xs),
        "factor": round(st.median(xs), 3),
        "range": [round(pct(xs, 0.1), 3), round(pct(xs, 0.9), 3)],
    }


def run(vintage_year: int = 2024, opener: Callable = urllib.request.urlopen, url: str | None = None) -> dict:
    with connect(url) as conn:
        tracts = {t for (t,) in conn.execute(
            "select distinct p.tract_geoid from parcel_site s join parcel p using (pin) where p.tract_geoid is not null"
        ).fetchall()}  # fmt: skip
    data = {}
    for table, codes in (("b25111", ["002", "003"]), ("b25064", ["001"])):
        with opener(ACS_URL.format(y=vintage_year, t=table), timeout=300) as resp:
            data[table] = medians(io.TextIOWrapper(resp, encoding="utf-8"), table, codes, tracts)
    out = factor(data["b25111"], data["b25064"])
    out["tracts_with_lots"] = len(tracts)
    out["vintage"] = f"{vintage_year - 4}-{vintage_year}"
    return out


def write(res: dict) -> None:
    path = region.rules_dir() / "feasibility_defaults.json"
    d = json.loads(path.read_text())
    v = res["vintage"]
    built = "2020 or later" if res["basis"] == "built_2020_or_later" else "2010-2019"
    other = res["built_2010_2019"] if res["basis"] == "built_2020_or_later" else res["built_2020_or_later"]
    other_label = "2010-2019" if res["basis"] == "built_2020_or_later" else "2020 or later"
    d["rents"] = {
        "new_construction_factor": res["factor"],
        "factor_range": res["range"],
        "range_basis": f"10th-90th percentile over {res['tracts']} tracts of ACS {v} rent of units built {built}"
                       " over all rented units",
        "evidence": f"python -m jobs.check_rents_acs: ACS {v} B25111 (median gross rent of units built {built})"
                    f" over B25064 (all rented units), median over {res['tracts']} tracts with lots in"
                    f" {region.current()['name']}. Units built {other_label}: {other['median']} over"
                    f" {other['tracts']} tracts.",
        "caveat": "Census rents include long-tenure leases and utilities; no public rent rolls outside Chicago."
                  " Replace with a rent source when one is available.",
        "verified_on": date.today().isoformat(),
    }  # fmt: skip
    path.write_text(json.dumps(d, indent=2) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    if region.is_chicago():
        raise SystemExit("Chicago's factor comes from python -m jobs.check_rents")
    res = run()
    print(json.dumps(res, indent=2))
    if a.write and "factor" in res:
        write(res)
