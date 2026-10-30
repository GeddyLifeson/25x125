"""Build lot_use: what stands on each lot now and which block face it fronts.

Units come from the Assessor class of each PIN on the lot: condo unit PINs (299) count one each, 2-6 unit
apartment buildings (211, 212) take the apartments count from residential characteristics, houses and
townhouses count one, and 7+ unit classes (313-399) count at least 7. Vacant classes (100, 190, 241) mark
a vacant lot. The block face is the lot's address street, side (even or odd) and hundred block, which
stands in for "the same side of the street between the two nearest intersecting streets". Unit numbers
after the street type are dropped.
Run: python -m jobs.build_lot_use
"""

from core.db import connect

SQL = """
truncate lot_use;
with types as (
  -- Unit numbers follow the street type ('2845 W SHAKESPEARE AVE 2'); cut them off.
  select 'AVE|ST|BLVD|RD|DR|PL|CT|PKWY|TER|WAY|LN|HWY|SQ|PLZ|CIR|ROW|XING|TRL' as street_types
),
apts as (
  select distinct on (pin) pin, apartments from building_char
  where apartments > 0 order by pin, tax_year desc, card
),
pin_units as (
  select p.pin10, p.pin, p.class,
    case
      when p.class = '299' then 1
      when p.class in ('211', '212') then coalesce(a.apartments, case p.class when '211' then 2 else 1 end)
      when p.class in ('202', '203', '204', '205', '206', '207', '208', '209', '210', '234', '278', '295') then 1
      when p.class ~ '^3(1[3-9]|[2-9][0-9])$' then greatest(coalesce(a.apartments, 7), 7)
      else 0
    end as units,
    p.class in ('100', '190', '241') as vacant
  from parcel p left join apts a on a.pin = p.pin
),
lot as (
  select pin10, sum(units) as units, bool_and(vacant) as vacant, min(pin) as first_pin
  from pin_units group by pin10
)
insert into lot_use (pin10, use_now, units_now, block_face)
select l.pin10,
       case when l.vacant then 'vacant' when l.units >= 2 then 'multi' when l.units = 1 then 'single'
            else 'other' end,
       l.units,
       (select m[2] || ' ' || m[3] || '|' || case when m[1]::bigint % 2 = 0 then 'even' else 'odd' end
               || '|' || (m[1]::bigint / 100 * 100)
        from types, parcel_address a,
             regexp_match(regexp_replace(upper(a.address), '\\s(' || street_types || ')\\s.*$', ' \\1'),
                          '^([0-9]+)[A-Z]?(?:-[0-9]+)?\\s+([NSEW])\\s+(.+)$') m
        where a.pin = l.first_pin and m is not null)
from lot l;
"""


def run(url: str | None = None) -> int:
    with connect(url) as conn:
        conn.execute(SQL)
        return conn.execute("select count(*) from lot_use").fetchone()[0]


if __name__ == "__main__":
    print(f"lots: {run():,}")
