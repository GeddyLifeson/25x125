"""Nightly development score for every lot (data/rules/development_score.json).

For each lot (one row per 10-digit PIN, priced on its lowest 14-digit PIN):
1. Zoning upside: units allowed by right minus units standing (engine/zoning.py).
2. Profit: the largest 2-6 unit program that fits by right, priced to sell with the same engine functions the
   feasibility screen uses (engine/parcel_feasibility.inputs_for, engine/feasibility.scenario). Points use the
   return on cost at the 25th percentile of the 10,000-draw range.
   Sale values are estimated once per 0.005 degree grid cell (about 0.35 x 0.26 mi) and program, at the cell
   centre, so 600,000 lots need a few thousand comp searches. The live screen estimates at the lot itself.
3. Acquisition signals, location and incentives from parcel_site, lot_use, parcel_signal and lot_for_sale.
4. Penalties: historic rating, landmark district, 606/Pilsen demolition surcharge, fire limits.
The score is a sorting aid built from the points shown; it does not rate investment quality.
Run: python -m jobs.score_parcels [--limit N]
"""

import argparse
import json
import time
from datetime import date

from core.db import connect
from engine.comps import RULES_DIR, Target, estimate, index_from_db, params_from_files, pool_from_db
from engine.feasibility import scenario, scenarios_for
from engine.parcel_feasibility import escalation, inputs_for, land_value, load_defaults, load_patterns
from engine.rules import Rules
from engine.sites import FIELDS, _site
from engine.zoning import evaluate

CELL = 0.005

SQL = """
select distinct on (ps.pin10)
       ps.pin, ps.zone_class, ps.zone_class_2, ps.zone_share_2, ps.lot_sqft, ps.frontage_ft, ps.lot_source,
       ps.zone_share, ps.transit_served, ps.adu_zone, ps.adu_limits, ps.special_district, ps.historic_rating,
       ps.landmark_name, ps.fire_limits, lu.use_now, lu.units_now, bf.lots, bf.multi_lots, bf.single_lots,
       bf.two_flat_lots, bf.vacant_lots,
       ps.pin10, st_y(p.geom), st_x(p.geom), p.nbhd_code, p.community_area_num, ps.enterprise_zone,
       ps.opportunity_zone_2018, ps.tif_name, ps.open_violations, ps.scofflaw, ps.demolition_notice_date,
       coalesce(vb.n, 0), coalesce(fs.for_sale, false)
from parcel_site ps
join parcel p on p.pin = ps.pin and p.geom is not null
left join lot_use lu on lu.pin10 = ps.pin10
left join block_face bf on bf.block_face = lu.block_face
left join (select pin10, count(*) n from parcel_signal
           where kind = 'vacant_building_311' and signal_date > current_date - 730
             and lower(coalesce(attrs->>'duplicate', '')) <> 'true'
           group by pin10) vb on vb.pin10 = ps.pin10
left join (select pin10, bool_or(for_sale) for_sale from lot_for_sale group by pin10) fs on fs.pin10 = ps.pin10
where ps.zone_class is not null
order by ps.pin10, ps.pin, p.tax_year desc
{limit}
"""
EXTRA = ["pin10", "lat", "lon", "nbhd", "ca_num", "enterprise_zone", "opportunity_zone", "tif", "open_violations",
         "scofflaw", "demolition_notice_date", "vacant_building_2y", "for_sale"]  # fmt: skip

COLUMNS = ["pin10", "pin", "score", "zoning_upside", "profit", "acquisition", "location", "incentives", "penalties",
           "units_now", "by_right_units", "units_priced", "sale_per_unit", "sale_comps", "land", "total_cost",
           "profit_central", "profit_p25", "return_on_cost", "return_on_cost_p25", "max_land_price", "details",
           "computed_on"]  # fmt: skip


def linear(v: float, lo: float, hi: float, pts: float) -> float:
    return pts * min(max((v - lo) / (hi - lo), 0.0), 1.0)


