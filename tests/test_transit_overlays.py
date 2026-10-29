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
