-- Street centerline segments (City of Chicago pr57-gg9e) with address ranges per side. A block face is one
-- segment and one side, which matches "the same side of the street between the two nearest intersecting
-- streets" better than the hundred block.
create table street_segment (
  trans_id text primary key,
  pre_dir text,
  street_name text,
  street_type text,
  l_from integer, l_to integer, l_parity text,
  r_from integer, r_to integer, r_parity text,
  f_cross text,
  t_cross text,
  class text,
  geom geometry(MultiLineString, 4326),
  source_pull_id bigint not null references source_pull (id)
);
create index street_segment_name on street_segment (street_name, pre_dir);
create index street_segment_geom on street_segment using gist (geom);

alter table lot_use add column block_face_source text;  -- 'segment' or 'hundred block'
