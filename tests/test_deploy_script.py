from scripts import deploy


def test_example_env_reads_and_flags_only_the_placeholders(tmp_path):
    env = deploy.read_env(deploy.ROOT / ".env.production.example")
    assert env["APP_URL"] == "https://x25x125-web.fly.dev"
    assert env["DATABASE_URL"].endswith("?sslmode=require")
    assert deploy.check_env(env) == [
        "ENGINE_SHARED_SECRET is still the example placeholder; make one (see the example file)",
        "EMAIL_SERVER is still the example placeholder; put in your Gmail address and app password",
    ]
    # Every secret the apps take is documented in the example file.
    names = {k for app in deploy.APPS.values() for k in app["secrets"]}
    assert names <= set(env)


def test_bad_values_are_named(tmp_path):
    f = tmp_path / "env"
    f.write_text('DATABASE_URL=postgresql://u:p@h:6543/db\nAPP_URL=http://x\nEMAIL_FROM="A <a@b.c>"\n')
    env = deploy.read_env(f)
    assert env["EMAIL_FROM"] == "A <a@b.c>"
    problems = " | ".join(deploy.check_env(env))
    assert "6543" in problems and "sslmode" in problems and "https" in problems
    assert "ENGINE_SHARED_SECRET is empty" in problems and "EMAIL_SERVER is empty" in problems


def test_dry_run_changes_nothing_and_prints_every_step(capsys, monkeypatch):
    monkeypatch.setattr(deploy.shutil, "which", lambda name: None)  # no flyctl needed for a dry run
    assert deploy.main(["--dry-run", "--first-load"]) == 0
    out = capsys.readouterr().out
    for part in ("fly apps create x25x125-engine", "fly secrets import --stage --app x25x125-web",
                 "--config deploy/fly.engine.toml", "--config deploy/fly.tiles.toml", "--config deploy/fly.web.toml",
                 "--schedule daily", "-- python -m jobs.nightly --skip-yearly", "--rm", "Nothing was changed"):  # fmt: skip
        assert part in out, part
    assert "replace-with" not in out  # secret values never printed


def test_gmail_checks():
    from scripts.deploy import gmail_problems

    good = "smtps://marlon%40gmail.com:abcdefghijklmnop@smtp.gmail.com:465"
    assert gmail_problems(good, "25x125 <marlon@gmail.com>") == []
    assert gmail_problems("smtps://resend:re_x@smtp.resend.com:465", "a@b.c") == []
    spaced = "smtps://marlon%40gmail.com:abcd%20efgh%20ijkl%20mnop@smtp.gmail.com:465"
    assert any("without its spaces" in p for p in gmail_problems(spaced, "marlon@gmail.com"))
    assert any("same Gmail address" in p for p in gmail_problems(good, "25x125 <other@gmail.com>"))
    assert any(
        "%40" in p for p in gmail_problems("smtps://marlon:abcdefghijklmnop@smtp.gmail.com:465", "x@y.z")
    )
