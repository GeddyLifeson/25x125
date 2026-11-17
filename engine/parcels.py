"""Parcel search and the parcel page's facts, read from Postgres (never from the portals)."""

import re
from datetime import date

SITE_FIELDS = [
    "zone_class", "zone_share", "zone_class_2", "zone_share_2", "lot_sqft", "frontage_ft", "depth_ft", "lot_source",
    "historic_rating", "landmark_name", "tif_name", "cta_rail_ft", "metra_ft", "transit_served", "adu_zone",
    "special_district", "aro_area", "pedestrian_street", "enterprise_zone", "opportunity_zone_2018", "fire_limits",
    "open_violations", "last_violation_date", "vacant_building_311", "vacant_lot_311", "scofflaw",
    "city_owned_status", "demolition_notice_date", "foreclosures_half_mile_5y", "nearest_new_construction_ft",
    "stories", "footprint_units", "hearing_fines_3y", "vacant_building_fine_due", "environmental_hold",
    "foreclosed_rental_date", "exempt_owner", "foreclosure_auction_date", "foreclosure_auction_status",
    "public_sale_source", "public_sale_price", "last_rezoning_date", "last_rezoning_status", "tax_sale_date",
    "tax_sale_due", "tax_sale_pins",
]  # fmt: skip

HALF_MILE_M = 804.67
PASSED = ("Passed", "Passed as Substitute")
SHOWN_DISTRICT_CHECKS = ("model", "confirmed", "corrected")  # db/migrations/0091_rezoning_district_check.sql


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
            left join lateral (select * from block_face b where b.block_face = lu.block_face offset 0) bf on true
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
            # A PIN range rather than left(pin, 10), so the lookup uses the pin index (0.2 s down to under 1 ms).
            "select sale_date, sale_price, deed_type from sale where pin between %s and %s order by sale_date desc limit 5",
            (out["pin10"] + "0000", out["pin10"] + "9999"),
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
    sc = conn.execute(
        """select score, zoning_upside, profit, acquisition, location, incentives, penalties, details, computed_on
           from parcel_score where pin10 = %s""",
        (out["pin10"],),
    ).fetchone()
    out["score"] = None if not sc else {
        "score": float(sc[0]), "zoning_upside": float(sc[1]), "profit": float(sc[2]), "acquisition": float(sc[3]),
        "location": float(sc[4]), "incentives": float(sc[5]), "penalties": float(sc[6]), "details": sc[7],
        "computed_on": sc[8].isoformat(), "label": "a sorting aid built from the points shown; it does not rate investment quality"}  # fmt: skip
    out.update(extras(conn, out))
    return out


def _plain(v):
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if type(v).__name__ == "Decimal":
        return float(v)
    return v


def _has(conn, table: str) -> bool:
    return conn.execute("select to_regclass(%s)", (table,)).fetchone()[0] is not None


