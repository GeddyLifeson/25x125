"""Deploy 25x125 to Fly.io with the database on Supabase (docs/deploy.md).

Run from the repo root, on Windows, Mac or Linux:
    python -m scripts.deploy --dry-run        print every command, run nothing
    python -m scripts.deploy                  create apps, set secrets, migrate, deploy, schedule the nightly job
    python -m scripts.deploy --first-load     same, then start the one-off full load (yearly steps included)

Other options: --only engine,tiles,web,nightly  --env-file PATH  --ci (no app creation, no secrets: code only)
Needs flyctl (https://fly.io/docs/flyctl/install/) and `fly auth login`. Uses the standard library only.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGION = "iad"  # Ashburn, Virginia: next to Supabase us-east-1

APPS = {
    "engine": {
        "name": "x25x125-engine",
        "config": "deploy/fly.engine.toml",
        "dockerfile": "deploy/engine.Dockerfile",
        "public": False,
        "secrets": [
            "DATABASE_URL",
            "ENGINE_SHARED_SECRET",
            "EMAIL_SERVER",
            "EMAIL_FROM",
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
            "STRIPE_PRICE_PRO_MONTHLY",
            "STRIPE_PRICE_FOUNDING_MONTHLY",
            "SENTRY_DSN",
            "ADMIN_EMAILS",
            "SOCRATA_APP_TOKEN",
            "CENSUS_API_KEY",
        ],
    },
    "tiles": {
        "name": "x25x125-tiles",
        "config": "deploy/fly.tiles.toml",
        "dockerfile": "deploy/tiles.Dockerfile",
        "public": False,
        "secrets": ["DATABASE_URL"],
    },
    "web": {
        "name": "x25x125-web",
        "config": "deploy/fly.web.toml",
        "dockerfile": "deploy/web.Dockerfile",
        "public": True,
        "secrets": ["ENGINE_SHARED_SECRET", "APP_URL", "SENTRY_DSN"],
    },
}
# Deploy order: the engine first (its release command runs the migrations), then the tile server (needs the
# tile functions), then the web app.
ORDER = ["engine", "tiles", "web"]
REQUIRED = ["DATABASE_URL", "ENGINE_SHARED_SECRET", "APP_URL", "EMAIL_SERVER", "EMAIL_FROM"]
NIGHTLY_NAME = "nightly"
NIGHTLY_MEMORY_MB = 2048  # jobs.score_parcels peaked at 1,609 MB on 604,808 lots (docs/deploy.md)
NIGHTLY_CMD = ["python", "-m", "jobs.nightly", "--skip-yearly"]
FIRST_LOAD_CMD = ["python", "-m", "jobs.nightly"]


class Runner:
    """Runs flyctl, or with dry_run prints the command and returns an empty result."""

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.fly = shutil.which("fly") or shutil.which("flyctl")

    def show(self, args: list[str], stdin_note: str = "") -> None:
        print(
            "  $ " + " ".join(_quote(a) for a in args) + (f"   < {stdin_note}" if stdin_note else ""),
            flush=True,
        )

    def run(
        self, args: list[str], stdin: str | None = None, stdin_note: str = "", capture: bool = False
    ) -> str:
        self.show(args, stdin_note)
        if self.dry_run:
            return ""
        res = subprocess.run(args, check=False, cwd=ROOT, input=stdin, text=True, capture_output=capture)
        if res.returncode != 0:
            if capture:
                sys.stderr.write(res.stdout + res.stderr)
            sys.exit(f"Stopped: the command above failed (exit {res.returncode}).")
        return res.stdout if capture else ""

    def query(self, args: list[str]) -> str | None:
        """A read-only flyctl call whose answer decides the next step. None in a dry run."""
        if self.dry_run:
            self.show(args)
            return None
        res = subprocess.run(args, check=False, cwd=ROOT, text=True, capture_output=True)
        return res.stdout if res.returncode == 0 else None


def _quote(a: str) -> str:
    return f'"{a}"' if (" " in a or not a) else a


def read_env(path: Path) -> dict[str, str]:
    """KEY=VALUE lines; # comments and blank lines skipped; surrounding quotes removed."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def check_env(env: dict[str, str]) -> list[str]:
    """Problems that would break production. Empty list = good to go."""
    problems = [f"{k} is empty" for k in REQUIRED if not env.get(k)]
    url = env.get("DATABASE_URL", "")
    if url:
        u = urlparse(url)
        if u.port == 6543:
            problems.append(
                "DATABASE_URL uses port 6543 (Supabase transaction pooler). Use the direct connection or the "
                "session pooler, both port 5432 (docs/deploy.md)."
            )
        if "sslmode=" not in url:
            problems.append("DATABASE_URL should end with ?sslmode=require (Supabase needs TLS)")
    if env.get("APP_URL", "").startswith("http://"):
        problems.append("APP_URL should start with https://")
    secret = env.get("ENGINE_SHARED_SECRET", "")
    if secret.startswith("replace-"):
        problems.append(
            "ENGINE_SHARED_SECRET is still the example placeholder; make one (see the example file)"
        )
    elif secret and len(secret) < 32:
        problems.append(
            "ENGINE_SHARED_SECRET is shorter than 32 characters; make a new one (see the example)"
        )
    if (
        env.get("EMAIL_SERVER")
        and "resend" in env["EMAIL_SERVER"]
        and "@smtp.resend.com" not in env["EMAIL_SERVER"]
    ):
        problems.append("EMAIL_SERVER for Resend looks like smtps://resend:<api key>@smtp.resend.com:465")
    return problems


