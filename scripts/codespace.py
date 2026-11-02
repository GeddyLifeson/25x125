"""Run 25x125 in a GitHub Codespace: one person, no sign-in, nothing to host.

The devcontainer (.devcontainer/) calls this script:
  python scripts/codespace.py setup            once, when the codespace is made: packages and the web build
  python scripts/codespace.py start            every start: runs `run` in the background and returns
  python scripts/codespace.py status --follow  every time the editor connects: progress, then the app's address

By hand, in the codespace terminal:
  python scripts/codespace.py status           what is running and the app's address
  python scripts/codespace.py update           pull what is new from the portals now (5-20 minutes)
  python scripts/codespace.py full-reload      reload everything from the portals (1-2 hours)
  python scripts/codespace.py restart          stop and start the engine and the app

First start: the database is empty, so `run` downloads the data snapshot that the "Data snapshot" workflow
publishes weekly on the repo's Releases page (release `data-snapshot`) and restores it. That takes about 5-15
minutes in place of the 1-2 hour load. With no snapshot it runs the full load from the portals instead.
Later starts pull what is new when the last update is more than 20 hours old. The engine runs with
LOCAL_MODE=1 (engine/auth.py), as in the desktop program: no sign-in, one local owner on Pro.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".codespace"
LOG = STATE_DIR / "run.log"
PIDFILE = STATE_DIR / "run.pid"
STATE = STATE_DIR / "state.json"
SNAPSHOT_TAG = "data-snapshot"
DEFAULT_REPO = "GeddyLifeson/25x125"
ENGINE_PORT = 8000
WEB_PORT = 3000
UPDATE_AFTER_HOURS = 20


# ---------- small helpers (tested in tests/test_codespace.py) ----------


def app_url(env: dict[str, str] | None = None) -> str:
    """The address the browser uses: the codespace's forwarded port, or localhost outside a codespace."""
    env = os.environ if env is None else env
    name, domain = env.get("CODESPACE_NAME"), env.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")
    if name and domain:
        return f"https://{name}-{WEB_PORT}.{domain}"
    return f"http://localhost:{WEB_PORT}"


def snapshot_parts(assets: list[dict]) -> list[dict]:
    """The dump's assets in order: one `x25x125.dump`, or `x25x125.dump.part-NN` pieces when it passed 2 GB."""
    whole = [a for a in assets if a["name"] == "x25x125.dump"]
    if whole:
        return whole
    return sorted((a for a in assets if a["name"].startswith("x25x125.dump.part-")), key=lambda a: a["name"])


def update_due(state: dict, now: dt.datetime, hours: float = UPDATE_AFTER_HOURS) -> bool:
    last = state.get("last_update_at")
    if not last:
        return True
    return now - dt.datetime.fromisoformat(last) > dt.timedelta(hours=hours)


