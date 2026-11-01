"""Step 3 acceptance checks for cost (docs/v1-spec.md, Acceptance).

1. A standard 3-flat (25 x 125 ft RT-4 lot, production preset, area adjustment 1.0, $60,000 land) has a cost range whose low and high
   per unit cover the city's Missing Middle per-unit budgets, $308,000-365,000.
2. Market check: at each test building's actual sale price and $60,000 of land, at least 60% show a profit of
   $0 or more, with each building costed at its area's index and preset.
Run: python -m jobs.check_costs
"""

import csv
import json
from pathlib import Path

from core.db import connect
from engine.costs import cost
from engine.rules import Rules
from jobs.check_test_parcels import run as resolve_test_parcels

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads((ROOT / "data" / "rules" / "feasibility_defaults.json").read_text())
MISSING_MIDDLE = (308_000, 365_000)


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
    rows, wins = [], 0
    for t in csv.DictReader((ROOT / "data" / "reference" / "test_parcels.csv").open()):
        units, sale = int(t["units"]), float(t["sale_total"])
        idx, thin = index.get(t["area"].upper(), (None, False))
        lot = lots.get(t["addr"], {})
        d = rules.district_for(lot.get("zone"))
        c = cost(DEFAULTS, units, 60_000, idx, float(lot["lot_sqft"]) if lot.get("lot_sqft") else None,
                 d.far if d else None, thin_index=thin)  # fmt: skip
        profit = sale * DEFAULTS["sell"]["net_sale_factor"] - c.total
        wins += profit >= 0
        rows.append((t["addr"], t["area"], units, c.preset, idx, sale, c.total, profit))
    for r in rows:
        idx = f"{r[4]:.2f}" if r[4] is not None else "-"
        print(f"  {r[0]:24} {r[1]:20} {r[2]}u {r[3]:10} idx {idx:>5}  sale ${r[5]:>10,.0f}  cost ${r[6]:>10,.0f}"
              f"  profit ${r[7]:>10,.0f}")  # fmt: skip
    share = wins / len(rows)
    print(
        f"profit $0 or more at actual sale and $60,000 land: {wins} of {len(rows)} ({share:.0%}); target 60%"
    )
    return 0 if ok1 and share >= 0.6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
