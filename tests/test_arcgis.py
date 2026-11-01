import io
import json

from core.arcgis import ArcGIS


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_features_pages_by_key():
    bodies = [
        {"features": [{"properties": {"OBJECTID": 1}}, {"properties": {"OBJECTID": 2}}]},
        {"features": [{"properties": {"OBJECTID": 3}}]},
    ]
    urls = []

    def opener(url, timeout):
        urls.append(url)
        return FakeResponse(json.dumps(bodies.pop(0)).encode())

    client = ArcGIS(
        "https://gis.example.org/rest/services/x/MapServer/2025", opener=opener, sleep=lambda s: None
    )
    got = [f["properties"]["OBJECTID"] for page in client.features("1=1", "PIN10", page_size=2) for f in page]
    assert got == [1, 2, 3]
    assert "OBJECTID+%3E+2" in urls[1]
    assert "outFields=PIN10%2COBJECTID" in urls[0]
    assert "outSR=4326" in urls[0]
    assert client.host == "gis.example.org"
