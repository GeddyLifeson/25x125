"""Load one parcel's inputs from Postgres and price its scenarios (the live feasibility screen).

The nightly scorer uses the same engine functions with inputs loaded in bulk (jobs/score_parcels.py).
"""

import json
from datetime import date

from engine.comps import RULES_DIR, Target, estimate, index_from_db, params_from_files, pool_from_db
from engine.feasibility import Inputs, pattern_fits, scenario, scenarios_for
from engine.rents import rent
from engine.rules import Rules
from engine.sites import site_by_pin
from engine.zoning import evaluate


def load_defaults() -> dict:
    return json.loads((RULES_DIR / "feasibility_defaults.json").read_text())


def load_patterns() -> list[dict]:
    return json.loads((RULES_DIR / "building_patterns.json").read_text())["patterns"]


def bedrooms_for(unit_sqft: float) -> int:
    return 3 if unit_sqft >= 1100 else 2


def parcel_context(conn, pin: str) -> dict | None:
    row = conn.execute(
        """select p.pin, p.pin10, st_y(p.geom), st_x(p.geom), p.tract_geoid, p.zip, p.community_area_num,
                  p.community_area_name, p.nbhd_code, ps.enterprise_zone, ps.opportunity_zone_2018, ps.tif_name
           from parcel p left join parcel_site ps on ps.pin = p.pin
           where (p.pin = %s or p.pin10 = %s) and p.geom is not null
           order by p.tax_year desc, p.pin limit 1""",
        (pin, pin[:10]),
    ).fetchone()
    if not row:
        return None
    keys = ["pin", "pin10", "lat", "lon", "tract", "zip", "ca_num", "ca_name", "nbhd", "enterprise_zone",
            "opportunity_zone", "tif"]  # fmt: skip
    ctx = dict(zip(keys, row, strict=True))
    ci = conn.execute(
        "select index, thin, permits, neighbor_weight, computed_on from cost_index where community_area_num = %s",
        (ctx["ca_num"],),
    ).fetchone()
    ctx["cost_index"] = {"index": float(ci[0]), "thin": ci[1], "permits": ci[2], "neighbor_weight": float(ci[3]),
                         "computed_on": ci[4].isoformat()} if ci else None  # fmt: skip
    ctx["land_values"] = land_value(conn, ctx["nbhd"], ctx["ca_num"])
    return ctx


def escalation(conn, d: dict) -> dict:
    """Preset escalation (build_spec_presets.escalation): latest Census index over the base, then half the build
    period at the 12-month change. 1.0 when the index has not been loaded."""
    e = d["build_spec_presets"]["escalation"]
    row = conn.execute(
        "select latest_month, latest_value, change_12m from cost_escalation where series = %s", (e["series"],)
    ).fetchone()
    if not row or not row[1]:
        return {"factor": 1.0, "basis": "escalation index not loaded; presets as published"}
    months = d["financing"]["months_build"]
    change = float(row[2] or 0)
    f = float(row[1]) / e["base_value"] * (1 + change) ** (months / 2 / 12)
    return {"factor": round(f, 4), "latest_month": str(row[0]), "change_12m": change,
            "basis": f"Census under-construction index {row[0]} vs {e['base_month']}, then {change:+.1%} a year to mid-build"}  # fmt: skip


def land_value(conn, nbhd: str | None, ca_num: int | None, min_sales: int = 5) -> dict | None:
    """Land price per buildable sq ft: Assessor neighborhood, else community area (CLAUDE.md rule 4)."""
    for kind, gid in (("nbhd", nbhd), ("community_area", str(ca_num) if ca_num else None)):
        if not gid:
            continue
        row = conn.execute(
            """select sales, median_per_lot_sqft, median_per_buildable_sqft, first_sale, last_sale
               from land_value where geo_kind = %s and geo_id = %s and kind = 'all'""",
            (kind, gid),
        ).fetchone()
        if row and row[0] >= min_sales:
            return {"geo": kind, "geo_id": gid, "sales": row[0], "per_lot_sqft": float(row[1]),
                    "per_buildable_sqft": float(row[2]) if row[2] else None,
                    "first_sale": row[3].isoformat(), "last_sale": row[4].isoformat(),
                    "source": "vacant and teardown sales, last 36 months (jobs/build_land_values.py)"}  # fmt: skip
    return None


