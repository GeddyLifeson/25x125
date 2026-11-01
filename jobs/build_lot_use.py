"""Build lot_use: what stands on each lot now and which block face it fronts.

Units come from the Assessor class of each PIN on the lot: condo unit PINs (299) count one each unless the
condo data marks them as a parking space or common area, 2-6 unit apartment buildings (211, 212) take the
apartments count summed over every building card (so a coach house on a second card counts), houses and
townhouses count one per card, and 7+ unit classes (313-399) count at least 7. Vacant classes (100, 190, 241) mark
a vacant lot. The block face is the street centerline segment (pr57-gg9e) of the lot's address street whose address
range holds its house number, plus the side (even or odd): "the same side of the street between the two
nearest intersecting streets". Where no segment matches, the street, side and hundred block stand in.
Unit numbers after the street type are dropped.
Run: python -m jobs.build_lot_use
"""

from core.db import connect

SQL = """
truncate lot_use;
with types as (
  -- Unit numbers follow the street type ('2845 W SHAKESPEARE AVE 2'); cut them off.
  select 'AVE|ST|BLVD|RD|DR|PL|CT|PKWY|TER|WAY|LN|HWY|SQ|PLZ|CIR|ROW|XING|TRL' as street_types
),
latest as (
  select pin, max(tax_year) as tax_year from building_char group by pin
),
cards as (
  -- Every building card on the PIN in its latest year: a coach house is a second card.
  select b.pin, sum(case when b.apartments > 0 then b.apartments
                         when b.class in ('202', '203', '204', '205', '206', '207', '208', '209', '210', '234',
                                          '278', '295') then 1
                         else 0 end) as units
  from building_char b join latest l on l.pin = b.pin and l.tax_year = b.tax_year
  group by b.pin
),
condo as (
  select distinct on (pin) pin, is_parking_space or is_common_area as not_a_home
  from condo_char order by pin, tax_year desc
),
pin_units as (
  select p.pin10, p.pin, p.class,
    case
      when p.class = '299' then case when c.not_a_home then 0 else 1 end
      when p.class in ('211', '212') then coalesce(nullif(k.units, 0), case p.class when '211' then 2 else 1 end)
      when p.class in ('202', '203', '204', '205', '206', '207', '208', '209', '210', '234', '278', '295')
        then greatest(coalesce(k.units, 1), 1)
      when p.class ~ '^3(1[3-9]|[2-9][0-9])$' then greatest(coalesce(k.units, 7), 7)
      else 0
    end as units,
    p.class in ('100', '190', '241') as vacant
  from parcel p left join cards k on k.pin = p.pin left join condo c on c.pin = p.pin
),
lot as (
  select pin10, sum(units) as units, bool_and(vacant) as vacant, min(pin) as first_pin
  from pin_units group by pin10
),
addr as (
  select l.pin10, m[1]::bigint as num, m[2] as dir, m[3] as street,
         coalesce(substring(m[3] from '^(.*) (?:' || street_types || ')$'), m[3]) as street_name,
         substring(m[3] from ' (' || street_types || ')$') as street_type
  from lot l
  cross join types
  join parcel_address a on a.pin = l.first_pin
  cross join lateral regexp_match(
    regexp_replace(upper(a.address), '\\s(' || street_types || ')\\s.*$', ' \\1'),
    '^([0-9]+)[A-Z]?(?:-[0-9]+)?\\s+([NSEW])\\s+(.+)$') m
  where m is not null
),
seg as (
  -- The centerline segment of the address street whose range on one side holds the house number.
  select ad.pin10, x.face
  from addr ad
  cross join lateral (
    select 'seg ' || g.trans_id || '|' || case when ad.num % 2 = 0 then 'even' else 'odd' end as face
    from street_segment g
    where g.street_name = ad.street_name and g.pre_dir = ad.dir
      and g.street_type is not distinct from ad.street_type
      and ((ad.num between least(g.l_from, g.l_to) and greatest(g.l_from, g.l_to)
            and g.l_parity = case when ad.num % 2 = 0 then 'E' else 'O' end)
        or (ad.num between least(g.r_from, g.r_to) and greatest(g.r_from, g.r_to)
            and g.r_parity = case when ad.num % 2 = 0 then 'E' else 'O' end))
    order by g.trans_id
    limit 1
  ) x
)
insert into lot_use (pin10, use_now, units_now, block_face, block_face_source)
select l.pin10,
       case when l.vacant then 'vacant' when l.units >= 2 then 'multi' when l.units = 1 then 'single'
            else 'other' end,
       l.units,
       coalesce(seg.face, ad.dir || ' ' || ad.street || '|' || case when ad.num % 2 = 0 then 'even' else 'odd' end
                || '|' || (ad.num / 100 * 100)),
       case when seg.face is not null then 'segment' when ad.pin10 is not null then 'hundred block' end
from lot l
left join addr ad on ad.pin10 = l.pin10
left join seg on seg.pin10 = l.pin10;
"""


def run(url: str | None = None) -> int:
    with connect(url) as conn:
        conn.execute(SQL)
        return conn.execute("select count(*) from lot_use").fetchone()[0]


if __name__ == "__main__":
    print(f"lots: {run():,}")
