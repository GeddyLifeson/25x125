"""Desktop program start-up: create the 25x125 database on the bundled Postgres if it is missing, then apply
the migrations. Copied into the program's runtime folder as desktop_bootstrap.py; run by desktop/src/main.js.

Run: python -m desktop_bootstrap   (DATABASE_URL names the database to create)
"""

import sys

import psycopg
from psycopg import sql

from core.settings import settings
from db.migrate import migrate


def ensure_database(url: str) -> bool:
    """Create the database named in `url` when it does not exist. True when it was created."""
    info = psycopg.conninfo.conninfo_to_dict(url)
    name = info.get("dbname") or "x25x125"
    admin = psycopg.conninfo.make_conninfo(url, dbname="postgres")
    with psycopg.connect(admin, autocommit=True, connect_timeout=10) as conn:
        if conn.execute("select 1 from pg_database where datname = %s", (name,)).fetchone():
            return False
        conn.execute(
            sql.SQL("create database {} encoding 'UTF8' template template0").format(sql.Identifier(name))
        )
        return True


def main() -> int:
    created = ensure_database(settings.database_url)
    print("database:", "created" if created else "exists", flush=True)
    names = migrate()
    print("migrations applied:", ", ".join(names) if names else "nothing new", flush=True)
    # PostGIS and its PROJ data load: Illinois State Plane (EPSG:3435, the county's parcel grid) to lat/lon.
    with psycopg.connect(settings.database_url) as conn:
        print("postgis:", conn.execute("select postgis_full_version()").fetchone()[0], flush=True)
        pt = conn.execute(
            "select st_astext(st_transform(st_setsrid(st_point(1160000, 1900000), 3435), 4326))"
        ).fetchone()[0]
        print("transform check (State Plane to lat/lon):", pt, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
