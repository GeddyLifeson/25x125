import psycopg
from fastapi import FastAPI, HTTPException

from core.db import connect
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