def image_ref(app: str, label: str) -> str:
    return f"registry.fly.io/{app}:{label}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deploy 25x125 to Fly.io (docs/deploy.md).")
    ap.add_argument("--dry-run", action="store_true", help="print every command without running any")
    ap.add_argument("--first-load", action="store_true", help="start the one-off full load after deploying")
    ap.add_argument("--only", default="engine,tiles,web,nightly", help="comma list: engine,tiles,web,nightly")
    ap.add_argument("--env-file", default=".env.production", help="secrets file (default .env.production)")
    ap.add_argument(
        "--org", default=None, help="Fly organization for new apps (default: FLY_ORG or personal)"
    )
    ap.add_argument(
        "--ci", action="store_true", help="code only: skip app creation and secrets (GitHub Actions)"
    )
    a = ap.parse_args(argv)
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    unknown = only - set(ORDER) - {"nightly"}
    if unknown:
        sys.exit(f"Unknown --only part: {', '.join(sorted(unknown))}")
    r = Runner(a.dry_run)
    if a.dry_run:
        print("Dry run: nothing is created, changed or deployed.\n")

    # 1. flyctl installed and signed in.
    print("1. flyctl")
    if not r.fly:
        if not a.dry_run:
            sys.exit(
                "flyctl is not installed. Windows (PowerShell): iwr https://fly.io/install.ps1 -useb | iex\n"
                "Mac: brew install flyctl. Linux: curl -L https://fly.io/install.sh | sh. Then: fly auth login"
            )
        print("  flyctl not found; the dry run prints the commands as `fly ...`")
        r.fly = "fly"
    fly = r.fly
    who = r.query([fly, "auth", "whoami"])
    if not a.dry_run and not who:
        sys.exit("flyctl is not signed in. Run: fly auth login (or set FLY_API_TOKEN)")
    if who:
        print(f"  signed in as {who.strip()}")

    # 2. Secrets file.
    env: dict[str, str] = {}
    if not a.ci:
        print("\n2. Secrets file")
        path = ROOT / a.env_file
        if not path.exists():
            example = ROOT / ".env.production.example"
            if not a.dry_run:
                sys.exit(
                    f"{a.env_file} not found. Copy .env.production.example to {a.env_file} and fill it in."
                )
            print(f"  {a.env_file} not found; the dry run reads .env.production.example instead")
            path = example
        env = read_env(path)
        problems = check_env(env)
        for p in problems:
            print(f"  problem: {p}")
        if problems and not a.dry_run:
            sys.exit(f"Fix {a.env_file} first.")
        if not problems:
            print(f"  {path.name}: required values present")
    org = a.org or env.get("FLY_ORG") or "personal"

    label = "deploy-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], check=False, cwd=ROOT, text=True, capture_output=True
        )
        if sha.returncode == 0 and sha.stdout.strip():
            label += "-" + sha.stdout.strip()
    except OSError:  # git not installed: the timestamp alone labels the image
        pass

    # 3. Apps.
    if not a.ci:
        print("\n3. Apps (created if missing)")
        listed = r.query([fly, "apps", "list", "--json"])
        existing = {x.get("Name") or x.get("name") for x in json.loads(listed)} if listed else set()
        for part in ORDER:
            name = APPS[part]["name"]
            if part in only or (part == "engine" and "nightly" in only):
                if name in existing:
                    print(f"  {name}: exists")
                else:
                    r.run([fly, "apps", "create", name, "--org", org])

    # 4. Secrets, staged so they apply with the deploy below (values go through stdin, never the command line).
    if not a.ci:
        print("\n4. Secrets (fly secrets import --stage; values read from stdin and never printed)")
        for part in ORDER:
            if part not in only:
                continue
            app = APPS[part]
            pairs = {k: env[k] for k in app["secrets"] if env.get(k)}
            if not pairs:
                continue
            body = "".join(f"{k}={v}\n" for k, v in pairs.items())
            r.run(
                [fly, "secrets", "import", "--stage", "--app", app["name"]],
                stdin=body,
                stdin_note=", ".join(pairs),
            )

    # 5-6. Deploy. The engine's release command (deploy/fly.engine.toml) runs python -m db.migrate against the
    # production DATABASE_URL inside Fly's network before the new version starts.
    print("\n5. Migrations: run by the engine deploy's release command (python -m db.migrate)")
    print("\n6. Deploy (remote builder; one Machine per app)")
    for part in ORDER:
        if part not in only:
            continue
        app = APPS[part]
        cmd = [
            fly,
            "deploy",
            ".",
            "--app",
            app["name"],
            "--config",
            app["config"],
            "--dockerfile",
            app["dockerfile"],
        ]
        cmd += ["--remote-only", "--ha=false", "--image-label", label]
        if not app["public"]:
            cmd.append("--no-public-ips")
        r.run(cmd)

    engine_image = image_ref(APPS["engine"]["name"], label)
    if "engine" not in only:
        # Nightly or first load without an engine deploy: use the image the engine runs now.
        out = r.query([fly, "image", "show", "--app", APPS["engine"]["name"], "--json"])
        engine_image = _current_image(out) or engine_image

    # 7. One-off full load (yearly steps too). Started before the schedule so the scheduled run, if it starts
    # at once, finds the run lock taken and stops (jobs/nightly.py).
    if a.first_load:
        print("\n7. First full load (one-off Machine, removed when it exits)")
        r.run(
            [
                fly,
                "machine",
                "run",
                engine_image,
                "--app",
                APPS["engine"]["name"],
                "--name",
                f"first-load-{label[7:22]}",
            ]
            + [
                "--region",
                REGION,
                "--vm-cpu-kind",
                "shared",
                "--vm-cpus",
                "1",
                "--vm-memory",
                str(NIGHTLY_MEMORY_MB),
            ]
            + ["--restart", "no", "--rm", "--detach", "--metadata", "x25_role=first-load", "--"]
            + FIRST_LOAD_CMD
        )
        print(f"  follow it: fly logs --app {APPS['engine']['name']}")
        if not a.dry_run:
            time.sleep(20)

    # 8. Daily scheduled Machine: created once, then moved to the new image on every deploy.
    if "nightly" in only:
        print("\n8. Nightly job (scheduled Machine, daily, stops after the run)")
        listed = r.query([fly, "machine", "list", "--app", APPS["engine"]["name"], "--json"])
        machine = _find_machine(listed, NIGHTLY_NAME)
        if machine:
            r.run(
                [
                    fly,
                    "machine",
                    "update",
                    machine,
                    "--app",
                    APPS["engine"]["name"],
                    "--image",
                    engine_image,
                    "--yes",
                ]
            )
        else:
            if a.dry_run:
                print(
                    "  (if a Machine named nightly exists, the script runs `fly machine update <id> --image ...`)"
                )
            r.run(
                [fly, "machine", "run", engine_image, "--app", APPS["engine"]["name"], "--name", NIGHTLY_NAME]
                + ["--region", REGION, "--schedule", "daily", "--restart", "no"]
                + ["--vm-cpu-kind", "shared", "--vm-cpus", "1", "--vm-memory", str(NIGHTLY_MEMORY_MB)]
                + ["--detach", "--metadata", "x25_role=nightly", "--"]
                + NIGHTLY_CMD
            )

    print("\nDone." if not a.dry_run else "\nDry run finished. Nothing was changed.")
    if not a.dry_run and env.get("APP_URL"):
        print(f"Check: {env['APP_URL'].rstrip('/')}/api/health")
    return 0


def _find_machine(listed: str | None, name: str) -> str | None:
    if not listed:
        return None
    for m in json.loads(listed) or []:
        if m.get("name") == name:
            return m.get("id")
    return None


def _current_image(out: str | None) -> str | None:
    if not out:
        return None
    data = json.loads(out)
    items = data if isinstance(data, list) else [data]
    for it in items:
        reg, repo, tag = it.get("Registry"), it.get("Repository"), it.get("Tag")
        if reg and repo and tag:
            return f"{reg}/{repo}:{tag}"
    return None


if __name__ == "__main__":
    sys.exit(main())
