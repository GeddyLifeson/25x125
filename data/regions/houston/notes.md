# Houston notes

Checked 2026-11-17. Free public sources only.

## How Houston is modeled

Houston has no use zoning. The City's own letter says so (2026-01-06). The rules that shape a small residential project are in Code of Ordinances Chapter 42 (platting and lot rules) and Chapter 26 (parking), plus private deed restrictions.

`zoning_districts.csv` has 2 pseudo-districts:

| Row | Match | Lot area per single-family lot | Source |
|---|---|---|---|
| City of Houston (no zoning) | `FULL` in the city limit layer, field `SERVICE_TY` | 3,500 sq ft | Sec. 42-181(a)(2) |
| Houston ETJ (outside city limits) | `ETJ` in the ETJ layer, field `Class` | 5,000 sq ft | Sec. 42-181(a)(1) |

The code no longer says "urban area" and "suburban area". The text in force says "within the city" and "within the extraterritorial jurisdiction". The ETJ row is there for completeness; only the city is loaded now. The ETJ match value is in a second layer, so the loader needs a point-in-polygon test against both layers.

Everything else is in `zoning_steps.json`: lots down to an average of 1,400 sq ft (Sec. 42-184), lots under 1,400 (Sec. 42-181(c)), narrow-lot and access rules, the second dwelling unit, multi-unit residential (3-8 units), courtyard style development, building lines, parking, Special Minimum Lot Size and Building Line, state laws and flags.

## What was read

- Ord. 2023-801 (Chapter 42, Livable Places, effective 2023-11-27), the signed 49-page ordinance on houstontx.gov. It is a scan. It was read with OCR (RapidOCR, run locally) and page 23 (Sec. 42-181 to 42-185) was checked by eye against the image. The numbers matched.
- Ord. 2023-802 (Chapter 26 parking), same method.
- Sec. 42-197 to 42-208 (Special Minimum Lot Size) and Sec. 42-170 and following (Special Minimum Building Line), text PDFs on the Planning Department site.
- Texas SB 840 and SB 15 enrolled text on capitol.texas.gov.
- Municode (the official codified copy) blocked automated fetches. It was not read. The amending ordinances restate each amended section in full, so the numbers here come from adopted text, but any amendment after 2023-11-27 is not reflected. One is known: a June 2026 council committee file names an "open space ordinance amendments redline"; it was not read.

## Numbers left blank on purpose

- `far`: Chapter 42 has no FAR, no lot coverage cap and no height cap for a standard 3,500 sq ft lot, so no ceiling can be derived. The engine loader turns a blank FAR into 0. That needs handling before Houston results show floor area.
- `max_units`: blank. A single-family lot holds up to 2 units (Sec. 42-1), but land not restricted to single-family use has no unit cap in Chapter 42.
- `max_height_ft`: blank in `zoning_heights.csv` (the loader skips those rows). 30 ft applies only to multi-unit residential and courtyard style development.
- `max_lot_coverage`: blank. The 40% building coverage (60% uncovered) applies only to lots under 3,500 sq ft under Sec. 42-184. It is in the `reduced_lot_size` step.
- No `rezoning` step. There is nothing to rezone. The paths up are a replat under Sec. 42-184, a multi-unit residential site, a courtyard plat, or a variance from the Planning Commission.

## Not confirmed

1. Deed restrictions. They are private, recorded with the county, and not in any free GIS layer. They decide more Houston lots than Chapter 42 does. The app can only name the subdivision (Subdivisions layer) and tell the user to look them up.
2. The codified Chapter 42 on Municode as of today, including the 2026 open space amendments and the compensating open space table in Sec. 42-182/42-183 (the table is an image in the City's plat notes guide and was not read).
3. Whether SB 840's caps (1 parking space per unit, 25 ft setbacks, 45 ft height floor) override Chapter 26 and Chapter 42 for multifamily in Houston. The law is written around zoning classifications, and Houston has none. No City statement was found. Same question for SB 15, which applies only to land "zoned for single-family homes".
4. Building line for single-family lots in the ETJ and under Sec. 42-156 (20 ft and 25 ft appear in the summary chart only; the section text was not in the ordinance read).
5. Market Based Parking area rules (layer found, Chapter 26 text not read).
6. Historic district design limits (Chapter 33 Art. VII, Heights design guidelines) and Chapter 19 floodplain elevations. Flagged only.
7. Whether LIMITED (limited purpose annexation) areas count as "within the city" for Chapter 42. Left unmatched.
8. Street right-of-way width. MUR and courtyard sites need a 50 ft street; no layer for width was tested.
9. OCR risk: sections other than 42-181 to 42-185 were not checked against the page image by eye.

## GIS tests (2026-11-17)

- City limit: `https://services.arcgis.com/NummVBqZSIJKUeVR/arcgis/rest/services/COH_City_Limit_view/FeatureServer/0`, field `SERVICE_TY`. Distinct values: `FULL` (2 polygons), `LIMITED` (749). A point in the Heights returned `FULL`.
- ETJ: `.../HoustonMap/Administrative_Boundary/MapServer/1`, field `Class`: `ETJ`, `SB 2038`.
- Special Minimum Lot Size: 804 records, `LOTSIZE` (for example 5000, 6250, 6600), `Status` (Approved, Pending, Expired, Denied, Rescinded, Withdrawn, Ineligible). Many are Expired; filter on Status.
- Special Minimum Building Line: 249 records, `BLD__LINE` (for example 19, 20, 25).
- Historic districts: 23 names; the Heights test point returned Houston Heights South.
- Flood: floodway 405, 100-year 3,957, 500-year 5,201 polygons (Harris County).
- Subdivisions: 45,431 plats; the test point returned HOUSTON HEIGHTS, Vol_Page 021-044.
- HCAD parcels: `https://www.gis.hctx.net/arcgis/rest/services/HCAD/Parcels/MapServer/0`, tax year 2026, with land and market values. Texas sale prices are not public, so prices are appraisal district values.

## Permits

No API. The Houston Permitting Center posts a weekly spreadsheet on https://www.houstonpermittingcenter.org/sold-permits-search. Tested the Oct 12-19, 2026 file: 358 rows; columns Zip Code, Permit Date, Permit Type, Project No, Address, Comments. No unit count, value or parcel id. About 45 weekly files are linked (2026 only). File names are irregular, so a job has to scrape the page. No permit layer was found on the City's ArcGIS open data.
