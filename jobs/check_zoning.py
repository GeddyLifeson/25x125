"""Step 2 acceptance check: for each test building, the units built fit a zoning path on its lot, and each
hand-checked parcel (data/reference/hand_check_parcels.csv) gives the expected path or flag.

Takes each test parcel's lot from jobs.check_test_parcels, runs the rules engine on it, and reports the
smallest-approval path that allows the units built. A building that fits no path is a miss to explain
(often a lot rezoned for the project after the fact, or a lot later divided into condo PINs).
Run: python -m jobs.check_zoning
"""

import csv
from pathlib import Path

from core.db import connect
from engine.rules import Rules
from engine.sites import site_by_pin
from engine.zoning import evaluate
from jobs import check_test_parcels

# Fewest approvals first: the path a builder would most likely have used.
ORDER = ["by_right", "rs3_two_flat", "admin_adjustment", "adu", "tsl_bonus_50", "tsl_bonus_75", "tsl_bonus_100",
         "rezoning"]  # fmt: skip


HAND_CHECK = Path(__file__).resolve().parents[1] / "data" / "reference" / "hand_check_parcels.csv"
PIN_BY_ADDRESS = "select left(pin, 10) from parcel_address where address = %s order by pin limit 1"


def fitting_path(res, units: int) -> str | None:
    paths = {p.id: p for p in res.paths}
    return next((pid for pid in ORDER if pid in paths and paths[pid].units >= units), None)


def check(expect: str, res, units: int | None) -> bool:
    kind, _, what = expect.partition(":")
    flags = {f.id for f in res.flags}
    if kind == "path":
        return units is not None and fitting_path(res, units) == what
    if kind == "fits":
        return units is not None and fitting_path(res, units) is not None
    if kind == "flag":
        return what in flags
    if kind == "no_flag":
        return what not in flags
    return False


def run_hand_check(url: str | None = None) -> list[dict]:
    out = []
    with connect(url) as conn:
        rules = Rules.from_db(conn)
        for t in csv.DictReader(HAND_CHECK.open()):
            if not t["expect"]:
                continue
            pin = t["pin"] or (conn.execute(PIN_BY_ADDRESS, (t["address"],)).fetchone() or [None])[0]
            site = site_by_pin(conn, pin) if pin else None
            units = int(t["units_built"]) if t["units_built"] else None
            r = {"addr": t["address"], "zoning_file": t["zoning_now"], "expect": t["expect"], "units": units}
            if site:
                res = evaluate(site, rules)
                r.update(zone=site.zone_class, path=fitting_path(res, units) if units else None,
                         flags=sorted(f.id for f in res.flags), ok=check(t["expect"], res, units))  # fmt: skip
            else:
                r.update(zone=None, path=None, flags=[], ok=False)
            out.append(r)
    return out


def run(url: str | None = None) -> list[dict]:
    out = []
    parcels = check_test_parcels.run(url)
    with connect(url) as conn:
        rules = Rules.from_db(conn)
        for t in parcels:
            r = {
                "addr": t["addr"],
                "units": int(t["units"]),
                "zone": t.get("zone"),
                "path": None,
                "by_right": None,
            }
            site = site_by_pin(conn, t["pin10"]) if t.get("pin10") else None
            if site:
                res = evaluate(site, rules)
                paths = {p.id: p for p in res.paths}
                r["by_right"] = paths["by_right"].units if "by_right" in paths else None
                r["lot_sqft"] = site.lot_sqft
                for pid in ORDER:
                    if pid in paths and paths[pid].units >= r["units"]:
                        r["path"] = pid
                        break
            out.append(r)
    return out


if __name__ == "__main__":
    results = run()
    for r in results:
        print(f"{'ok  ' if r['path'] else 'MISS'} {r['addr']:<24} {r['zone'] or '-':<7} lot {r.get('lot_sqft') or 0:>6.0f}"
              f"  built {r['units']}  by right {r['by_right']}  path {r['path'] or '-'}")  # fmt: skip
    fit = [r for r in results if r["path"]]
    by_right = [r for r in results if r["path"] == "by_right"]
    print(f"{len(fit)} of {len(results)} fit a path; {len(by_right)} by right")
    print()
    hand = run_hand_check()
    for r in hand:
        print(f"{'ok  ' if r['ok'] else 'MISS'} {r['addr']:<24} {r['zone'] or '-':<7} (file {r['zoning_file']:<6})"
              f" built {r['units'] or '-'}  path {r['path'] or '-':<16} expect {r['expect']:<22} flags {', '.join(r['flags'])}")  # fmt: skip
    print(f"hand-checked: {sum(r['ok'] for r in hand)} of {len(hand)} as expected")