def repo_name(env: dict[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    return env.get("GITHUB_REPOSITORY") or DEFAULT_REPO


# ---------- state and logging ----------


def load_state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(**changes) -> None:
    state = load_state() | changes
    STATE_DIR.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def log(msg: str) -> None:
    line = f"{dt.datetime.now().strftime('%H:%M:%S')}  {msg}"
    print(line, flush=True)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def sh(args: list[str], **kw) -> int:
    log("$ " + " ".join(args))
    return subprocess.run(args, check=False, **kw).returncode


# ---------- setup ----------


def setup() -> int:
    """Python packages, web packages and the web build. Safe to run again (after a git pull, say)."""
    STATE_DIR.mkdir(exist_ok=True)
    if sh([sys.executable, "-m", "pip", "install", "--quiet", "-e", "."], cwd=ROOT):
        return 1
    if sh(["npm", "ci", "--no-audit", "--no-fund"], cwd=ROOT / "web"):
        return 1
    return build_web()


def head_commit() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return r.stdout.strip()


def build_web() -> int:
    code = sh(["npm", "run", "build"], cwd=ROOT / "web")
    if code == 0:
        save_state(web_built_for=head_commit())
    return code


def pull_latest() -> bool:
    """On main with no local edits, bring in what was merged since. True when new commits came in."""
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if branch != "main" or dirty.stdout.strip():
        log(
            f"Not pulling new code (branch {branch or '?'}{', local edits' if dirty.stdout.strip() else ''})."
        )
        return False
    before = head_commit()
    if sh(["git", "pull", "--ff-only", "--quiet", "origin", "main"], cwd=ROOT):
        log("Could not pull the latest code; using what is here.")
        return False
    return head_commit() != before


# ---------- database and data ----------


def db_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/x25x125")


def wait_for_db(timeout_s: int = 180) -> None:
    import psycopg

    end = time.time() + timeout_s
    while True:
        try:
            with psycopg.connect(db_url(), connect_timeout=5) as conn:
                conn.execute("select 1")
                return
        except psycopg.OperationalError:
            if time.time() > end:
                raise
            time.sleep(2)


def has_data() -> bool:
    """True when parcels are loaded or anything was saved (deals, edits, searches). Then it is never replaced."""
    import psycopg

    with psycopg.connect(db_url()) as conn:
        for table in ("parcel_site", "deal", "deal_event", "saved_search", "saved_override"):
            if conn.execute("select to_regclass(%s)", (table,)).fetchone()[0] is None:
                continue
            if conn.execute(f"select exists (select 1 from {table})").fetchone()[0]:
                return True
    return False


def github_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def download(url: str, dest: Path, append: bool) -> None:
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    done, last = 0, time.time()
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "ab" if append else "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if time.time() - last > 15:
                last = time.time()
                pct = f" ({done * 100 // total}%)" if total else ""
                log(f"  downloaded {done >> 20} MB{pct}")


def restore_snapshot() -> bool:
    """Download the newest data snapshot and restore it into an empty database. False when there is none."""
    import psycopg

    repo = repo_name()
    try:
        # SNAPSHOT_RELEASE_URL points at another release's API address (a test server, say).
        default = f"https://api.github.com/repos/{repo}/releases/tags/{SNAPSHOT_TAG}"
        rel = github_json(os.environ.get("SNAPSHOT_RELEASE_URL") or default)
    except Exception as e:  # noqa: BLE001 - no snapshot yet (404) or GitHub unreachable: fall back to the load
        log(f"No data snapshot found on {repo} ({e}).")
        return False
    parts = snapshot_parts(rel.get("assets", []))
    meta_asset = next((a for a in rel.get("assets", []) if a["name"] == "snapshot.json"), None)
    if not parts:
        log("The data-snapshot release has no dump file.")
        return False
    meta = {}
    if meta_asset:
        try:
            req = urllib.request.Request(meta_asset["browser_download_url"])
            with urllib.request.urlopen(req, timeout=30) as r:
                meta = json.load(r)
        except Exception:  # noqa: BLE001
            meta = {}
    size_mb = sum(a.get("size", 0) for a in parts) >> 20
    log(f"Downloading the data snapshot from {meta.get('built_at', 'the Releases page')} ({size_mb} MB).")
    dump = STATE_DIR / "snapshot.dump"
    for i, a in enumerate(parts):
        download(a["browser_download_url"], dump, append=i > 0)
    if meta.get("sha256"):
        h = hashlib.sha256()
        with open(dump, "rb") as f:
            while chunk := f.read(1 << 20):
                h.update(chunk)
        if h.hexdigest() != meta["sha256"]:
            log("The snapshot download is damaged (checksum differs). Falling back to the full load.")
            dump.unlink(missing_ok=True)
            return False

    # Recreate the database empty (template0, no PostGIS yet: the dump creates its own extensions), then restore.
    info = psycopg.conninfo.conninfo_to_dict(db_url())
    name = info.get("dbname") or "x25x125"
    admin = psycopg.conninfo.make_conninfo(db_url(), dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity where datname = %s and pid <> pg_backend_pid()",
            (name,),
        )
        conn.execute(f'drop database if exists "{name}"')
        conn.execute(f"create database \"{name}\" encoding 'UTF8' template template0")
        # Roles live outside the dump; the grants in it need the restricted role (db/migrations/0023_account.sql).
        conn.execute(
            "do $$ begin if not exists (select 1 from pg_roles where rolname = 'x25_app') then "
            "create role x25_app nologin; end if; end $$"
        )
    log("Restoring the snapshot into the database (5-10 minutes).")
    code = sh(["pg_restore", "--no-owner", "--jobs", "2", "--dbname", db_url(), str(dump)])
    dump.unlink(missing_ok=True)
    if code != 0:
        log(f"pg_restore finished with code {code}; checking what came in.")
    sh(["vacuumdb", "--analyze-only", "--quiet", "--dbname", db_url()])
    if not has_data():
        log("The restore left no parcels. Falling back to the full load.")
        return False
    stamp = meta.get("built_at") or now_utc().isoformat()
    save_state(snapshot_restored_at=now_utc().isoformat(), last_update_at=stamp, last_full_at=stamp)
    log("Snapshot restored.")
    return True


def migrate() -> None:
    sh([sys.executable, "-m", "db.migrate"], cwd=ROOT)


def data_load(full: bool) -> int:
    args = [sys.executable, "-m", "jobs.nightly", "--year", str(dt.date.today().year)]
    if not full:
        args.append("--skip-yearly")
    log("Full data load from the portals (1-2 hours)." if full else "Pulling what is new (5-20 minutes).")
    started = now_utc().isoformat()
    code = sh(args, cwd=ROOT)
    save_state(last_update_at=started, **({"last_full_at": started} if full else {}), last_load_code=code)
    log(f"Data load finished (code {code}).")
    return code


# ---------- engine and web app ----------


def service_env() -> dict[str, str]:
    url = app_url()
    return os.environ | {
        "LOCAL_MODE": "1",
        "APP_ENV": "development",
        "DATABASE_URL": db_url(),
        "ENGINE_URL": f"http://127.0.0.1:{ENGINE_PORT}",
        "TILES_URL": f"http://127.0.0.1:{ENGINE_PORT}/tiles",
        "APP_URL": url,
        "APP_ORIGINS": url.split("://", 1)[1],
        "NODE_ENV": "production",
        "PYTHONUNBUFFERED": "1",
    }


def start_engine() -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "engine.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(ENGINE_PORT),
    ]
    out = open(STATE_DIR / "engine.log", "ab")  # noqa: SIM115 - held open for the child's life
    return subprocess.Popen(cmd, cwd=ROOT, env=service_env(), stdout=out, stderr=subprocess.STDOUT)


def start_web() -> subprocess.Popen:
    next_bin = ROOT / "web" / "node_modules" / "next" / "dist" / "bin" / "next"
    cmd = ["node", str(next_bin), "start", "-p", str(WEB_PORT), "-H", "0.0.0.0"]
    out = open(STATE_DIR / "web.log", "ab")  # noqa: SIM115
    return subprocess.Popen(cmd, cwd=ROOT / "web", env=service_env(), stdout=out, stderr=subprocess.STDOUT)


def wait_http(url: str, timeout_s: int) -> bool:
    end = time.time() + timeout_s
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status < 500:
                    return True
        except Exception:  # noqa: BLE001 - not up yet
            time.sleep(1)
    return False


# ---------- the background run ----------


def run() -> int:
    STATE_DIR.mkdir(exist_ok=True)
    save_state(phase="starting", app_ready=False)
    log("25x125 is starting.")
    if pull_latest():
        log("New code came in from main; reinstalling and rebuilding the app (about 3 minutes).")
        setup()
    elif load_state().get("web_built_for") != head_commit():
        log("The app's build is older than the code; rebuilding (about 2 minutes).")
        build_web()

    save_state(phase="database")
    log("Waiting for the database.")
    wait_for_db()
    fresh = not has_data()
    restored = False
    if fresh:
        save_state(phase="snapshot")
        log("The database is empty. This first start fills it.")
        restored = restore_snapshot()
    migrate()

    engine, web = start_engine(), start_web()
    ok = wait_http(f"http://127.0.0.1:{ENGINE_PORT}/health", 180) and wait_http(
        f"http://127.0.0.1:{WEB_PORT}/", 180
    )
    save_state(phase="running", app_ready=ok)
    if ok:
        log(f"25x125 is up: {app_url()}")
    else:
        log(
            "The engine or the app did not answer in 3 minutes. See .codespace/engine.log and .codespace/web.log."
        )

    # Data: the full load when the snapshot was missing, otherwise the daily update when it is due.
    loader = None
    if fresh and not restored:
        save_state(phase="loading")
        loader = subprocess.Popen([sys.executable, __file__, "full-reload"], cwd=ROOT)
    elif update_due(load_state(), now_utc()):
        save_state(phase="updating")
        loader = subprocess.Popen([sys.executable, __file__, "update"], cwd=ROOT)

    # Keep the engine and the app running; restart either one if it stops.
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    while not stopping:
        time.sleep(5)
        if loader is not None and loader.poll() is not None:
            loader = None
            save_state(phase="running")
        if engine.poll() is not None:
            log(f"The engine stopped (code {engine.returncode}); starting it again.")
            engine = start_engine()
        if web.poll() is not None:
            log(f"The app stopped (code {web.returncode}); starting it again.")
            web = start_web()
    for p in (engine, web, loader):
        if p is not None and p.poll() is None:
            p.terminate()
    return 0


def running_pid() -> int | None:
    """The background run's process id, if it is alive. After a codespace restart the old id may belong to
    another process, so check its command line too."""
    try:
        pid = int(PIDFILE.read_text())
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (OSError, ValueError):
        return None
    return pid if b"codespace.py" in cmdline and b"run" in cmdline else None


def start() -> int:
    """Start `run` detached from this shell, so it keeps going after the devcontainer's start command ends."""
    STATE_DIR.mkdir(exist_ok=True)
    if pid := running_pid():
        print(f"25x125 is already running (process {pid}).")
        return 0
    # A fresh log and state for this start, so `status --follow` doesn't report the last start's "up" line.
    if LOG.exists():
        LOG.replace(LOG.with_suffix(".log.old"))
    save_state(phase="starting", app_ready=False)
    with open(LOG, "ab") as out:
        p = subprocess.Popen(
            [sys.executable, __file__, "run"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PIDFILE.write_text(str(p.pid))
    print("25x125 is starting in the background. Progress: python scripts/codespace.py status --follow")
    return 0


def restart() -> int:
    if pid := running_pid():
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            if running_pid() is None:
                break
            time.sleep(1)
    return start()


def status(follow: bool) -> int:
    pos = 0
    shown_ready = False
    began = time.time()
    print("25x125 in this codespace. Log: .codespace/run.log\n", flush=True)
    while True:
        if LOG.exists():
            with open(LOG, "rb") as f:
                f.seek(pos)
                text = f.read()
                pos = f.tell()
            if text:
                sys.stdout.write(text.decode("utf-8", "replace"))
                sys.stdout.flush()
        state = load_state()
        if state.get("app_ready") and not shown_ready:
            shown_ready = True
            print(f"\nOpen 25x125: {app_url()}", flush=True)
            if state.get("phase") in ("loading", "updating"):
                print("A data load is running in the background; the log above shows its steps.", flush=True)
        gone = time.time() - began > 20 and running_pid() is None
        if follow and not state.get("app_ready") and gone:
            print("\n25x125 stopped before the app came up. The log above says why.", flush=True)
            print("Start it again: python scripts/codespace.py start", flush=True)
            return 1
        if not follow:
            if not running_pid():
                print("25x125 is not running. Start it: python scripts/codespace.py start")
            return 0
        if shown_ready and state.get("phase") == "running":
            print(
                "\nYou can close this terminal. The app keeps running while the codespace is on.", flush=True
            )
            return 0
        time.sleep(2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "command", choices=["setup", "start", "run", "status", "update", "full-reload", "restart"]
    )
    ap.add_argument(
        "--follow", action="store_true", help="with status: keep showing progress until the app is up"
    )
    a = ap.parse_args(argv)
    if a.command == "setup":
        return setup()
    if a.command == "start":
        return start()
    if a.command == "run":
        return run()
    if a.command == "status":
        return status(a.follow)
    if a.command == "restart":
        return restart()
    return data_load(full=a.command == "full-reload")


if __name__ == "__main__":
    sys.exit(main())
