# Orlando notes

Checked 2026-11-17. City of Orlando, Orange County, Florida.

## What was read

- Land Development Code Chapter 58, Part 1 (Figure 1 district tables FG-1A, FG-1B, FG-1C; Figure 2 use tables; all 43 footnotes), Part 2A (Sec. 58.203-58.210), Part 3A (ADUs, Sec. 58.500-58.501), Part 3B (townhomes, Sec. 58.510-58.512), Part 3C (duplex and tandem, Sec. 58.514-58.516), Part 3H (multiplex, Sec. 58.560-58.562), Part 7B (nonconforming lots, Sec. 58.1150-58.1155).
- The text came from the Zoneomics copy of the Municode code (https://www.zoneomics.com/code/orlando-FL/chapter_1 and chapter_3, chapter_7). The official Municode site and its API returned a bot challenge and could not be read. The copy carries ordinance history through Ord. 2024-17 for Figure 1A and Ord. 2025-12 for Figure 2. **Check the numbers once against Municode in a browser before they reach a screen.**
- City guidebook "Duplex and Tandem Development and Design Standards" (orlando.gov PDF, updated 2017-05-04) for parking.
- Florida Statutes s. 166.04151 (2025) on flsenate.gov for the Live Local Act.

## Districts covered (21)

R-1AA, R-1A, R-1, R-1N, R-2A, R-2B, R-3A, R-3B, R-3C, R-3D, MXD-1, MXD-2, O-1, O-2, O-3, MU-1, MU-2, AC-N, AC-1, AC-2, AC-3.

Not covered: AC-3A (downtown, 75 du/ac minimum), PD (110 plain polygons plus many with overlays; each has its own ordinance), I-C, I-G, I-P, P, C, H, UR, ASD-2, and unincorporated land.

## How the columns were filled

- `match`: the zoning layer stores base district plus overlay suffixes (R-2A/T/HP). Every stored value whose base equals the district is listed, 325 distinct values in the layer on 2026-11-17. New suffix combinations will appear over time. The engine should match on the text before the first "/" as a fallback.
- `lot_area_per_unit_sqft`: R-1 districts use the minimum lot. R-2A uses 5,500 / 2 (the duplex lot minimum). R-2B uses 5,000 / 2. All others use 43,560 / maximum density.
- `far`: 0.50 is the code's FAR for single family, tandem and duplex. Multifamily has no FAR; density governs. So the 0.50 understates floor area for 3+ unit buildings. Where Figure 1 gives no residential FAR (R-1 districts on conforming lots, R-3D, O-3, MU-2, AC-3), the value is ISR x stories at 12 ft per story. That is a loose ceiling because ISR counts driveways and patios.
- `max_lot_coverage`: this is the maximum impervious surface ratio (ISR). The code has no building coverage limit in Figure 1.
- `min_lot_area_sqft` and `min_lot_width_ft`: single-family values. Where the table differs inside and outside the Traditional City, the outside (larger) figure is used.
- Heights: where inside and outside Traditional City differ (R-1, R-2, O-1), the lower 30 ft is used. Parcels outside /T get 35 ft.

## Known gaps in the model

- R-3A: 12 du/ac gives 3,630 sq ft per unit, so the engine shows 1 unit on a 5,500 sq ft lot. The code allows a duplex or tandem there. The `duplex_lot` step holds the real lot minimums.
- R-2A: the table lists 12 du/ac and a 5,500 sq ft duplex lot (15.8 du/ac). How the city squares the two was not confirmed. The duplex lot minimum is used.
- R-2B multiplex: true rule is 16 du/ac with .5 rounded up, cap 5. The 2,500 per unit figure is close and never overstates.
- Minimum densities are in the section text and a flag, not in a column.
- Density bonuses (Ch. 58 Part 6) are not modeled.
- Corner lots need 15% more width (Fig. 1 footnote 11), not modeled.

## Could not confirm

1. Multifamily parking ratio (Ch. 61 Figure 26). Only the one-family, duplex and tandem numbers were confirmed, and those from a 2017 city guidebook, not the current code text.
2. Rezoning procedure (Ch. 65). The Municipal Planning Board step is confirmed from a 2025 case page. The City Council step and review standards were not read. Rezoning targets are a judgment.
3. The current code text on Municode itself (see above). One point to check: Figure 1A shows "(16)" rather than 0.50 for single-family FAR in the four R-1 districts.
4. ADU owner occupancy. Sec. 58.501 has no such rule. Section 30A.24 of the City Code, which it cites, was not read.
5. Whether Florida has a statewide ADU requirement. Not checked against the statutes.
6. Whether MXD and O districts count as "mixed use" or "commercial" under the Live Local Act. Only MU and AC districts are listed.
7. Historic district rules (Ch. 62 Part 2, Sec. 62.706 for ADUs), Parramore Heritage, special plan, aircraft noise, Wekiva and resource protection overlay rules were not read.
8. City floodplain rules (Ch. 63 Part 2C) were not read.
9. Setbacks are in Figure 1 but the contract has no column for them.
10. FHFA metro code 36740 (Orlando-Kissimmee-Sanford) and the map center were set from memory, not looked up.

## Data sources tested

- Zoning: https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/OrlandoLUZoning/FeatureServer/0, field `Zoning`. Most common values: C 114, PD 110, PD/AN 63, C/AN 51, P 48, PD/T 46, R-3B 39, UNINCORPORATED 38, I-G 34, R-2A/T 34, P/AN 33, R-3A 30, NO CITY ZONING 24, R-3B/W 23, O-1 22, R-3A/W 22, R-1 21, PD/W 20, R-3B/AN 20, AC-1 19 (polygon counts).
- Historic: OrlandoHistoricLocalDistricts (6 polygons), OrlandoHistoricNationalDistricts (7).
- Flood: Esri-hosted FEMA layer, 3,792 polygons for DFIRM 12095C. It holds special flood hazard areas only; a parcel with no hit is outside them. FEMA's own NFHL server reset the connection.
- Permits: Socrata ryhf-m453, 1,115,820 rows, no key needed. It has cost and square footage but no unit count, so 2-6 unit buildings must be picked out from project_name or another source.
