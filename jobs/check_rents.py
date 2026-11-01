"""Calibrate the new-construction rent premium over Census ACS rents.

The Assessor's 2024 Chicago income worksheets (csik-bsws) give potential gross income and the unit mix for each
apartment building it valued by income. Market rent per unit = potential gross income / 12 / units. For each
building, the ACS expectation is the unit mix applied to its tract's median gross rent by bedrooms (ZIP area,
then the tract's overall median, as fallbacks), moved from the ACS midpoint to the valuation date with ZIP rent
growth (internal Zillow index). The ratio of the two, for buildings built 2014 or later, is
the premium a new building commands over ACS rents, which include long-tenure leases.

Caveats: Assessor rents are the office's market estimates, not leases; ACS rents are gross (utilities
included), Assessor income usually is not, so the measured premium is if anything low.
Run: python -m jobs.check_rents
"""

import statistics as st
from datetime import date

from core.db import connect
from core.socrata import COOK, Socrata
from engine.rents import ACS_MID, growth

DATASET = "csik-bsws"
TYPES = ("Multifamily-Low Rise (3 floors or less)", "Multifamily-MidRise (4 to 12 floors)")
VALUATION_DATE = date(2024, 1, 1)
BEDS = {"studiounits": "0", "_1brunits": "1", "_2brunits": "2", "_3brunits": "3", "_4brunits": "4"}


def run(client: Socrata | None = None) -> dict:
    client = client or Socrata(COOK)
    types = ", ".join(f"'{t}'" for t in TYPES)
    rows = [r for page in client.pages(DATASET, order=":id", where=f"year = '2024' and property_type_use in ({types})")
            for r in page]  # fmt: skip
    out: dict[str, list[float]] = {}
    with connect() as conn:
        for r in rows:
            try:
                units, pgi, built = float(r["tot_units"]), float(r["pgi"]), int(float(r["yearbuilt"]))
            except (KeyError, ValueError):
                continue
            if units < 2 or pgi <= 0:
                continue
            pin = r["keypin"].replace("-", "")
            geo = conn.execute(
                "select tract_geoid, zip from parcel where pin = %s order by tax_year desc limit 1", (pin,)
            ).fetchone()
            if not geo:
                continue
            rents = {}
            for kind, gid in (("zcta", geo[1]), ("tract", geo[0])):  # tract last so it wins
                for beds, rent in conn.execute(
                    "select bedrooms, median_rent from acs_rent where geo_kind = %s and geo_id = %s",
                    (kind, gid),
                ).fetchall():
                    rents[beds] = float(rent)
            mix = {b: float(r.get(k) or 0) for k, b in BEDS.items()}
            if sum(mix.values()) < units * 0.9 or "all" not in rents:
                continue
            expected = sum(n * rents.get(b, rents["all"]) for b, n in mix.items()) / sum(mix.values())
            market = pgi / 12 / units
            expected *= growth(conn, geo[1], ACS_MID, VALUATION_DATE)
            age = "new" if built >= 2014 else "older"
            out.setdefault(age, []).append(market / expected)
            if r["property_type_use"] == TYPES[0]:
                out.setdefault(f"{age}, low rise", []).append(market / expected)
    res = {}
    for k, v in out.items():
        if len(v) >= 4:
            q = st.quantiles(v, n=10)
            res[k] = {"buildings": len(v), "median_ratio": round(st.median(v), 3), "p10": round(q[0], 3),
                      "p90": round(q[-1], 3)}  # fmt: skip
    return res


if __name__ == "__main__":
    for k, v in run().items():
        print(k, v)
