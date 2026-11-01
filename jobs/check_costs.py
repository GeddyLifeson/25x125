"""Step 3 acceptance checks for cost (docs/v1-spec.md, Acceptance).

1. A standard 3-flat (25 x 125 ft RT-4 lot, production preset, area adjustment 1.0, $60,000 land) has a cost range whose low and high
   per unit cover the city's Missing Middle per-unit budgets, $308,000-365,000.
2. Market check: at each test building's actual sale price and $60,000 of land, at least 60% show a profit of
   $0 or more, with each building costed at its area's index and preset. Costs are moved back to each building's
   build midpoint (halfway from permit to first sale) with the Census under-construction index the presets
   escalate with, and sized at the building's Assessor square feet where the Assessor has it (else the pattern
   size). Also prints each building's break-even production cost per sq ft at the presets' base month.
Run: python -m jobs.check_costs
"""

import copy
import csv
import json
import statistics
from datetime import date
from pathlib import Path

from core.db import connect
from engine.costs import cost
from engine.rules import Rules
from jobs.check_test_parcels import run as resolve_test_parcels

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads((ROOT / "data" / "rules" / "feasibility_defaults.json").read_text())
MISSING_MIDDLE = (308_000, 365_000)


def midpoint(permit: str, sale: str) -> str:
    """Build midpoint month, halfway from permit to first sale: ('2023-01-01', '2024-01-01') -> '2023-07'."""
    a, b = date.fromisoformat(permit), date.fromisoformat(sale)
    return (a + (b - a) / 2).strftime("%Y-%m")


def building_sqft(conn, pin10: str) -> float | None:
    """Assessor building sq ft for the lot, or the sum of its condo units."""
    row = conn.execute(
        "select sum(building_sqft) from building_char where left(pin, 10) = %s"
        " and tax_year = (select max(tax_year) from building_char)",
        (pin10,),
    ).fetchone()
    if not row[0]:
        row = conn.execute(
            "select sum(unit_sqft) from condo_char where pin10 = %s and tax_year = (select max(tax_year) from condo_char)",
            (pin10,),
        ).fetchone()
    return float(row[0]) if row[0] else None


def sized(d: dict, units: int, sqft: float) -> dict:
    """Defaults with the unit size set so gross floor area equals the building's actual sq ft."""
    out = copy.deepcopy(d)
    per = sqft / units / d["circulation_factor"]
    out["unit_size_sqft"] = {"2": per, "3": per, "4-6": per}
    return out


def break_even(d: dict, units: int, sale: float, esc: float, lot_sqft, far) -> int:
    """Production base cost per sq ft (at the presets' base month) at which profit is $0 with $60,000 of land."""

    def total(base: float) -> float:
        dd = copy.deepcopy(d)
        dd["build_spec_presets"]["production"] = {"2-3": base, "4-6": base}
        return cost(dd, units, 60_000, 1.0, lot_sqft, far, preset="production", escalation=esc).total

    t0, t1 = total(100), total(200)
    return round(100 + 100 * (sale * d["sell"]["net_sale_factor"] - t0) / (t1 - t0))


def main() -> int:
    c = cost(DEFAULTS, 3, 60_000, lot_sqft=3125, far=1.2, preset="production")  # 25 x 125 RT-4 lot
    lo, hi = c.low / 3, c.high / 3
    ok1 = lo <= MISSING_MIDDLE[0] and hi >= MISSING_MIDDLE[1]
    print(f"standard 3-flat: ${c.total / 3:,.0f} per unit (${lo:,.0f} to ${hi:,.0f});"
          f" Missing Middle ${MISSING_MIDDLE[0]:,}-{MISSING_MIDDLE[1]:,}: {'covered' if ok1 else 'NOT covered'}")  # fmt: skip

    lots = {r["addr"]: r for r in resolve_test_parcels()}
    with connect() as conn:
        rules = Rules.from_db(conn)
        index = {
            name.upper(): (float(i), thin)
            for name, i, thin in conn.execute("select community_area, index, thin from cost_index").fetchall()
        }
        uc = dict(conn.execute(
            "select to_char(month, 'YYYY-MM'), value::float from cost_escalation_index where series = 'census_uc'"
        ).fetchall())  # fmt: skip
        sizes = {r["pin10"]: building_sqft(conn, r["pin10"]) for r in lots.values() if r.get("pin10")}
    base = DEFAULTS["build_spec_presets"]["escalation"]["base_value"]
    rows, wins, breakeven = [], 0, []
    for t in csv.DictReader((ROOT / "data" / "reference" / "test_parcels.csv").open()):
        units, sale = int(t["units"]), float(t["sale_total"])
        idx, thin = index.get(t["area"].upper(), (None, False))
        lot = lots.get(t["addr"], {})
        d = rules.district_for(lot.get("zone"))
        mid = midpoint(t["permit_date"], t["first_sale"])
        esc = uc[mid] / base if mid in uc else 1.0
        sqft = sizes.get(lot.get("pin10"))
        spec = sized(DEFAULTS, units, sqft) if sqft else DEFAULTS
        lot_sqft, far = (None, None) if sqft else (float(lot["lot_sqft"]) if lot.get("lot_sqft") else None,
                                                    d.far if d else None)  # fmt: skip
        c = cost(spec, units, 60_000, idx, lot_sqft, far, thin_index=thin, escalation=esc)
        profit = sale * DEFAULTS["sell"]["net_sale_factor"] - c.total
        wins += profit >= 0
        be = break_even(spec, units, sale, esc, lot_sqft, far)
        breakeven.append(be)
        rows.append(
            (t["addr"], t["area"], units, c.preset, idx, sale, c.total, profit, mid, round(c.gfa_sqft), be)
        )
    for r in rows:
        idx = f"{r[4]:.2f}" if r[4] is not None else "-"
        print(f"  {r[0]:24} {r[1]:20} {r[2]}u {r[3]:10} idx {idx:>5}  built {r[8]}  {r[9]:>5,} sf"
              f"  sale ${r[5]:>10,.0f}  cost ${r[6]:>10,.0f}  profit ${r[7]:>10,.0f}  break-even ${r[10]:>4}/sf")  # fmt: skip
    print(f"break-even production cost per sq ft: median ${statistics.median(breakeven):,.0f},"
          f" 25th percentile ${sorted(breakeven)[len(breakeven) // 4]:,.0f}")  # fmt: skip
    share = wins / len(rows)
    print(
        f"profit $0 or more at actual sale and $60,000 land: {wins} of {len(rows)} ({share:.0%}); target 60%"
    )
    return 0 if ok1 and share >= 0.6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
