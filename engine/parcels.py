"""Parcel search and the parcel page's facts, read from Postgres (never from the portals)."""

import re

SITE_FIELDS = [
    "zone_class", "zone_share", "zone_class_2", "zone_share_2", "lot_sqft", "frontage_ft", "depth_ft", "lot_source",
    "historic_rating", "landmark_name", "tif_name", "cta_rail_ft", "metra_ft", "transit_served", "adu_zone",
    "special_district", "aro_area", "pedestrian_street", "enterprise_zone", "opportunity_zone_2018", "fire_limits",
    "open_violations", "last_violation_date", "vacant_building_311", "vacant_lot_311", "scofflaw",
    "city_owned_status", "demolition_notice_date", "foreclosures_half_mile_5y", "nearest_new_construction_ft",
    "stories", "footprint_units", "hearing_fines_3y", "vacant_building_fine_due", "environmental_hold",
    "foreclosed_rental_date", "exempt_owner",
]  # fmt: skip


def normalize_address(q: str) -> str:
    q = " ".join(q.upper().replace(",", " ").replace(".", " ").split())
    q = re.sub(r"\bCHICAGO\b.*$", "", q).strip()
    for a, b in (("STREET", "ST"), ("AVENUE", "AVE"), ("BOULEVARD", "BLVD"), ("PLACE", "PL"), ("NORTH", "N"),
                 ("SOUTH", "S"), ("WEST", "W"), ("EAST", "E"), ("COURT", "CT"), ("DRIVE", "DR"), ("ROAD", "RD")):  # fmt: skip
        q = re.sub(rf"\b{a}\b", b, q)
    return q


def search(conn, q: str, limit: int = 10) -> list[dict]:
    digits = re.sub(r"\D", "", q)
    if len(digits) in (10, 14) and len(digits) >= len(q.replace("-", "").strip()) - 1:
        rows = conn.execute(
            """select a.pin, a.address, a.zip, ps.zone_class, ps.lot_sqft from parcel_address a
               left join parcel_site ps on ps.pin = a.pin
               where a.pin like %s order by a.pin limit %s""",
            (digits[:10] + "%", limit),
        ).fetchall()
    else:
        addr = normalize_address(q)
        sql = """select a.pin, a.address, a.zip, ps.zone_class, ps.lot_sqft from parcel_address a
                   left join parcel_site ps on ps.pin = a.pin where {where} limit %s"""
        rows = conn.execute(
            sql.format(where="a.address like %s order by a.address, a.pin"), (addr + "%", limit)
        ).fetchall()
        if not rows:  # typo or a different street suffix: closest addresses by trigram similarity
            rows = conn.execute(
                sql.format(where="a.address %% %s order by a.address <-> %s, a.pin"), (addr, addr, limit)
            ).fetchall()
    return [{"pin": r[0], "address": r[1], "zip": r[2], "zone_class": r[3], "lot_sqft": float(r[4]) if r[4] else None}
            for r in rows]  # fmt: skip


def parcel(conn, pin: str) -> dict | None:
    row = conn.execute(
        f"""select p.pin, p.pin10, a.address, a.zip, p.class, p.ward, p.community_area_name, p.nbhd_code,
                   p.tract_geoid, st_y(p.geom), st_x(p.geom), p.tax_year, {", ".join("ps." + f for f in SITE_FIELDS)},
                   lu.use_now, lu.units_now, bf.lots, bf.multi_lots, sp.finished_at
            from parcel p
            left join parcel_address a on a.pin = p.pin
            left join parcel_site ps on ps.pin = p.pin
            left join lot_use lu on lu.pin10 = p.pin10
            left join block_face bf on bf.block_face = lu.block_face
            left join source_pull sp on sp.id = p.source_pull_id
            where p.pin = %s or p.pin10 = %s order by p.tax_year desc, p.pin limit 1""",
        (pin, pin[:10]),
    ).fetchone()
    if not row:
        return None
    head = ["pin", "pin10", "address", "zip", "class", "ward", "community_area", "nbhd_code", "tract", "lat", "lon",
            "tax_year", *SITE_FIELDS, "use_now", "units_now", "block_face_lots", "block_face_multi_lots", "pulled_at"]  # fmt: skip
    out = dict(zip(head, row, strict=True))
    for k, v in list(out.items()):
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif v is not None and type(v).__name__ == "Decimal":
            out[k] = float(v)
    out["recent_sales"] = [
        {"date": d.isoformat(), "price": float(p), "deed_type": t}
        for d, p, t in conn.execute(
            "select sale_date, sale_price, deed_type from sale where left(pin, 10) = %s order by sale_date desc limit 5",
            (out["pin10"],),
        ).fetchall()
    ]
    out["signals"] = [
        {"kind": k, "date": d.isoformat() if d else None, "status": s, "detail": det, "match": m}
        for k, d, s, det, m in conn.execute(
            """select kind, signal_date, status, left(detail, 160), match_method from parcel_signal
               where pin10 = %s order by signal_date desc nulls last limit 25""",
            (out["pin10"],),
        ).fetchall()
    ]
    out["sources"] = {
        "parcel": "Cook County Assessor parcel universe (pabr-t5kh)",
        "zoning": "City of Chicago zoning districts (dj47-wfun)",
        "signals": "City of Chicago violations, 311, scofflaw, city land, demolition notices",
    }
    return out