def extras(conn, p: dict) -> dict:
    """Facts that sit beside the lot: the tax sale rows, the city's sale listing, the Assessor's value and
    rezoning applications within half a mile. Each block is None or empty when its table has no row."""
    pin10 = p["pin10"]
    out: dict = {"tax_sale": None, "city_listing": None, "assessor_value": None, "rezonings_nearby": None}

    upcoming = p.get("tax_sale_date") and str(p["tax_sale_date"]) >= date.today().isoformat()
    if upcoming and _has(conn, "tax_sale_list"):
        rows = conn.execute(
            """select pin, tax_year, tax_type, total_tax_due, total_due, classification, listed_through, source_url
               from tax_sale_list where pin10 = %s and sale_date = %s order by pin, tax_year""",
            (pin10, p["tax_sale_date"]),
        ).fetchall()
        head = [
            "pin",
            "tax_year",
            "tax_type",
            "tax_due",
            "total_due",
            "classification",
            "listed_through",
            "source_url",
        ]
        out["tax_sale"] = {
            "sale_date": p["tax_sale_date"], "total_due": p.get("tax_sale_due"), "pins": p.get("tax_sale_pins"),
            "rows": [{k: _plain(v) for k, v in zip(head, r, strict=True)} for r in rows],
            "listed_through": _plain(rows[0][6]) if rows else None,
            "source": "Cook County Treasurer, Annual Tax Sale delinquent lists by ward (cookcountytreasurer.com)",
            "source_url": rows[0][7] if rows else "https://www.cookcountytreasurer.com/delinquenttaxes.aspx",
            "note": "The owner can pay until the sale, which takes the lot off the list. A tax buyer gets a lien, "
                    "not the deed; the owner can redeem afterward.",
        }  # fmt: skip

    if _has(conn, "lot_for_sale"):
        r = conn.execute(
            """select l.source, l.status, l.for_sale, l.asking_price, l.minimum_bid, l.city_land_value, l.deadline,
                      l.offer_round, l.apply_url, l.listed_on, sp.finished_at
               from lot_for_sale l left join source_pull sp on sp.id = l.source_pull_id
               where l.pin10 = %s order by l.for_sale desc, l.listed_on desc nulls last limit 1""",
            (pin10,),
        ).fetchone()
        if r:
            head = ["source", "status", "for_sale", "asking_price", "minimum_bid", "city_land_value", "deadline",
                    "offer_round", "apply_url", "listed_on", "pulled_at"]  # fmt: skip
            out["city_listing"] = {k: _plain(v) for k, v in zip(head, r, strict=True)}

    if _has(conn, "lot_market_value"):
        r = conn.execute(
            """select market_value, land_market_value, total_av, tax_year, stages, pins, pins_without_value
               from lot_market_value where pin10 = %s""",
            (pin10,),
        ).fetchone()
        if r and r[0]:
            head = ["market_value", "land_market_value", "assessed_value", "tax_year", "stages", "pins", "pins_without_value"]  # fmt: skip
            out["assessor_value"] = {k: _plain(v) for k, v in zip(head, r, strict=True)} | {
                "source": "Cook County Assessor assessed values (uzyt-m557) divided by the level of assessment"
            }

    if _has(conn, "rezoning") and p.get("lat") is not None:
        rows = conn.execute(
            """select r.record_number, r.address, r.intro_date, r.final_date, r.status, r.sub_status,
                      case when r.district_check = any(%s) then r.from_district end,
                      case when r.district_check = any(%s) then r.to_district end,
                      round(st_distance(g.geom::geography, st_setsrid(st_makepoint(%s, %s), 4326)::geography))
               from rezoning r
               join lateral (select geom from parcel where pin10 = r.pin10 limit 1) g on true
               where r.intro_date >= current_date - interval '5 years' and r.pin10 is not null
                 and st_dwithin(g.geom::geography, st_setsrid(st_makepoint(%s, %s), 4326)::geography, %s)
               order by r.intro_date desc""",
            (list(SHOWN_DISTRICT_CHECKS), list(SHOWN_DISTRICT_CHECKS), p["lon"], p["lat"], p["lon"], p["lat"], HALF_MILE_M),
        ).fetchall()  # fmt: skip
        placed, total = conn.execute(
            "select count(pin10), count(*) from rezoning where intro_date >= current_date - interval '5 years'"
        ).fetchone()
        out["rezonings_nearby"] = rezoning_summary(rows) | {"placed": placed, "citywide": total}
    return out


