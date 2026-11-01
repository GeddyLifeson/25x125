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
        "cost escalation",
        "lots for sale",
        "foreclosure auctions",
        "rezonings",
        "parcel sites",
        "lot use and block faces",
        "comps",
        "older sales",
        "cost index",
        "land values",
        "rules",
        "development score",
    ]


def test_a_second_run_stops_while_one_holds_the_lock(db_url, monkeypatch, capsys):
    import psycopg

    from core.settings import settings

    monkeypatch.setattr(settings, "database_url", db_url)
    ran = []
    monkeypatch.setattr(nightly, "steps", lambda year, skip: [("a", lambda: ran.append("a"))])
    monkeypatch.setattr(nightly.report, "main", lambda: None)
    with psycopg.connect(db_url, autocommit=True) as other:
        other.execute("select pg_advisory_lock(%s)", (nightly.LOCK_KEY,))
        assert nightly.main(["--skip-yearly"]) == 0
        assert ran == [] and "in progress" in capsys.readouterr().out
    assert nightly.main(["--skip-yearly"]) == 0 and ran == ["a"]
