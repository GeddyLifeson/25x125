import csv
import io
import json
from datetime import date
from typing import Annotated

import psycopg
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import Response

from core.db import connect
from engine.comps import RULES_DIR, Target, estimate, index_from_db, params_from_files, pool_from_db
from engine.parcel_feasibility import feasibility
from engine.parcels import LOT_COLUMNS, lots, parcel, search
from engine.rents import rent
from engine.rules import Rules
from engine.sites import site_by_pin
from engine.zoning import evaluate

app = FastAPI(title="25x125 engine", version="0.1.0")


@app.get("/health")
def health() -> dict:
    """Engine is up; reports whether the database and PostGIS answer."""
    try:
        with connect() as conn:
            postgis = conn.execute("select postgis_version()").fetchone()[0]
        return {"status": "ok", "database": "ok", "postgis": postgis}
    except (psycopg.Error, OSError) as e:  # report, don't crash, so the host can see what's wrong
        return {"status": "degraded", "database": f"error: {type(e).__name__}"}


@app.get("/parcels/{pin}/zoning")
def parcel_zoning(pin: str, target: str | None = None) -> dict:
    """Zoning capacity paths and flags for a PIN (14 digits) or lot (10 digits), from the stored rules.

    `target` picks the rezoning district (e.g. RM-4.5); the default is the first listed target.
    """
    pin = pin.replace("-", "")
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    with connect() as conn:
        site = site_by_pin(conn, pin)
        if site is None:
            raise HTTPException(404, f"PIN {pin} is not in the parcel table")
        rules = Rules.from_db(conn)
    return evaluate(site, rules, rezoning_target=target).to_dict()


@app.get("/parcels/{pin}/sale-value")
def parcel_sale_value(
    pin: str, units: int = 3, sell: str = "building", sqft_per_unit: float | None = None
) -> dict:
    """Sale price per unit for new construction on this lot, from comps, with the 80% range.

    `sell` is 'building' (whole building, both comp kinds) or 'condo' (condo units, condo comps only).
    """
    pin = pin.replace("-", "")
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    if sell not in ("building", "condo") or not 2 <= units <= 6:
        raise HTTPException(400, "sell must be building or condo; units 2 to 6")
    with connect() as conn:
        row = conn.execute(
            "select st_y(geom), st_x(geom) from parcel where (pin = %s or pin10 = %s) and geom is not null"
            " order by tax_year desc limit 1",
            (pin, pin[:10]),
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"PIN {pin} has no location in the parcel table")
        pool, index = pool_from_db(conn), index_from_db(conn)
    sqft = sqft_per_unit or {2: 1300, 3: 1200}.get(units, 1000)
    t = Target(row[0], row[1], units, date.today(), sqft, "condo" if sell == "condo" else None)
    e = estimate(t, pool, params_from_files(), index)
    if e is None:
        raise HTTPException(404, "no comps")
    return {
        "per_unit": round(e.per_unit), "low": round(e.low) if e.low else None,
        "high": round(e.high) if e.high else None, "range": "80% range from tested errors",
        "comps": e.n, "radius_mi": e.radius_mi, "same_size_group": e.same_group, "notes": e.notes,
        "time_index": e.index_used,
        "source": "Cook County Assessor sales (wvhk-k5uv) and characteristics; FHFA HPI",
        "label": "estimate, not an appraisal",
        "comp_list": [
            {"pin": c.pin, "kind": c.kind, "sale_date": c.sale_date.isoformat(), "price_per_unit": round(c.price_per_unit),
             "adjusted": round(v), "weight": round(w, 3)}
            for c, v, w in sorted(e.comps, key=lambda x: -x[2])[:25]
        ],
    }  # fmt: skip


@app.get("/parcels/{pin}/rent")
def parcel_rent(pin: str, bedrooms: int = 2) -> dict:
    """Monthly rent per unit for a new unit on this lot: Census ACS rent, grown to today, x the new-building factor."""
    pin = pin.replace("-", "")
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    with connect() as conn:
        row = conn.execute(
            "select tract_geoid, zip from parcel where pin = %s or pin10 = %s order by tax_year desc limit 1",
            (pin, pin[:10]),
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"PIN {pin} is not in the parcel table")
        defaults = json.loads((RULES_DIR / "feasibility_defaults.json").read_text())
        r = rent(conn, bedrooms, row[0], row[1], defaults, date.today())
    if r is None:
        raise HTTPException(404, "no Census rent for this tract or ZIP area")
    return {
        **r,
        "label": "estimate, not an appraisal",
        "source": "U.S. Census Bureau ACS 5-year, tables B25031 and B25064",
    }


@app.post("/parcels/{pin}/feasibility")
def parcel_feasibility(
    pin: str, exit: str = "sell", target: str | None = None, overrides: Annotated[dict | None, Body()] = None
) -> dict:
    """Scenarios A/B/C (build and sell, or build and hold) with every line, range, incentive and source.

    `overrides` sets any input per scenario ("0", "1", "2") or for all ("all"): units, unit_sqft, land,
    sale_per_unit, rent_per_unit, cost_index, preset, stage, sell_as, toggles, answers.
    """
    pin = pin.replace("-", "")
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    if exit not in ("sell", "hold"):
        raise HTTPException(400, "exit must be sell or hold")
    with connect() as conn:
        out = feasibility(conn, pin, exit, overrides or {}, target)
    if out is None:
        raise HTTPException(404, f"PIN {pin} is not in the parcel table")
    return out


@app.get("/search")
def search_parcels(q: str, limit: int = 10) -> list[dict]:
    """Find parcels by street address (prefix, then similarity) or by 10- or 14-digit PIN."""
    if len(q.strip()) < 3:
        raise HTTPException(400, "type at least 3 characters")
    with connect() as conn:
        return search(conn, q, min(limit, 25))


@app.get("/lots")
def list_lots(
    community_area: int | None = None,
    zone: str | None = None,
    min_score: float = 0,
    min_units: int = 0,
    signal: str | None = None,
    for_sale: bool = False,
    vacant: bool = False,
    sort: Annotated[str, Query(pattern="^(score|return|upside|lot)$")] = "score",
    limit: int = 100,
    offset: int = 0,
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
):
    """Scored lots for the list and map, with filters. format=csv returns the same rows as a CSV file."""
    with connect() as conn:
        rows = lots(conn, community_area=community_area, zone_prefix=zone, min_score=min_score, min_units=min_units,
                    signal=signal, for_sale=for_sale, vacant=vacant, sort=sort,
                    limit=min(limit, 5000 if format == "csv" else 500), offset=offset)  # fmt: skip
    if format == "json":
        return rows
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([*LOT_COLUMNS, "source"])
    for r in rows:
        w.writerow([json.dumps(r[c]) if c == "details" else r[c] for c in LOT_COLUMNS]
                   + ["25x125 nightly score; estimates, not tax, legal, zoning or appraisal advice"])  # fmt: skip
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=25x125-lots.csv"})  # fmt: skip


@app.get("/parcels/{pin}")
def parcel_facts(pin: str) -> dict:
    """The parcel page's facts: lot, zoning, overlays, what stands on the lot, signals and recent sales."""
    pin = pin.replace("-", "")
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    with connect() as conn:
        out = parcel(conn, pin)
    if out is None:
        raise HTTPException(404, f"PIN {pin} is not in the parcel table")
    return out
