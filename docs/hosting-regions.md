# Hosting the new regions for free (2026-11-18)

Marlon's rule: no spending, hosting included. This page sizes the job and lists the free options.

## How big each region is

Measured on 2026-11-17, Postgres database size after a full load and score:

| Region | Database |
|---|---|
| Chicago (sandbox copy, partial) | 468 MB |
| Tampa | about 470 MB (loaded in the default database during the build) |
| Orlando | 421 MB |
| Jacksonville | 1,459 MB |
| Miami | 80 MB (before the countywide comps) |
| Houston | 1,626 MB |
| Dallas | 955 MB |
| Austin | 1,030 MB |
| San Antonio | 1,852 MB |
| Atlanta | 526 MB |
| All nine new regions | about 8.4 GB |

Free managed Postgres tiers hold 0.5 to 1 GB per project, so the larger regions don't fit any of them.
The free options are a machine Marlon already owns, or a free cloud VM with its own disk.

## Option 1: Marlon's PC (works today)

The desktop app already serves Chicago to the internet through Tailscale Funnel (free). From the next desktop release
(after 0.1.5), `"region": "tampa"` in `%APPDATA%\25x125\config.json` points the app at that region and its own database
(`x25_tampa`). Chicago's data stays in `x25x125` and comes back when the setting is removed.

- Cost: $0.
- Limit: one region at a time, and only while the PC is on and the app is open.
- Loading a region on the PC takes 10 to 40 minutes per city and needs the free data files
  (`docs/regions.md`, "Loading a region").

## Option 2: Oracle Cloud Always Free VM (all regions at once)

Oracle's Always Free tier includes an Arm VM with up to 4 cores, 24 GB of memory and 200 GB of disk, with no
time limit. That holds every region's database with room to spare. Each region runs as its own engine
process (`REGION=<id>`, its own `DATABASE_URL`) behind one web server, using the existing Docker Compose files.

- Cost: $0 if the account stays inside the Always Free limits.
- What only Marlon can do: create the Oracle Cloud account. Oracle asks for a card to verify identity at
  sign-up. Choose the Always Free shapes only, and don't upgrade the account to Pay As You Go.
- Oracle says it may reclaim Always Free VMs that sit idle. The nightly jobs keep the machine busy each night.
- Arm VMs are often out of stock in busy home regions. Retrying later, or picking a quieter home region at
  sign-up, usually works.

## Recommendation for now

Use option 1 to show a region to someone this week. Set up option 2 only when Marlon wants several regions
live at once, and confirm with him before the sign-up because it asks for a card.
