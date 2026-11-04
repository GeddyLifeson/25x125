"""The local background map: which tiles the cut asks for, and the engine serving them from the file."""

import gzip

from fastapi.testclient import TestClient
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import Writer

import engine.app as app_module
from jobs.build_basemap import load_rules, tile_range, wanted_tiles

client = TestClient(app_module.app)


def test_tile_range_covers_chicago():
    xs, ys = tile_range([-87.96, 41.63, -87.5, 42.04], 15)
    assert len(xs) == 43 and len(ys) == 51  # about 15 by 22 miles at street level
    assert tile_range([-87.96, 41.63, -87.5, 42.04], 0) == (range(1), range(1))


def test_wanted_tiles_are_in_file_order_and_include_every_zoom():
    tiles = wanted_tiles(load_rules()["areas"])
    ids = [zxy_to_tileid(*t) for t in tiles]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert {z for z, _, _ in tiles} == set(range(9, 16))


def _write(path, tiles: dict):
    with open(path, "wb") as f:
        w = Writer(f)
        for (z, x, y), data in sorted(tiles.items(), key=lambda kv: zxy_to_tileid(*kv[0])):
            w.write_tile(zxy_to_tileid(z, x, y), gzip.compress(data))
        w.finalize(
            {
                "tile_type": TileType.MVT,
                "tile_compression": Compression.GZIP,
                "min_zoom": 9,
                "max_zoom": 15,
                "min_lon_e7": -884000000,
                "min_lat_e7": 414500000,
                "max_lon_e7": -873000000,
                "max_lat_e7": 422500000,
                "center_zoom": 11,
                "center_lon_e7": -877300000,
                "center_lat_e7": 418400000,
            },
            {"attribution": "© OpenStreetMap contributors"},
        )


def test_engine_serves_the_local_basemap(tmp_path, monkeypatch):
    monkeypatch.setenv("BASEMAP_FILE", str(tmp_path / "none.pmtiles"))
    assert client.get("/basemap").status_code == 404
    assert client.get("/tiles/basemap/9/131/190").status_code == 204

    f = tmp_path / "chicago.pmtiles"
    _write(f, {(9, 131, 190): b"tile-bytes", (15, 8402, 12175): b"street"})
    monkeypatch.setenv("BASEMAP_FILE", str(f))
    info = client.get("/basemap").json()
    assert info["min_zoom"] == 9 and info["max_zoom"] == 15 and "OpenStreetMap" in info["attribution"]
    r = client.get("/tiles/basemap/9/131/190")
    assert r.status_code == 200 and r.content == b"tile-bytes"  # stored gzipped, sent with content-encoding
    assert client.get("/tiles/basemap/9/130/190").status_code == 204  # not in the file
    assert client.get("/tiles/basemap/5/8/11").status_code == 204  # below the file's zooms
    assert client.get("/tiles/basemap/9/999/190").status_code == 400
