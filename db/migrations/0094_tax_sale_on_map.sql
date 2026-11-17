-- Lots in the next Cook County Annual Tax Sale show on the map and in the list filter.
-- The map tiles carry 'tax_sale' in the lot's signal list while the sale date is today or later.
create index if not exists parcel_site_tax_sale on parcel_site (pin) where tax_sale_date is not null;

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
             concat_ws(',', (select string_agg(v, ',') from jsonb_array_elements_text(s.details->'signals') v),
                       case when ps.tax_sale_date >= current_date then 'tax_sale' end) sig
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
             concat_ws(',', (select string_agg(v, ',') from jsonb_array_elements_text(s.details->'signals') v),
                       case when ps.tax_sale_date >= current_date then 'tax_sale' end) sig
      from parcel_score s
      join parcel p on p.pin = s.pin
      join parcel_site ps on ps.pin = s.pin
      where s.score >= floor_score and p.geom && env4326
    ) t;
  end if;
  return coalesce(tile, ''::bytea);
end $$;
