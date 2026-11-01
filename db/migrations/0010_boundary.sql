-- Boundaries for maps and pricing fallbacks: community areas, wards, 2020 census tracts and Assessor
-- neighborhoods. Codes match the parcel columns (community_area_num, ward, census_tract_geoid, nbhd_code).

create table boundary (
  kind text not null,                      -- 'community_area', 'ward', 'tract_2020', 'assessor_nbhd'
  code text not null,
  name text,
  geom geometry(MultiPolygon, 4326) not null,
  source_pull_id bigint not null references source_pull (id),
  primary key (kind, code)
);
create index boundary_geom on boundary using gist (geom);

-- Community areas that share an edge: the next fallback step when a community area has too few comps.
create view community_area_neighbor as
select a.code as code, b.code as neighbor_code, b.name as neighbor_name
from boundary a join boundary b
  on a.kind = 'community_area' and b.kind = 'community_area' and a.code <> b.code
 and st_intersects(a.geom, b.geom)
 and st_length(st_intersection(st_boundary(a.geom), st_boundary(b.geom))::geography) > 50;
