"""The pure helpers in scripts/codespace.py (the GitHub Codespaces launcher)."""

import datetime as dt
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "codespace", Path(__file__).resolve().parent.parent / "scripts" / "codespace.py"
)
codespace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codespace)


def test_app_url_in_a_codespace():
    env = {
        "CODESPACE_NAME": "fluffy-pancake-x7",
        "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev",
    }
    assert codespace.app_url(env) == "https://fluffy-pancake-x7-3000.app.github.dev"


def test_app_url_outside_a_codespace():
    assert codespace.app_url({}) == "http://localhost:3000"


def test_snapshot_parts_whole_file_wins():
    assets = [{"name": "snapshot.json"}, {"name": "x25x125.dump"}, {"name": "x25x125.dump.part-00"}]
    assert [a["name"] for a in codespace.snapshot_parts(assets)] == ["x25x125.dump"]


def test_snapshot_parts_in_order():
    assets = [{"name": "x25x125.dump.part-01"}, {"name": "snapshot.json"}, {"name": "x25x125.dump.part-00"}]
    assert [a["name"] for a in codespace.snapshot_parts(assets)] == [
        "x25x125.dump.part-00",
        "x25x125.dump.part-01",
    ]


def test_snapshot_parts_none():
    assert codespace.snapshot_parts([{"name": "snapshot.json"}]) == []


def test_update_due():
    now = dt.datetime(2026, 11, 2, 12, tzinfo=dt.UTC)
    assert codespace.update_due({}, now)
    assert not codespace.update_due({"last_update_at": "2026-11-02T00:00:00+00:00"}, now)
    assert codespace.update_due({"last_update_at": "2026-11-01T10:00:00+00:00"}, now)


def test_repo_name():
    assert codespace.repo_name({"GITHUB_REPOSITORY": "someone/fork"}) == "someone/fork"
    assert codespace.repo_name({}) == "GeddyLifeson/25x125"
