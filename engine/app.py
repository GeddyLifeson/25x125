import psycopg
from fastapi import FastAPI

from core.db import connect

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
