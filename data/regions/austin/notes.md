# Austin, Texas: zoning rules notes

Checked 2026-11-17. Travis County only. 19 district rows (18 with a unit count; MF-6 has none).

## What was read

- Land Development Code Chapter 25-2: the use table (25-2-491), the site development table (25-2-492), district sections 25-2-555 to 25-2-563, use sections 25-2-771 to 25-2-779, Subchapter E 4.2 and 4.3 (mixed use), Subchapter F 2.1. Also 25-4-232 (small lot subdivisions) and 25-6-471 (parking).
- The official code is on Municode, which blocks automated requests. The text was read from the Zoneomics copy of the Municode pages (https://www.zoneomics.com/code/austin-TX/chapter_2, chapter_4, chapter_6). That copy carries amendments through Ord. 20260528-067 (June 2026).
- Checked against two signed ordinances on the city's own server: HOME Phase 1 (20231207-001) and HOME Phase 2 (20240516-006). The numbers match.
- Checked against the city's Guide to Zoning (September 2016). Lot size, width, cover, height and FAR match for every district covered; only the HOME changes differ.
- Texas SB 840 and SB 15 enrolled bill text, plus Austin's SB 840 page and information sheet.

## How the districts are encoded

- **SF-1, SF-2, SF-3**: 3 units per lot on 5,750 sq ft or more (HOME Phase 1). Lot area per unit is 1,916 sq ft, which is 5,750 / 3. That figure is derived so the engine returns 3 units at 5,750 sq ft; the code states a lot minimum and a unit cap, not a per-unit area. FAR is 0.65 (three-unit cap). A lot under 5,750 sq ft returns one house, which matches the HOME Phase 2 small lot rule down to 1,800 sq ft. The engine does not stop at 1,800 sq ft; the `small_lot` step holds that floor.
- **SF-1**: one house alone still needs 10,000 sq ft and 35% cover. The row uses the 2-3 unit numbers (5,750 sq ft, 40%).
- **Small lots**: one lot of 5,750 sq ft can be split into 3 lots of 1,800 sq ft or more, each with one house, by subdivision. The engine does not compute this path; the numbers are in the `small_lot` step.
- **SF-5, SF-6**: 3,500 sq ft per unit is the condominium rule (14,000 sq ft site). A duplex or two-unit use is also allowed on a 5,750 sq ft lot, so the row shows 1 unit on a 5,750 sq ft lot where 2 are allowed. Townhouses need 3,600 sq ft each.
- **MF-1 to MF-5 and the -MU districts**: site area per unit depends on bedrooms. The row uses the two-or-more-bedroom figure, the largest. Efficiencies and one-bedrooms fit more units; all three figures are in the `site_area_by_unit_type` step.
- **MF-6**: no site area per unit and no FAR in the code. The row has a blank lot area per unit, so the engine reports MF-6 as not covered.
- **NO, LO, GO, LR, GR, CS, CS-1**: one row each. The match list holds the plain district and every -MU and -V string. Under the city code, housing needs -MU or -V; the plain district allows none. The row uses the -MU site area numbers for all of them. That overstates the city-code answer on a plain lot, but SB 840 allows 3 or more units there at 54 units per acre (807 sq ft per unit), which is more than any -MU figure. The SB 840 path is in `state_overrides` with `units_per_acre` 54, `min_units` 3, `min_height_ft` 45.
- **FAR where the code has none** (SF-4A, SF-5, SF-6, MF-1, MF-2, MF-6): building cover x stories, with stories = height / 12 ft rounded down to a half story.
- **Parking**: 0 spaces per unit. Austin removed car parking minimums citywide in November 2023 (25-6-471).
- **ADU**: no `adu` step. HOME Phase 1 repealed the accessory apartment rule (25-2-901) and the two-family use (25-2-774). A second or third home on an SF lot is now a unit under 25-2-773, with no size cap of its own, no owner-occupancy rule and a building permit only. Adding an `adu` step would double count.
- **Rezoning targets** are a judgment about what small builders ask for. They are not from the code.

## Zoning layer

- https://services.arcgis.com/0L95CJ0VTaxqcmED/arcgis/rest/services/PLANNINGCADASTRE_zoning_small_map_scale/FeatureServer/0, field `ZONING_ZTYPE`. 22,502 polygons, 558 distinct strings.
- The field holds the full string (SF-3-NP, CS-MU-V-CO-NP), so `match` lists every string seen on 2026-11-17: 438 strings across the 19 rows, covering 18,205 polygons. New strings will appear after rezonings. The nightly job should re-pull the distinct list and map each string by its leading base district (after dropping a leading `I-`).
- Left out of `match`: split strings with a slash (GR-MU-CO-NP/MF-6-CO-NP, 4 polygons), `LR -NP` (has a space, 1 polygon), `SF-4` and `p` (typos in the layer, 6 polygons).
- Strings starting `I-` are interim zoning from annexation and are matched to their district.

## Not covered

- CBD and DMU (downtown; no density limit, density bonus programs), L, CH, CR, W/LO, SF-4B (condominium sites of 1 to 5 acres), MH, RR, LA, DR, AG, P, industrial districts, PUD, TOD, NBG, ERC, TND, and any string with -PDA. SB 840 also reaches CBD, DMU, CH, CR, L and W/LO, but those have no rows.
- Density bonus paths: DB90, ETOD/DBETOD, VMU bonus, Affordability Unlocked, University Neighborhood Overlay.
- Neighborhood plan infill options (small lot amnesty, secondary apartment, cottage lot, urban home).
- Setbacks are in the step text only.

## Could not confirm

1. **The official Municode text.** Everything from the code comes from a third-party copy. It matched the two signed ordinances and the 2016 city guide, but an amendment after June 2026 would not show.
2. **How Austin applies SB 840 lot by lot.** The city gives 54 units per acre, 45 ft and no FAR limit, but has not published which lots are excluded (within 1,000 ft of heavy industrial use, within 3,000 ft of an airport). No city ordinance writing SB 840 into the code was found. Whether building cover and impervious cover limits still apply to SB 840 projects is assumed, not confirmed.
3. **Conditional overlays (-CO) and NCCDs.** About 4,100 polygons carry -CO and 730 carry -NCCD. Each has its own ordinance that can cut units, height or FAR. Those ordinances were not read; lots are matched to the base district and flagged.
4. Compatibility height steps within 75 ft of houses (number from a city summary page, code text not read).
5. The 32 ft height limit for a single house inside the Subchapter F area (from the city HOME page, code text not read).
6. Whether three units are allowed in SF-5, SF-6 or MF districts on a small lot. The use table shows three-unit residential only in SF-1, SF-2 and SF-3; multifamily starts at 4 units.
7. Watershed impervious cover limits (Chapter 25-8), which can be lower than zoning limits.
8. The column positions inside TCAD's IMP_DET.TXT and LAND_DET.TXT. The files hold year built, segment area and land square feet (seen in sample rows), but only PROP.TXT was mapped column by column.

## Data sources tested

- Permits: https://data.austintexas.gov/resource/3syk-w9eu.json (Socrata, 2,385,678 rows, no key). `tcad_id` joins to TCAD `geo_id`.
- Appraisal roll: https://traviscad.org/publicinformation. 2026 Certified Appraisal Export, 557 MB zip of fixed-width text. Market value, land acres and situs are in PROP.TXT. Year built and floor area are per segment in IMP_DET.TXT; living area has to be summed. No sale prices.
- Overlays: historic (National Register polygons, landmark points; local districts are -H and -HD in the zoning string), city and FEMA floodplains, NCCD, Subchapter F boundary, ETOD, waterfront, Lake Austin, Barton Springs Zone, capitol view corridors, airport, University Neighborhood, wildland-urban interface, jurisdictions. All returned counts on 2026-11-17.
