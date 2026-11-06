"""Create or update the 25x125 website on Hugging Face Spaces (docs/website.md). Run by
.github/workflows/website.yml; works the same from any computer with HF_TOKEN set:

    python scripts/deploy_space.py --ref <commit or branch>

It makes the Space <hf-user>/25x125 (public, Docker, free CPU), sets its secrets HF_TOKEN and SITE_PASSWORD,
and uploads deploy/space with the Dockerfile pinned to the commit, which makes the Space rebuild.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPACE_DIR = ROOT / "deploy" / "space"
SPACE_NAME = "25x125"


def pinned_dockerfile(text: str, ref: str, repo_url: str) -> str:
    out = []
    for line in text.splitlines():
        if line.startswith("ARG REF="):
            line = f"ARG REF={ref}"
        elif line.startswith("ARG REPO="):
            line = f"ARG REPO={repo_url}"
        out.append(line)
    return "\n".join(out) + "\n"


def site_url(space_id: str) -> str:
    return "https://" + space_id.replace("/", "-").replace("_", "-").replace(".", "-").lower() + ".hf.space"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="main", help="commit or branch the Space builds")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "GeddyLifeson/25x125"))
    a = ap.parse_args(argv)

    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set.", file=sys.stderr)
        return 1
    api = HfApi(token=token)
    user = api.whoami()["name"]
    space_id = f"{user}/{SPACE_NAME}"
    api.create_repo(space_id, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
    api.add_space_secret(space_id, "HF_TOKEN", token)
    password = os.environ.get("SITE_PASSWORD")
    if password:
        api.add_space_secret(space_id, "SITE_PASSWORD", password)
    else:
        print("::warning::No SITE_PASSWORD secret: the website is open to anyone with the link.")

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "README.md").write_text((SPACE_DIR / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
        docker = pinned_dockerfile(
            (SPACE_DIR / "Dockerfile").read_text(encoding="utf-8"), a.ref, f"https://github.com/{a.repo}.git"
        )
        (t / "Dockerfile").write_text(docker, encoding="utf-8")
        api.upload_folder(
            folder_path=tmp,
            repo_id=space_id,
            repo_type="space",
            commit_message=f"Build {a.repo}@{a.ref[:12]}",
        )
    print(f"Website: {site_url(space_id)}  (builds in about 10 minutes, then loads the data)")
    print(f"Build log: https://huggingface.co/spaces/{space_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