def score_lot(row, w: dict, rules: Rules, ctx: dict, sale_for, sur_match: list[str], today: date) -> dict:
    """Points by part for one lot. `sale_for(lat, lon, units, unit_sqft)` returns a cached comp estimate."""
    p = w["parts"]
    site = _site(row[: len(FIELDS)])
    z = evaluate(site, rules)
    units_now = site.units_now or 0
    by_right = next((pa.units for pa in z.paths if pa.id == "by_right"), 0)
    out = {"pin10": ctx["pin10"], "pin": site.pin, "units_now": site.units_now, "by_right_units": by_right}
    det: dict = {}
    zu = linear(by_right - units_now, 0, 3, p["zoning_upside"]["max"])

    # Profit: the by-right pick from the same scenario picker the screen uses.
    profit_pts, inc_pts = 0.0, 0.0
    pick = next((pk for pk in scenarios_for(z, ctx["patterns"]) if pk["path"].id == "by_right"), None)
    if pick is None:
        det["profit"] = "no 2-6 unit program fits by right"
    else:
        units = pick["units"]
        unit_sqft = float(pick["unit_sqft"] or (1300 if units == 2 else 1200 if units == 3 else 1000))
        est = sale_for(ctx["lat"], ctx["lon"], units, unit_sqft)
        x = inputs_for(ctx, z, rules, pick, units, unit_sqft, est, None, ctx["esc"], {})
        sc = scenario(ctx["d"], x, "sell", "", pick["path"].approval, today.year)
        s = sc["sell"]
        out.update(units_priced=units, land=round(x.land), total_cost=sc["cost_range"]["central"])
        if "missing" in s:
            det["profit"] = s["missing"]
        else:
            total = sc["cost_range"]["central"]
            p25 = s["range"]["p25"]
            out.update(sale_per_unit=s["sale_per_unit"], sale_comps=x.sale_comps, profit_central=s["profit"],
                       profit_p25=p25, return_on_cost=s["return_on_cost"], return_on_cost_p25=round(p25 / total, 4),
                       max_land_price=s["max_land_price"])  # fmt: skip
            profit_pts = linear(p25 / total, 0.0, 0.25, p["profit"]["max"])
            if x.land == 0:
                det["land"] = "no land sales nearby; land priced at $0"
        progs = [i["id"] for i in sc["incentives"] if i["on"] and i["value"] > 0]
        det["incentives"] = progs
        inc_pts = min(len(progs) * 2, p["incentives"]["max"])
        if est and est.n_local >= 6:
            det["comps_within_0_75_mi"] = est.n_local

    ap = p["acquisition_signals"]["points"]
    sig = {
        "city_owned_for_sale": bool(ctx["for_sale"]),
        "vacant_land": site.use_now == "vacant",
        "vacant_building_complaint_2y": ctx["vacant_building_2y"] > 0,
        "open_violations": (ctx["open_violations"] or 0) > 0,
        "scofflaw_owner": bool(ctx["scofflaw"]),
        "demolition_notice": bool(ctx["demolition_notice_date"])
        and (today - ctx["demolition_notice_date"]).days <= 730,
    }
    det["signals"] = [k for k, v in sig.items() if v]
    acq = min(sum(ap[k] for k in det["signals"]), p["acquisition_signals"]["max"])

    lp = p["location"]["points"]
    loc = (lp["transit_served"] if site.transit_served else 0) + (
        lp["comps_6_plus_within_0_75_mi"] if "comps_within_0_75_mi" in det else 0
    )

    pp = w["penalties"]["points"]
    pen = {
        "historic_orange_or_red": (site.historic_rating or "").lower() in ("orange", "red"),
        "landmark_district": bool(site.landmark_name),
        "606_pilsen_surcharge": any(m in (site.special_district or "") for m in sur_match),
        "fire_limits": bool(site.fire_limits),
    }
    det["penalties"] = [k for k, v in pen.items() if v]
    pen_pts = max(sum(pp[k] for k in det["penalties"]), w["penalties"]["min_total"])

    total = zu + profit_pts + acq + loc + inc_pts + pen_pts
    lo, hi = w["range"]
    out.update(score=round(min(max(total, lo), hi), 1), zoning_upside=round(zu, 1), profit=round(profit_pts, 1),
               acquisition=acq, location=loc, incentives=inc_pts, penalties=pen_pts, details=det,
               computed_on=today)  # fmt: skip
    return out


def run(url: str | None = None, limit: int | None = None) -> dict:
    w = json.loads((RULES_DIR / "development_score.json").read_text())
    today = date.today()
    t0 = time.time()
    with connect(url) as conn:
        rules = Rules.from_db(conn)
        d, patterns = load_defaults(), load_patterns()
        pool, index, params = pool_from_db(conn), index_from_db(conn), params_from_files()
        esc = escalation(conn, d)
        cost_index = {r[0]: {"index": float(r[1]), "thin": r[2]} for r in conn.execute(
            "select community_area_num, index, thin from cost_index").fetchall()}  # fmt: skip
        sur = rules.special.get("demolition-surcharge-606-pilsen")
        sur_match = sur["match"] if sur else []
        lv_cache: dict = {}
        sales: dict = {}

        def sale_for(lat, lon, units, unit_sqft):
            key = (round(lat / CELL), round(lon / CELL), units, round(unit_sqft, -1))
            if key not in sales:
                sales[key] = estimate(
                    Target(key[0] * CELL, key[1] * CELL, units, today, unit_sqft), pool, params, index
                )
            return sales[key]

        rows = conn.execute(SQL.format(limit=f"limit {int(limit)}" if limit else "")).fetchall()
        out, errors = [], 0
        for row in rows:
            ctx = dict(zip(EXTRA, row[len(FIELDS) :], strict=True))
            lk = (ctx["nbhd"], ctx["ca_num"])
            if lk not in lv_cache:
                lv_cache[lk] = land_value(conn, *lk)
            ctx.update(land_values=lv_cache[lk], cost_index=cost_index.get(ctx["ca_num"]), patterns=patterns,
                       d=d, esc=esc)  # fmt: skip
            try:
                out.append(score_lot(row, w, rules, ctx, sale_for, sur_match, today))
            except Exception as e:  # noqa: BLE001 - one bad lot must not stop the nightly run
                errors += 1
                if errors <= 5:
                    print(f"  {row[0]}: {type(e).__name__}: {e}")
        if not limit:
            conn.execute("truncate parcel_score")
        else:
            conn.execute("delete from parcel_score where pin10 = any(%s)", ([r["pin10"] for r in out],))
        with conn.cursor().copy(f"copy parcel_score ({', '.join(COLUMNS)}) from stdin") as cp:
            for r in out:
                cp.write_row([json.dumps(r[c]) if c == "details" else r.get(c) for c in COLUMNS])
        conn.commit()
    res = {"lots": len(out), "errors": errors, "sale_cells": len(sales), "seconds": round(time.time() - t0)}
    print(
        f"scored {res['lots']:,} lots ({errors} errors), {res['sale_cells']:,} sale estimates, {res['seconds']}s"
    )
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    run(limit=a.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
