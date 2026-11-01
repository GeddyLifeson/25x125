-- Zoning map amendments introduced in City Council, from the City Clerk's eLMS public API (2010 on).
-- from_district and to_district stay empty until the ordinance PDFs are read (they are scans).
create table rezoning (
  record_number text primary key,    -- e.g. O2026-0029356 (SO = substitute ordinance)
  matter_id text not null,
  title text not null,
  map_no text,
  app_no text,                       -- T1 suffix = Type 1 (with plans); A- prefix = filed by the alderman
  type1 boolean not null,
  alderman_filed boolean not null,
  address text,                      -- first address in the title, ranges cut to their first number
  addresses text,                    -- every address the title lists
  intro_date date,
  final_date date,
  status text,
  sub_status text,
  from_district text,
  to_district text,
  pin10 text,
  source_pull_id bigint references source_pull (id)
);
create index on rezoning (pin10);

alter table parcel_site
  add column last_rezoning_date date,       -- introduced date of the latest map amendment on the lot
  add column last_rezoning_status text;
