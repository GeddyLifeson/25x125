import io
import zipfile

from jobs.load_overlays import to_row
from jobs.load_transit import cta_stations, metra_stations


def test_cta_rows_merge_into_one_station_with_all_lines():
    loc = {"latitude": "41.8857", "longitude": "-87.6278"}
    rows = [
        {"map_id": "40380", "station_descriptive_name": "Clark/Lake", "blue": "True", "location": loc},
        {
            "map_id": "40380",
            "station_descriptive_name": "Clark/Lake",
            "brn": "True",
            "g": "True",
            "location": loc,
        },
        {"map_id": "99999", "station_name": "No location"},
    ]
    got = cta_stations(rows)
    assert list(got) == ["40380"]
    assert got["40380"][3] == "Blue, Brown, Green"


def test_metra_stops_from_gtfs_with_padded_headers():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("stops.txt", "stop_id, stop_name, stop_lat, stop_lon\nOTC, Ogilvie, 41.8828,-87.6408\n")
    assert metra_stations(buf.getvalue()) == [("metra", "OTC", "Ogilvie", None, "-87.6408", "41.8828")]


def test_historic_overlay_keeps_rating_and_drops_computed_fields():
    r = {
        "objectid": "122752",
        "landmarkna": "1458-1458 N MAPLEWOOD AVE",
        "color": "Orange",
        ":@computed_region_x": "1",
        "the_geom": {"type": "MultiPolygon", "coordinates": []},
    }
    kind, sid, name, rating, attrs, _, pull = to_row("historic_survey", r, 7)
    assert (kind, sid, name, rating, pull) == (
        "historic_survey",
        "122752",
        "1458-1458 N MAPLEWOOD AVE",
        "Orange",
        7,
    )
    assert ":@computed_region_x" not in attrs


def test_city_layer_row_keeps_name_rating_and_drops_shape_fields():
    from jobs.load_city_layers import LAYERS
    from jobs.load_city_layers import to_row as layer_row

    layer = LAYERS["tsl_bus_corridor"]
    f = {
        "type": "Feature",
        "id": 321,
        "geometry": {"type": "MultiPolygon", "coordinates": []},
        "properties": {"OBJECTID": 321, "STREET_NAM": "Ashland Ave", "SERVED_BY_": "9, X9, 63",
                       "SHAPE.AREA": 1.0, "BUFF_DIST": 1320.0},
    }  # fmt: skip
    kind, sid, name, rating, attrs, _, pull = layer_row(
        "tsl_bus_corridor", f, 4, layer.key, layer.name_field, layer.rating_field
    )
    assert (kind, sid, name, rating, pull) == ("tsl_bus_corridor", "321", "Ashland Ave", "9, X9, 63", 4)
    assert "SHAPE.AREA" not in attrs and '"BUFF_DIST": 1320.0' in attrs


def test_fire_limits_file_has_a_source_and_one_polygon():
    import json

    from jobs.load_city_layers import FIRE_LIMITS

    fc = json.loads(FIRE_LIMITS.read_text())
    assert "13-116-010" in fc["source"] and fc["verified_on"]
    assert [f["geometry"]["type"] for f in fc["features"]] == ["Polygon"]


def test_assessor_neighborhood_row_uses_town_code_and_geometry_field():
    from jobs.load_boundaries import KINDS
    from jobs.load_boundaries import to_row as boundary_row

    r = {"town_nbhd": "77020", "township_name": "West Chicago", "multipolygon": {"type": "MultiPolygon"}}
    assert boundary_row("assessor_nbhd", r, 9)[:3] == ("assessor_nbhd", "77020", "West Chicago")
    assert "'77'" in KINDS["assessor_nbhd"][5]
    assert boundary_row("ward", {"ward": "1"}, 9) is None  # no geometry
