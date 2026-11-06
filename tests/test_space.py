"""The pure helpers in scripts/space.py and scripts/deploy_space.py (the public website)."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


deploy_space, space, codespace = _load("deploy_space"), _load("space"), _load("codespace")


def test_pinned_dockerfile_sets_ref_and_repo():
    text = "FROM x\nARG REPO=https://github.com/a/b.git\nARG REF=main\nRUN echo\n"
    out = deploy_space.pinned_dockerfile(text, "abc123", "https://github.com/c/d.git")
    assert "ARG REF=abc123\n" in out
    assert "ARG REPO=https://github.com/c/d.git\n" in out
    assert out.startswith("FROM x\n")


def test_site_url():
    assert deploy_space.site_url("GeddyLifeson/25x125") == "https://geddylifeson-25x125.hf.space"


def test_dataset_repo(monkeypatch):
    monkeypatch.delenv("BACKUP_REPO", raising=False)
    monkeypatch.setenv("SPACE_ID", "Someone/25x125")
    assert space.dataset_repo() == "Someone/25x125-data"
    monkeypatch.delenv("SPACE_ID")
    assert space.dataset_repo() is None


def test_app_url_on_space(monkeypatch):
    assert codespace.app_url({"SPACE_HOST": "x-25x125.hf.space"}) == "https://x-25x125.hf.space"
