-- Map overlays on each lot outside Chicago (flood zone, historic district, ADU area, ...), as
-- [{"kind": "flood", "name": "AE"}, ...]. Filled by jobs/build_region.py from the overlay table.
alter table parcel_site add column if not exists overlays jsonb;
