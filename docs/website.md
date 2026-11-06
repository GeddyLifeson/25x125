# The public website

25x125 runs as a website on Hugging Face Spaces at `https://<hf-user>-25x125.hf.space`. It is free (CPU basic:
2 CPUs, 16 GB memory) and needs no card.

## How it works

- `deploy/space/Dockerfile` builds one container: PostgreSQL 16 with PostGIS, the engine and the web app on
  port 3000. It clones this repo at the commit being deployed.
- `.github/workflows/website.yml` runs on every push to `main`. `scripts/deploy_space.py` creates the Space
  `<hf-user>/25x125` if needed, sets its secrets and uploads `deploy/space` with the commit pinned, so the
  Space rebuilds (about 10 minutes).
- `scripts/space.py` starts the container. The Space's disk is wiped on each restart, so every start restores
  the weekly data snapshot (release `data-snapshot`, about 380 MB, 10-20 minutes) and shows a progress page
  meanwhile. It then pulls the daily update from the portals while it runs.
- Your own work (deals, saved searches, edits, feedback) is copied every 5 minutes, when it changed, to the
  private dataset `<hf-user>/25x125-data` and put back on the next start.
- The site runs in single-user mode (`LOCAL_MODE=1`, as on the desktop). `SITE_PASSWORD` keeps strangers out:
  each browser asks for it once and remembers it for 90 days (`web/proxy.ts`).

## Setup (once)

1. Make a free account at https://huggingface.co/join.
2. Make a write token at https://huggingface.co/settings/tokens/new?tokenType=write and save it as the repo
   secret `HF_TOKEN` (GitHub, Settings, Secrets and variables, Actions).
3. Save the site's password as the repo secret `SITE_PASSWORD`.
4. Run the Website workflow (Actions tab), or push to `main`.

To change the password, change the `SITE_PASSWORD` secret and run the Website workflow again.

## Limits of the free Space

- It sleeps after 48 hours with no visits. The next visit wakes it; the data restore then takes 10-20 minutes.
- Saved work made in the last 5 minutes before a restart can be lost.
- Paid upgrades exist on the Space's settings page. Don't turn any on without checking the cost first.
