"""Census tract of each lot outside Chicago, from the Census Bureau's 2024 cartographic tract boundaries.

ACS 2020-2024 rents are published on 2020 tract lines. Florida's tax roll carries a census block code, but it is
not always on 2020 lines, and the Texas and Georgia parcel layers have none, so every region outside Chicago
takes its tract from the boundary file: the tract that contains the lot's point.
Run: python -m jobs.load_tracts   (REGION set; downloads one state file, about 4 MB)
"""

import io
import json
import urllib.request
import zipfile
from collections.abc import Callable

import shapefile  # pyshp

from core import region
from core.db import connect
from core.sources import finish_pull, start_pull

HOST = "www2.census.gov"
URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_{st}_tract_500k.zip"


def tracts(data: bytes):
    """(geoid, geojson) for each tract in a state file. All of the state's tracts load, since city lots spill
    past the loaded counties (12,748 Houston lots sit in Fort Bend and Montgomery counties)."""
    z = zipfile.ZipFile(io.BytesIO(data))
    name = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(name + ".shp")), dbf=io.BytesIO(z.read(name + ".dbf")))
    fields = [f[0] for f in r.fields[1:]]
    for sr in r.iterShapeRecords():
        rec = dict(zip(fields, sr.record, strict=False))
        yield rec["GEOID"], json.dumps(sr.shape.__geo_interface__)


def run(opener: Callable = urllib.request.urlopen, url: str | None = None) -> dict:
    if region.is_chicago():
        raise SystemExit("Chicago lots carry their tract from the Cook County parcel data")
    states = sorted({c["fips"][:2] for c in region.current()["counties"]})
    out = {"tracts": 0}
    with connect(url) as conn:
        conn.execute("create temp table tract_shape (geoid text primary key, geom geometry)")
        for st in states:
            src = URL.format(st=st)
            pull_id = start_pull(conn, HOST, src)
            with opener(src, timeout=300) as resp:
                rows = list(tracts(resp.read()))
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into tract_shape values (%s, st_setsrid(st_geomfromgeojson(%s), 4326))", rows
                )
            finish_pull(conn, pull_id, len(rows))
            out["tracts"] += len(rows)
        conn.execute("create index on tract_shape using gist (geom)")
        cur = conn.execute(
            """update parcel p set tract_geoid = t.geoid from tract_shape t
               where st_intersects(t.geom, p.geom) and p.tract_geoid is distinct from t.geoid"""
        )
        out["lots_changed"] = cur.rowcount
        out["lots_with_tract"], out["lots"] = conn.execute(
            "select count(tract_geoid), count(*) from parcel"
        ).fetchone()
        conn.commit()
    return out


if __name__ == "__main__":
    print(run())
