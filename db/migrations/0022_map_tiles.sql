-- Vector tile functions for the map, served by Martin (martin/config.yaml) as function sources.
-- Each takes (z, x, y) and returns one Mapbox vector tile. They read the nightly tables only.
-- plpgsql so the table references are checked when a tile is drawn, not when the migration runs
-- (lot_for_sale arrives in a later-numbered migration).

-- Lots, coloured by development score. Zoom 14 and closer: every lot's shape.
-- Farther out: one point per lot, only for lots scoring at or above a floor, so tiles stay small:
-- zoom 13: 20 or more; zoom 11-12: 40 or more; zoom 10 and out: 50 or more.
create or replace function lot_tiles(z integer, x integer, y integer)
returns bytea language plpgsql stable parallel safe as $$
declare
  env geometry := st_tileenvelope(z, x, y);
  env4326 geometry := st_transform(env, 4326);
  floor_score numeric := case when z >= 13 then 20 when z >= 11 then 40 else 50 end;
  tile bytea;
begin
  if z >= 14 then
    select st_asmvt(t, 'lots', 4096, 'g') into tile from (
      select st_asmvtgeom(st_transform(sh.geom, 3857), env, 4096, 16, true) g,
             s.pin10, round(s.score)::int score, s.by_right_units units,
             coalesce((s.details->>'fast_path')::boolean, false) fp, ps.zone_class zone,
             p.community_area_num ca,
             (select string_agg(v, ',') from jsonb_array_elements_text(s.details->'signals') v) sig
      from parcel_shape sh
      join parcel_score s on s.pin10 = sh.pin10
      join parcel_site ps on ps.pin = s.pin
      join parcel p on p.pin = s.pin
      where sh.geom && env4326
    ) t;
  else
    select st_asmvt(t, 'lots', 4096, 'g') into tile from (
      select st_asmvtgeom(st_transform(p.geom, 3857), env, 4096, 16, true) g,
             s.pin10, round(s.score)::int score, s.by_right_units units,
             coalesce((s.details->>'fast_path')::boolean, false) fp, ps.zone_class zone,
             p.community_area_num ca,
             (select string_agg(v, ',') from jsonb_array_elements_text(s.details->'signals') v) sig
      from parcel_score s
      join parcel p on p.pin = s.pin
      join parcel_site ps on ps.pin = s.pin
      where s.score >= floor_score and p.geom && env4326
    ) t;
  end if;
  return coalesce(tile, ''::bytea);
end $$;

-- Median land sale per lot square foot, by Assessor neighborhood and by community area (jobs/build_land_values.py).
create or replace function land_value_tiles(z integer, x integer, y integer)
returns bytea language plpgsql stable parallel safe as $$
declare
  env geometry := st_tileenvelope(z, x, y);
  tile bytea;
begin
  select st_asmvt(t, 'land_value', 4096, 'g') into tile from (
    select st_asmvtgeom(st_transform(b.geom, 3857), env, 4096, 64, true) g,
           lv.geo_kind kind, lv.geo_id code, b.name,
           round(lv.median_per_lot_sqft, 2)::real per_sqft, lv.sales,
           round(vac.median_per_lot_sqft, 2)::real vacant_per_sqft, coalesce(vac.sales, 0) vacant_sales,
           lv.first_sale::text first_sale, lv.last_sale::text last_sale, lv.computed_on::text computed_on
    from land_value lv
    join boundary b on b.code = lv.geo_id
      and b.kind = case lv.geo_kind when 'nbhd' then 'assessor_nbhd' else 'community_area' end
    left join land_value vac on vac.geo_kind = lv.geo_kind and vac.geo_id = lv.geo_id and vac.kind = 'vacant'
    where lv.kind = 'all' and b.geom && st_transform(env, 4326)
  ) t;
  return coalesce(tile, ''::bytea);
end $$;

-- City lots for sale (ChiBlockBuilder, city land inventory) and Cook County Land Bank listings
-- (jobs/load_lots_for_sale.py). Only rows marked for sale.
create or replace function lot_for_sale_tiles(z integer, x integer, y integer)
returns bytea language plpgsql stable parallel safe as $$
declare
  env geometry := st_tileenvelope(z, x, y);
  tile bytea;
begin
  select st_asmvt(t, 'lots_for_sale', 4096, 'g') into tile from (
    select st_asmvtgeom(st_transform(l.geom, 3857), env, 4096, 16, true) g,
           l.source src, l.source_id id, l.pin10, l.address, l.status,
           l.asking_price::real ask, l.minimum_bid::real min_bid, l.city_land_value::real city_value,
           l.deadline::text deadline, l.offer_round round, l.apply_url, l.listed_on::text listed_on,
           l.lot_sqft::real sqft, l.zoning, sp.finished_at::date::text pulled_on
    from lot_for_sale l
    left join source_pull sp on sp.id = l.source_pull_id
    where l.for_sale and l.geom is not null and l.geom && st_transform(env, 4326)
  ) t;
  return coalesce(tile, ''::bytea);
end $$;