def rezoning_summary(rows: list[tuple]) -> dict:
    """Counts only, no forecast: applications within half a mile in 5 years, the share of decided ones that
    passed, and the median days from introduction to passage."""
    passed = [r for r in rows if r[5] in PASSED]
    decided = [r for r in rows if (r[4] or "").startswith("90-")]
    days = sorted((r[3] - r[2]).days for r in passed if r[2] and r[3])
    median = None
    if days:
        mid = len(days) // 2
        median = days[mid] if len(days) % 2 else round((days[mid - 1] + days[mid]) / 2)
    return {
        "count": len(rows), "decided": len(decided), "passed": len(passed),
        "share_passed": round(len(passed) / len(decided), 3) if decided else None,
        "median_days_to_pass": median, "timed": len(days),
        "radius_mi": 0.5, "years": 5,
        "list": [
            {"record": r[0], "address": r[1], "introduced": _plain(r[2]), "decided": _plain(r[3]),
             "status": r[5] or r[4], "from": r[6], "to": r[7], "feet": round(float(r[8]) * 3.28084) if r[8] is not None else None}
            for r in rows[:12]
        ],
        "source": "Chicago City Council zoning map amendments (Office of the City Clerk, eLMS); districts read from "
                  "the ordinance scans and checked",
        "label": "Counts of past applications near this lot. They do not predict the result of a new application.",
    }  # fmt: skip


# Each sort ends in a unique key and matches an index (db/migrations/0093_lot_list_indexes.sql), so a page of
# the list reads 50 rows instead of sorting 600,000. ps.pin orders the same as s.pin10 here: one scored row per lot.
LOT_SORTS = {"score": "s.score desc, s.pin10", "return": "s.return_on_cost_p25 desc nulls last, s.pin10",
             "upside": "(s.by_right_units - coalesce(s.units_now, 0)) desc, s.pin10",
             "lot": "ps.lot_sqft desc nulls last, ps.pin"}  # fmt: skip
LOT_COLUMNS = ["pin10", "pin", "address", "zip", "community_area", "zone_class", "lot_sqft", "score", "zoning_upside",
               "profit", "acquisition", "location", "incentives", "penalties", "units_now", "by_right_units",
               "units_priced", "sale_per_unit", "sale_comps", "land", "total_cost", "profit_central", "profit_p25",
               "return_on_cost", "return_on_cost_p25", "max_land_price", "details", "computed_on", "lat", "lon", "tax_sale_date", "tax_sale_due"]  # fmt: skip


def lots(conn, *, community_area: int | None = None, zone_prefix: str | None = None, min_score: float = 0,
         min_units: int = 0, signal: str | None = None, for_sale: bool = False, vacant: bool = False, fast_path: bool = False, tax_sale: bool = False,
         sort: str = "score", limit: int = 100, offset: int = 0, pin10: str | None = None) -> list[dict]:  # fmt: skip
    """The list screen: scored lots with filters, from parcel_score (jobs/score_parcels.py)."""
    where, args = (
        ["s.score >= %s::numeric"],
        [min_score],
    )  # numeric, or a float parameter skips the score index
    if pin10:
        where.append("s.pin10 = %s")
        args.append(pin10)
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
    if fast_path:
        where.append("(s.details->>'fast_path')::boolean")
    if tax_sale:
        where.append("ps.tax_sale_date >= current_date")
    rows = conn.execute(
        f"""select s.pin10, s.pin, a.address, a.zip, p.community_area_name, ps.zone_class, ps.lot_sqft, s.score,
                   s.zoning_upside, s.profit, s.acquisition, s.location, s.incentives, s.penalties, s.units_now,
                   s.by_right_units, s.units_priced, s.sale_per_unit, s.sale_comps, s.land, s.total_cost,
                   s.profit_central, s.profit_p25, s.return_on_cost, s.return_on_cost_p25, s.max_land_price,
                   s.details, s.computed_on, st_y(p.geom), st_x(p.geom), ps.tax_sale_date, ps.tax_sale_due
            from parcel_score s
            join parcel_site ps on ps.pin = s.pin
            join parcel p on p.pin = s.pin
            left join parcel_address a on a.pin = s.pin
            where {" and ".join(where)}
            order by {LOT_SORTS.get(sort, LOT_SORTS["score"])}
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
        row["tax_sale_date"] = row["tax_sale_date"].isoformat() if row["tax_sale_date"] else None
        out.append(row)
    return out
