"""Read a Site from Postgres: parcel_site joined to what stands on the lot and its block face."""

from engine.zoning import Site

SQL = """
select ps.pin, ps.zone_class, ps.zone_class_2, ps.zone_share_2, ps.lot_sqft, ps.frontage_ft, ps.lot_source, ps.zone_share, ps.transit_served,
       ps.adu_zone, ps.adu_limits, ps.special_district, ps.historic_rating, ps.landmark_name, ps.fire_limits,
       lu.use_now, lu.units_now, bf.lots, bf.multi_lots, bf.single_lots, bf.two_flat_lots, bf.vacant_lots
from parcel_site ps
left join lot_use lu on lu.pin10 = ps.pin10
left join block_face bf on bf.block_face = lu.block_face
where {where}
"""
FIELDS = ["pin", "zone_class", "zone_class_2", "zone_share_2", "lot_sqft", "frontage_ft", "lot_source", "zone_share", "transit_served",
          "adu_zone", "adu_limits", "special_district", "historic_rating", "landmark_name", "fire_limits",
          "use_now", "units_now", "block_lots", "block_multi_lots", "block_single_lots", "block_two_flat_lots",
          "block_vacant_lots"]  # fmt: skip


def _site(row) -> Site:
    values = dict(zip(FIELDS, row, strict=True))
    for k in ("lot_sqft", "frontage_ft", "zone_share", "zone_share_2"):
        if values[k] is not None:
            values[k] = float(values[k])
    return Site(**values)


def site_by_pin(conn, pin: str) -> Site | None:
    """A 14-digit PIN, or a 10-digit lot PIN (first unit on the lot)."""
    where = "ps.pin = %s" if len(pin) == 14 else "ps.pin10 = %s order by ps.pin limit 1"
    row = conn.execute(SQL.format(where=where), (pin,)).fetchone()
    return _site(row) if row else None