def feasibility(
    conn, pin: str, exit_: str = "sell", overrides: dict | None = None, target: str | None = None
) -> dict | None:
    """Scenarios A/B/C for a parcel with every input and its source. `overrides` may set any Inputs field per
    scenario index ('0', '1', '2') or for all ('all')."""
    overrides = overrides or {}
    site = site_by_pin(conn, pin)
    ctx = parcel_context(conn, pin)
    if site is None or ctx is None:
        return None
    rules = Rules.from_db(conn)
    z = evaluate(site, rules, rezoning_target=target)
    d = load_defaults()
    patterns = load_patterns()
    pool, index, params = pool_from_db(conn), index_from_db(conn), params_from_files()
    today = date.today()
    picks = scenarios_for(z, patterns)
    esc = escalation(conn, d)
    out = {"pin": ctx["pin"], "address_area": ctx["ca_name"], "zone_class": z.zone_class, "lot_sqft": z.lot_sqft,
           "frontage_ft": z.frontage_ft, "exit": exit_, "zoning_flags": [f.__dict__ for f in z.flags],
           "inputs": {"cost_index": ctx["cost_index"], "land_value": ctx["land_values"], "escalation": esc}, "scenarios": [],
           "label": "Estimates, not tax, legal, zoning or appraisal advice."}  # fmt: skip
    for i, pick in enumerate(picks):
        path = pick["path"]
        o = {**overrides.get("all", {}), **overrides.get(str(i), {})}
        units = int(o.get("units", pick["units"]))
        unit_sqft = float(
            o.get("unit_sqft") or pick["unit_sqft"] or (1300 if units == 2 else 1200 if units == 3 else 1000)
        )
        sell_as = o.get("sell_as", "building")
        est = estimate(Target(ctx["lat"], ctx["lon"], min(units, 6), today, unit_sqft,
                              "condo" if sell_as == "condo" else None), pool, params, index)  # fmt: skip
        r = rent(conn, bedrooms_for(unit_sqft), ctx["tract"], ctx["zip"], d, today)
        x = inputs_for(ctx, z, rules, pick, units, unit_sqft, est, r, esc, o)
        letter = "ABC"[i]
        sc = scenario(d, x, exit_, f"{letter} · {_label(pick, path)}", path.approval, today.year)
        sc["path"] = {"id": path.id, "district": path.district, "units": path.units,
                      "floor_area_sqft": path.floor_area_sqft, "max_height_ft": path.max_height_ft,
                      "parking_spaces": path.parking_spaces, "notes": path.notes, "citations": path.citations}  # fmt: skip
        sc["pattern"] = pick["pattern"]
        sc["sale_source"] = None if not est else {
            "comps": est.n, "radius_mi": est.radius_mi, "same_size_group": est.same_group, "notes": est.notes,
            "sell_as": sell_as, "time_index": est.index_used,
            "source": "Cook County Assessor sales of buildings built 2014 or later; FHFA metro index"}  # fmt: skip
        sc["rent_source"] = r
        out["scenarios"].append(sc)
    out["patterns_checked"] = [
        {"pattern": pt["id"], "path": p.id, "fits": f, "why": why}
        for p in z.paths
        for pt in patterns
        for f, why in [pattern_fits(pt, p, z.lot_sqft)]
    ]
    return out


def inputs_for(
    ctx: dict, z, rules: Rules, pick: dict, units: int, unit_sqft: float, est, r, esc: dict, o: dict
) -> Inputs:
    """Scenario inputs for one pick. Shared by the live screen and the nightly scorer so they cannot drift."""
    path = pick["path"]
    land, land_basis = (
        (float(o["land"]), "entered") if "land" in o else land_for(ctx["land_values"], rules, z)
    )
    ci = ctx["cost_index"] or {}
    x = Inputs(
        units=units,
        sale_per_unit=float(o["sale_per_unit"]) if "sale_per_unit" in o else (est.per_unit if est else None),
        sale_low_mult=(est.low / est.per_unit) if est and est.low else None,
        sale_high_mult=(est.high / est.per_unit) if est and est.high else None,
        sale_comps=est.n if est else None,
        rent_per_unit=float(o["rent_per_unit"]) if "rent_per_unit" in o else (r["per_month"] if r else None),
        rent_low_mult=r["low"] / r["per_month"] if r else None,
        rent_high_mult=r["high"] / r["per_month"] if r else None,
        land=land, land_basis=land_basis,
        cost_index=float(o["cost_index"]) if "cost_index" in o else ci.get("index"),
        cost_index_thin=bool(ci.get("thin")),
        lot_sqft=z.lot_sqft, far=path.floor_area_sqft / z.lot_sqft if z.lot_sqft and path.floor_area_sqft else None,
        gross_sqft=float(o["gross_sqft"]) if "gross_sqft" in o else pick["gross_sqft"],
        unit_sqft=unit_sqft, preset=o.get("preset"), rezoning=path.id == "rezoning",
        stage=o.get("stage", "feasibility"), commercial_sqft=float(pick.get("commercial_sqft") or 0),
        in_enterprise_zone=bool(ctx["enterprise_zone"]), in_opportunity_zone=bool(ctx["opportunity_zone"]),
        in_tif=bool(ctx["tif"]), toggles=o.get("toggles", {}), answers=o.get("answers", {}),
        escalation=float(o.get("escalation", esc["factor"])),
    )  # fmt: skip
    return x


def land_for(lv: dict | None, rules: Rules, z) -> tuple[float, str]:
    """Land from the land map: per buildable sq ft x lot x FAR of the current district, else per lot sq ft."""
    if lv and lv["per_buildable_sqft"] and (now := _buildable_now(rules, z)):
        return lv["per_buildable_sqft"] * now, (
            f"land map: ${lv['per_buildable_sqft']:,.0f} per buildable sq ft under the current district,"
            f" {lv['sales']} sales {lv['first_sale']} to {lv['last_sale']} ({lv['geo']} {lv['geo_id']})"
        )
    if lv:
        return lv["per_lot_sqft"] * (
            z.lot_sqft or 0
        ), f"land map: ${lv['per_lot_sqft']:,.0f} per lot sq ft, {lv['sales']} sales"
    return 0.0, "no land sales nearby: enter the asking price"


def _buildable_now(rules: Rules, z) -> float | None:
    """Buildable area under the lot's current district (lot x FAR), the land map's denominator."""
    d = rules.district_for(z.zone_class)
    return z.lot_sqft * d.far if d and d.far and z.lot_sqft else None


def _label(pick: dict, path) -> str:
    names = {"two-flat": "2-flat", "three-flat": "3-flat", "three-flat-coach-house": "3-flat + coach house",
             "four-flat": "4-flat", "six-flat": "6-flat", "storefront-three": "storefront + 3"}  # fmt: skip
    what = names.get(pick["pattern"], f"{pick['units']} units")
    how = {"by_right": "by right", "rs3_two_flat": "RS-3 block-face rule", "admin_adjustment": "10% adjustment",
           "adu": "with ADU", "rezoning": f"rezone to {path.district}"}.get(path.id, path.id)  # fmt: skip
    return f"{what} {how}"