LOT_SORTS = {"score": "s.score desc", "return": "s.return_on_cost_p25 desc nulls last",
             "upside": "s.by_right_units - coalesce(s.units_now, 0) desc", "lot": "ps.lot_sqft desc nulls last"}  # fmt: skip
LOT_COLUMNS = ["pin10", "pin", "address", "zip", "community_area", "zone_class", "lot_sqft", "score", "zoning_upside",
               "profit", "acquisition", "location", "incentives", "penalties", "units_now", "by_right_units",
               "units_priced", "sale_per_unit", "sale_comps", "land", "total_cost", "profit_central", "profit_p25",
               "return_on_cost", "return_on_cost_p25", "max_land_price", "details", "computed_on", "lat", "lon"]  # fmt: skip


def lots(conn, *, community_area: int | None = None, zone_prefix: str | None = None, min_score: float = 0,
         min_units: int = 0, signal: str | None = None, for_sale: bool = False, vacant: bool = False,
         sort: str = "score", limit: int = 100, offset: int = 0) -> list[dict]:  # fmt: skip
    """The list screen: scored lots with filters, from parcel_score (jobs/score_parcels.py)."""
    where, args = ["s.score >= %s"], [min_score]
    if community_area:
        where.append("p.community_area_num = %s")
        args.append(community_area)
    if zone_prefix:
        where.append("ps.zone_class like %s")
        args.append(zone_prefix.upper() + "%")
    if min_units:
        where.append("s.by_right_units >= %s")
        args.append(min_units)
    if signal:
        where.append("s.details->'signals' ? %s")
        args.append(signal)
    if for_sale:
        where.append("s.details->'signals' ? 'city_owned_for_sale'")
    if vacant:
        where.append("s.details->'signals' ? 'vacant_land'")
    rows = conn.execute(
        f"""select s.pin10, s.pin, a.address, a.zip, p.community_area_name, ps.zone_class, ps.lot_sqft, s.score,
                   s.zoning_upside, s.profit, s.acquisition, s.location, s.incentives, s.penalties, s.units_now,
                   s.by_right_units, s.units_priced, s.sale_per_unit, s.sale_comps, s.land, s.total_cost,
                   s.profit_central, s.profit_p25, s.return_on_cost, s.return_on_cost_p25, s.max_land_price,
                   s.details, s.computed_on, st_y(p.geom), st_x(p.geom)
            from parcel_score s
            join parcel_site ps on ps.pin = s.pin
            join lateral (select * from parcel x where x.pin = s.pin order by x.tax_year desc limit 1) p on true
            left join parcel_address a on a.pin = s.pin
            where {" and ".join(where)}
            order by {LOT_SORTS.get(sort, LOT_SORTS["score"])}, s.pin10
            limit %s offset %s""",
        [*args, limit, offset],
    ).fetchall()
    out = []
    for r in rows:
        row = dict(zip(LOT_COLUMNS, r, strict=True))
        for k, v in row.items():
            if hasattr(v, "is_finite"):  # Decimal
                row[k] = float(v)
        row["computed_on"] = row["computed_on"].isoformat()
        out.append(row)
    return out
