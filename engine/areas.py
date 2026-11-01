"""Community areas for the map's area filter, and the area snapshot line above the list.

Reads the nightly tables only (comp, cost_index, land_value, boundary).
"""

from fastapi import APIRouter, HTTPException

from core.db import connect

router = APIRouter()


@router.get("/community-areas")
def community_areas() -> list[dict]:
    """The 77 community areas, by number, with their map bounds [west, south, east, north]."""
    with connect() as conn:
        rows = conn.execute(
            """select code::int, initcap(name), st_xmin(geom), st_ymin(geom), st_xmax(geom), st_ymax(geom)
               from boundary where kind = 'community_area' order by code::int"""
        ).fetchall()
    return [{"num": r[0], "name": r[1], "bounds": [round(v, 5) for v in r[2:]]} for r in rows]


@router.get("/community-areas/{num}/snapshot")
def area_snapshot(num: int) -> dict:
    """New-construction sales (last 3 years), the cost index and the land value for one community area."""
    with connect() as conn:
        name = conn.execute(
            "select initcap(name) from boundary where kind = 'community_area' and code = %s", (str(num),)
        ).fetchone()
        if name is None:
            raise HTTPException(404, f"community area {num} not found")
        sales = conn.execute(
            """select kind, count(*), percentile_cont(0.5) within group (order by price_per_unit), min(sale_date),
                      max(sale_date), max(built_at)::date
               from comp where excluded is null and lower(community_area) = lower(%s)
                 and sale_date > current_date - interval '3 years'
               group by kind order by kind""",
            (name[0],),
        ).fetchall()
        ci = conn.execute(
            "select index, permits, thin, computed_on from cost_index where community_area_num = %s", (num,)
        ).fetchone()
        lv = conn.execute(
            """select median_per_lot_sqft, sales, first_sale, last_sale, computed_on from land_value
               where geo_kind = 'community_area' and geo_id = %s and kind = 'all'""",
            (str(num),),
        ).fetchone()
    return {
        "num": num,
        "name": name[0],
        "sales": [
            {"kind": k, "sales": n, "median_per_unit": round(float(m)), "first_sale": a.isoformat(),
             "last_sale": b.isoformat(), "computed_on": c.isoformat()}
            for k, n, m, a, b, c in sales
        ],
        "sales_source": "Cook County Assessor sales (wvhk-k5uv) of buildings and condo units built 2014 or later; "
                        "new-construction first sales, last 3 years",
        "cost_index": None if ci is None else {
            "index": float(ci[0]), "permits": ci[1], "thin": ci[2], "computed_on": ci[3].isoformat(),
            "source": "Chicago building permits (ydr8-5enu), 2-6 unit new construction, cost per unit vs the city median"},
        "land_value": None if lv is None or lv[0] is None else {
            "per_lot_sqft": round(float(lv[0]), 2), "sales": lv[1], "first_sale": lv[2].isoformat() if lv[2] else None,
            "last_sale": lv[3].isoformat() if lv[3] else None, "computed_on": lv[4].isoformat(),
            "source": "Cook County Assessor sales of vacant lots and teardowns, last 36 months (jobs/build_land_values.py)"},
    }  # fmt: skip
