from jobs import nightly


def test_nightly_keeps_going_after_a_failed_source(monkeypatch, capsys):
    ran = []

    def fail():
        raise RuntimeError("portal down")

    monkeypatch.setattr(
        nightly, "steps", lambda year, skip: [("a", fail), ("b", lambda: ran.append("b") or 5)]
    )
    monkeypatch.setattr(nightly.report, "main", lambda: print("report"))
    assert nightly.main([]) == 1
    out = capsys.readouterr().out
    assert ran == ["b"]
    assert "a: FAILED" in out and "b: 5" in out and "report" in out


def test_skip_yearly_leaves_only_nightly_steps():
    names = [n for n, _ in nightly.steps(2026, skip_yearly=True)]
    assert names == [
        "sales",
        "permits",
        "zoning",
        "overlays",
        "transit",
        "signals",
        "assessor permits",
        "city layers",
        "parcel sites",
        "lot use and block faces",
        "comps",
        "cost index",
        "land values",
        "rules",
    ]
