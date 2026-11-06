"""Runs 25x125 as a public website on Hugging Face Spaces (deploy/space, docs/website.md).

One container holds everything: PostgreSQL with PostGIS, the engine and the web app on port 3000. The Space's
disk is wiped on every restart, so each start restores the weekly data snapshot (scripts/codespace.py does
that, as in a codespace) and then puts back your own work (deals, saved searches, edits, feedback) from a
private Hugging Face dataset. While the site runs, that work is copied to the dataset every 5 minutes when it
changed.

Space secrets (set by .github/workflows/website.yml):
  HF_TOKEN       write token; reads and writes the private dataset <user>/25x125-data
  SITE_PASSWORD  the password the site asks for (web/proxy.ts); without it the site is open to anyone
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codespace as cs  # noqa: E402

PGDATA = Path(os.environ.get("PGDATA", Path.home() / "pgdata"))
PGBIN = Path(os.environ.get("PGBIN", "/usr/lib/postgresql/16/bin"))
BACKUP = cs.STATE_DIR / "user-data.sql"
BACKUP_NAME = "user-data.sql"
BACKUP_EVERY_S = 300
# Tables that hold what people do in the app, in an order that satisfies the foreign keys.
USER_TABLES = [
    "account_user",
    "org",
    "membership",
    "deal",
    "deal_event",
    "saved_search",
    "saved_override",
    "feedback",
]


def dataset_repo() -> str | None:
    """<owner>/25x125-data, the owner taken from the Space's id (SPACE_ID is <owner>/<space>)."""
    if os.environ.get("BACKUP_REPO"):
        return os.environ["BACKUP_REPO"]
    space = os.environ.get("SPACE_ID", "")
    return f"{space.split('/')[0]}/25x125-data" if "/" in space else None


def start_postgres() -> None:
    if not (PGDATA / "PG_VERSION").exists():
        PGDATA.mkdir(parents=True, exist_ok=True)
        pwfile = cs.STATE_DIR / "pw"
        pwfile.write_text("postgres")
        subprocess.run(
            [PGBIN / "initdb", "-D", PGDATA, "-U", "postgres", "--pwfile", pwfile, "-E", "UTF8", "--locale=C.UTF-8"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        pwfile.unlink()
        with open(PGDATA / "postgresql.conf", "a") as f:
            f.write(
                "\nlisten_addresses = '127.0.0.1'\nunix_socket_directories = '/tmp'\nshared_buffers = 1GB\n"
                "maintenance_work_mem = 1GB\nwork_mem = 32MB\nmax_wal_size = 4GB\neffective_cache_size = 8GB\n"
                "fsync = off\nsynchronous_commit = off\nfull_page_writes = off\n"
            )
    subprocess.run(
        [PGBIN / "pg_ctl", "-D", PGDATA, "-l", cs.STATE_DIR / "postgres.log", "-w", "start"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    import psycopg

    with psycopg.connect("postgresql://postgres:postgres@127.0.0.1:5432/postgres", autocommit=True) as conn:
        if not conn.execute("select 1 from pg_database where datname = 'x25x125'").fetchone():
            conn.execute("create database x25x125")


def dump_user_data(dest: Path) -> bool:
    """Your own work as SQL inserts that skip rows already there. False when pg_dump failed."""
    import psycopg

    with psycopg.connect(cs.db_url()) as conn:
        tables = [t for t in USER_TABLES if conn.execute("select to_regclass(%s)", (t,)).fetchone()[0]]
    args = ["pg_dump", "--data-only", "--inserts", "--on-conflict-do-nothing", "--no-owner", "-f", str(dest)]
    for t in tables:
        args += ["-t", t]
    return subprocess.run([*args, cs.db_url()], check=False).returncode == 0


def restore_user_data() -> None:
    """After the snapshot restore and the migrations, before the engine starts: put back your own work."""
    repo, token = dataset_repo(), os.environ.get("HF_TOKEN")
    if not (repo and token):
        cs.log("No HF_TOKEN: deals and saved work are not kept between restarts of the site.")
        return
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=token)
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    try:
        path = hf_hub_download(repo, BACKUP_NAME, repo_type="dataset", token=token, local_dir=cs.STATE_DIR)
    except Exception as e:  # noqa: BLE001 - first start: nothing saved yet
        cs.log(f"No saved work to put back yet ({type(e).__name__}).")
        return
    code = cs.sh(["psql", "-q", "-v", "ON_ERROR_STOP=0", "-d", cs.db_url(), "-f", path])
    cs.log("Saved work put back." if code == 0 else f"Putting back saved work finished with code {code}.")


def backup_loop() -> None:
    repo, token = dataset_repo(), os.environ.get("HF_TOKEN")
    if not (repo and token):
        return
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    last = None
    while True:
        time.sleep(BACKUP_EVERY_S)
        if not cs.load_state().get("app_ready"):
            continue
        try:
            tmp = BACKUP.with_suffix(".tmp")
            if not dump_user_data(tmp):
                continue
            digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
            if digest == last:
                continue
            os.replace(tmp, BACKUP)
            api.upload_file(
                path_or_fileobj=str(BACKUP),
                path_in_repo=BACKUP_NAME,
                repo_id=repo,
                repo_type="dataset",
                commit_message="Saved work",
            )
            last = digest
        except Exception as e:  # noqa: BLE001 - try again next round
            cs.log(f"Could not save your work to {repo} ({type(e).__name__}: {e}); trying again in 5 minutes.")


def main() -> int:
    cs.STATE_DIR.mkdir(exist_ok=True)
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/x25x125")
    os.environ.setdefault("PGHOST", "127.0.0.1")
    start_postgres()

    plain_migrate = cs.migrate

    def migrate_then_restore() -> None:
        plain_migrate()
        restore_user_data()

    cs.migrate = migrate_then_restore
    threading.Thread(target=backup_loop, daemon=True).start()
    return cs.run()


if __name__ == "__main__":
    sys.exit(main())
