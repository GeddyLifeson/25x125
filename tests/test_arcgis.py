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
        {"features": [{"properties": {"OBJECTID": 3}}]},  # short page: the server may cap below page_size
        {"features": []},
        {"count": 0},
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
    assert len(urls) == 4 and "OBJECTID+%3E+3" in urls[2] and "returnCountOnly=true" in urls[3]
    assert "OBJECTID+%3E+2" in urls[1]
    assert "outFields=PIN10%2COBJECTID" in urls[0]
    assert "outSR=4326" in urls[0]
    assert client.host == "gis.example.org"


def test_features_halves_the_page_when_the_server_fails():
    sizes = []

    def opener(url, timeout):
        if "returnCountOnly" in url:
            return FakeResponse(json.dumps({"count": 0}).encode())
        size = int(url.split("resultRecordCount=")[1].split("&")[0])
        sizes.append(size)
        if size > 100:
            return FakeResponse(b"<html>timeout</html>")
        if len(sizes) > 6:
            return FakeResponse(json.dumps({"features": []}).encode())
        return FakeResponse(json.dumps({"features": [{"properties": {"OBJECTID": len(sizes)}}]}).encode())

    client = ArcGIS(
        "https://gis.example.org/rest/services/x/MapServer/1", opener=opener, sleep=lambda s: None, retries=0
    )
    pages = list(client.features("1=1", "*", page_size=400))
    assert sizes[:3] == [400, 200, 100]
    assert len(pages) >= 1 and all(s == 100 for s in sizes[2:])


def test_features_does_not_stop_on_a_false_empty_page():
    bodies = [
        {"features": [{"properties": {"OBJECTID": 1}}]},
        {"features": []},  # the server skipped rows it still has
        {"count": 1},
        {"features": [{"properties": {"OBJECTID": 2}}]},
        {"features": []},
        {"count": 0},
    ]

    def opener(url, timeout):
        return FakeResponse(json.dumps(bodies.pop(0)).encode())

    client = ArcGIS(
        "https://gis.example.org/rest/services/x/MapServer/1", opener=opener, sleep=lambda s: None
    )
    got = [f["properties"]["OBJECTID"] for page in client.features("1=1", "*") for f in page]
    assert got == [1, 2] and not bodies
