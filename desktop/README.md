# 25x125 desktop program (Windows)

25x125 as one Windows program for one person. No account, no sign-in, no hosting, no Stripe. Everything runs on your own computer and only your computer can reach it.

The program bundles four parts and starts them for you:

| Part | What it is | Where it comes from |
| --- | --- | --- |
| Database | PostgreSQL 16.13 with PostGIS 3.5.3 | EDB's Windows build and the OSGeo PostGIS bundle |
| Python | Python 3.12.10 with the engine's packages | python.org's Windows build (NuGet package) |
| Node.js | Node.js 22.23.4 (`node.exe` only), runs the app's server | nodejs.org |
| Engine | The FastAPI rules and feasibility engine (`engine/`) and the data loaders (`jobs/`) | this repository |
| App | The Next.js screens (`web/`) | this repository |

You don't install Docker, Python, Node or Postgres. They are inside the program.

## Install

You need Windows 10 or 11 (64-bit), about 1.5 GB free for the program and 4 GB for the data, and an internet connection for the data loads.

1. Open https://github.com/GeddyLifeson/25x125/releases in your browser.
2. Under the newest release whose name starts with "25x125 desktop", click `25x125-Setup-<version>.exe` to download it (about 310 MB).
3. Double-click the downloaded file.
4. Windows may show a blue box: "Windows protected your PC". The program isn't signed with a paid code-signing certificate, so Windows doesn't recognise it yet. Click **More info**, then **Run anyway**.
5. The installer runs by itself in a few seconds. It doesn't ask for an administrator password; it installs for your Windows user only, in `C:\Users\<you>\AppData\Local\Programs\25x125`. It adds 25x125 to the Start menu and the desktop.
6. Open 25x125 from the Start menu or the desktop icon.
7. If you use Norton or another antivirus program, add the exclusions in [Antivirus warnings](#antivirus-warnings-norton) first. Otherwise it may stop the program and leave the window stuck.

## First start: the data load

On the first start the program creates its database and starts copying the public data in. The window shows each step as it happens. It never stays blank: until the app answers, and whenever something stops, it shows what is happening, with an **Open logs folder** button.

- The first load takes 1 to 2 hours and fills about 3 GB of disk.
- You can open the app (the **Open 25x125** button) and look around while it runs. The map, the lot list and the scores fill in when the load finishes, because the score runs last.
- Keep 25x125 open until the window says "Data load finished". If you close it early, sources already loaded are kept and the rest load the next time you open it.
- Windows Firewall should not ask anything, because the parts talk to each other only inside your computer (127.0.0.1). If it does ask, click **Cancel**; nothing needs outside access to the program.

## Everyday use

- Open 25x125 from the Start menu. The map and list open first.
- Everything from the web version works: address search, the parcel page, feasibility with every input editable, deals and the outreach log, saved searches, saved edits, the PDF one-pager and every CSV export. There is no sign-in and no Pro check: you are the owner, on Pro, with nothing to pay.
- Downloads (CSV, PDF) ask where to save the file.
- Links to sources and to city pages open in your normal browser.

## Keeping the data fresh

The data comes from the free public portals (Chicago Data Portal, Cook County data catalog, Census Bureau, FHFA, FRED). The program never reads them while you click around; it copies them into its own database.

- **Daily update.** When you open 25x125 and the last update is more than 20 hours old, it pulls what is new (sales, permits, zoning changes, signals, lots for sale, and so on) and rescores every lot. This usually takes 5 to 20 minutes. While the program stays open it checks again every hour.
- **Monthly full reload.** Every 30 days it also reloads the tax-year sources (parcels, building characteristics, assessed values, boundaries, rents). That takes 1 to 2 hours again.
- The program only updates while it is open. If you don't open it for a week, the first start after that runs the update.
- The **Data** menu has **Update data now**, **Full reload** and **Stop the data load**. **Status and data log** shows what ran and when.
- If a portal is down, that one source fails and the others still load. The status window names it, and the next update tries it again. Screens show a note when a nightly source is more than 36 hours old.

## Where things are on your computer

| What | Where |
| --- | --- |
| The program | `C:\Users\<you>\AppData\Local\Programs\25x125` |
| Your database, settings and logs | `C:\Users\<you>\AppData\Roaming\25x125` (File menu, **Open data folder**) |
| Logs | `...\Roaming\25x125\logs` (File menu, **Open logs folder**) |

The database folder (`pgdata`) holds your deals, saved edits and outreach log as well as the public data. Back up the whole `Roaming\25x125` folder while 25x125 is closed if you want a copy.

## Update to a new version

Download the newer `25x125-Setup-<version>.exe` from the releases page and run it. It replaces the program and keeps your data folder, so your deals and edits stay.

## Uninstall

Windows Settings, **Apps**, **Installed apps**, 25x125, **Uninstall**. Your data folder stays in `AppData\Roaming\25x125` in case you reinstall; delete that folder by hand to remove the data too.

## Antivirus warnings (Norton)

25x125 isn't code-signed yet, and very few people run it. Norton's Behavioral Protection may flag `25x125.exe` as `IDP.Generic` and stop it or its parts. `IDP.Generic` is a general warning Norton gives to new, unsigned programs it hasn't seen before. It doesn't name any specific malware. The program's code is all in this repository. It runs PostgreSQL (signed by EnterpriseDB), Python (signed by the Python Software Foundation) and Node.js (signed by the OpenJS Foundation) from its own folder, and it doesn't start with Windows.

To let it run, open Norton and add two exclusions. The menu names below are from Norton 360 and may differ a little in other versions:

1. Open Norton. Click **Settings** (on the **My Norton** screen, under **Device Security**, click **Open** first).
2. Click **Antivirus**, then the **Scans and Risks** tab.
3. Next to **Items to Exclude from Scans**, click **Configure**, then **Add Folders**. Add `C:\Users\<you>\AppData\Local\Programs\25x125` with "Include subfolders" checked. Then add `C:\Users\<you>\AppData\Roaming\25x125` the same way. Click **OK**.
4. Next to **Items to Exclude from Auto-Protect, Script Control, SONAR and Download Intelligence Detection**, click **Configure** and add the same two folders. Behavioral Protection is SONAR, so this step is the one that stops the warning. Click **OK**, then **Apply**.
5. If Norton already quarantined the file: **Security**, **History**, show **Quarantine**, select `25x125.exe`, then **Restore** (or **Options**, then **Restore & exclude this file**).
6. Close 25x125 if it's open and start it again.

To get Norton to clear the file for everyone, report it as a false positive. This is free and takes 2 to 5 days:

1. Go to https://submit.norton.com and pick the false positive (incorrect detection) option.
2. Upload `C:\Users\<you>\AppData\Local\Programs\25x125\25x125.exe`, or the installer file.
3. For the detection name, enter `IDP.Generic (Behavioral Protection)`. Give the download link https://github.com/GeddyLifeson/25x125/releases.

## If something goes wrong

- **The window says something stopped, or stays on the status page**: an antivirus program may have stopped part of it (see above). Click **Open logs folder**.
- **"25x125 could not start"**: close it and open it again. If the message comes back, send the files in the logs folder (`desktop.log`, `postgres-server.log`, `engine.log`, `web.log`).
- **Port in use**: the database uses port 54325 when it is free and picks another one when it isn't, so it doesn't collide with a Docker database on 5432. The engine and the app pick free ports on every start.
- **The map is blank but the list works**: the background map comes from OpenFreeMap over the internet. Lots still draw on a plain background when it can't load.

## Limits of the desktop version

- One person on one computer. Teammates, invites and the Stripe billing screens are not used.
- Nothing runs while the program is closed, so the data is as fresh as the last time it was open.
- Results are estimates, not tax, legal, zoning or appraisal advice. This is the same as the web version.

## For developers

How it's built:

- `desktop/src/main.js` is the Electron main process. It creates the database on first start (`initdb` with a random password, listening on 127.0.0.1 only), starts Postgres with `pg_ctl`, runs `desktop_bootstrap.py` (creates the database, applies `db/migrations`, checks PostGIS and PROJ), starts the engine with `LOCAL_MODE=1` and a random `ENGINE_SHARED_SECRET`, starts the Next.js standalone server with the bundled, signed `node.exe` (Node.js 22.23.4), and shows the app in the window once it answers. Until then, and whenever a part stops, the window shows the status page. It runs `python -m jobs.nightly` for data loads and stops everything on quit.
- Local mode: `LOCAL_MODE=1` on the engine turns on `POST /auth/local-session`, which returns the one local user as owner of the `default` organization on Pro at no charge. The web app (`web/lib/session.ts`) uses it in place of the session cookie, and `web/proxy.ts` drops the sign-in redirects. `APP_ENV=production` refuses local mode.
- Map tiles come from the engine (`GET /tiles/{layer}/{z}/{x}/{y}`, the same PostGIS functions Martin serves), so the desktop build needs no Martin. The hosted setup still uses Martin.
- `desktop/scripts/prepare-runtime.mjs` builds `desktop/build/runtime`: it downloads the pinned Postgres, PostGIS and Python archives (SHA-256 checked), installs the Python packages from `pyproject.toml`, copies the engine and data, and builds the web app. On Mac or Linux only the `app` and `web` parts run (`node scripts/prepare-runtime.mjs app web`).
- `.github/workflows/desktop.yml` builds on `windows-latest`, starts the unpacked program with `--self-test --self-test-load` (database, PostGIS, migrations, engine, app, local mode, tiles, one real loader), installs it silently, and uploads the installer as a workflow artifact. On main it also publishes a GitHub Release named `desktop-v<version>` (the version in `desktop/package.json`) the first time that version builds; bump the version to publish a new release.

Build it on Windows yourself (needs Node 22 and Git):

```
cd desktop
npm ci
node scripts/prepare-runtime.mjs
npx electron-builder --win nsis --publish never
```

The installer lands in `desktop\dist`. To run without installing: `npm start` after `prepare-runtime`.

Self-test switches: `--self-test` (start everything, check, stop, exit 0 or 1), `--self-test-load` (also run the boundary loader), `--self-test-out=<file>` (write the report as JSON), `--data-dir=<folder>` (use another data folder).
