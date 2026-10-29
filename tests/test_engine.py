from fastapi.testclient import TestClient

import engine.app as app_module
from db.migrate import migrate


def test_health_reports_postgis(db_url, monkeypatch):
    migrate(db_url)
    monkeypatch.setattr(app_module, "connect", lambda: __import__("psycopg").connect(db_url))
    body = TestClient(app_module.app).get("/health").json()
    assert body["status"] == "ok"
    assert body["postgis"]


def test_health_degrades_without_database(monkeypatch):
    def broken():
        raise OSError("no database")

    monkeypatch.setattr(app_module, "connect", broken)
    body = TestClient(app_module.app).get("/health").json()
    assert body == {"status": "degraded", "database": "error: OSError"}
