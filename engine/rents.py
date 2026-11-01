"""Monthly rent per unit for new construction.

rent = ACS 5-year median gross rent for the bedroom count (tract, else ZIP area, else the tract's overall
median) x rent growth since the ACS midpoint (Zillow ZORI by ZIP, used only as a ratio and never shown;
the Chicago ZIP median growth when the ZIP has no series) x the new-construction factor.
The factor and its 80% range come from jobs/check_rents.py (data/rules/feasibility_defaults.json rents).
"""

import statistics as st
from datetime import date

ACS_VINTAGE = "2020-2024"
ACS_MID = date(2022, 7, 1)


def _zori(conn, zip_code: str | None, month: date) -> float | None:
    row = conn.execute(
        "select zori from zori_growth where zip = %s and month <= %s order by month desc limit 1",
        (zip_code, month),
    ).fetchone()
    return float(row[0]) if row else None


def growth(conn, zip_code: str | None, start: date, end: date) -> float:
    a, b = _zori(conn, zip_code, start), _zori(conn, zip_code, end)
    if a and b:
        return b / a
    rows = conn.execute(
        """select z1.zori, z2.zori from
             (select distinct on (zip) zip, zori from zori_growth where zip like '606%%' and month <= %s
              order by zip, month desc) z1
           join (select distinct on (zip) zip, zori from zori_growth where zip like '606%%' and month <= %s
                 order by zip, month desc) z2 using (zip)""",
        (start, end),
    ).fetchall()
    return st.median(float(b) / float(a) for a, b in rows) if rows else 1.0


def acs_rent(
    conn, bedrooms: int, tract: str | None, zip_code: str | None
) -> tuple[float, float | None, str] | None:
    beds = "5+" if bedrooms >= 5 else str(bedrooms)
    for kind, gid, b in (("tract", tract, beds), ("zcta", zip_code, beds), ("tract", tract, "all")):
        if not gid:
            continue
        row = conn.execute(
            "select median_rent, moe from acs_rent where geo_kind = %s and geo_id = %s and bedrooms = %s"
            " and vintage = %s",
            (kind, gid, b, ACS_VINTAGE),
        ).fetchone()
        if row:
            return (
                float(row[0]),
                float(row[1]) if row[1] else None,
                f"{kind} {gid}, {b} bedrooms, ACS {ACS_VINTAGE}",
            )
    return None


def rent(
    conn, bedrooms: int, tract: str | None, zip_code: str | None, rules: dict, as_of: date
) -> dict | None:
    base = acs_rent(conn, bedrooms, tract, zip_code)
    if base is None:
        return None
    median, moe, where = base
    g = growth(conn, zip_code, ACS_MID, as_of)
    r = rules["rents"]
    central = median * g * r["new_construction_factor"]
    return {
        "per_month": round(central),
        "low": round(median * g * r["factor_range"][0]),
        "high": round(median * g * r["factor_range"][1]),
        "acs_median": median,
        "acs_moe": moe,
        "acs_source": where,
        "growth_since_acs": round(g, 3),
        "factor": r["new_construction_factor"],
        "range": "80% range from the Assessor's 2024 income worksheets for buildings built 2014 or later",
    }
