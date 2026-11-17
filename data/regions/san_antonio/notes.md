# San Antonio notes

Checked 2026-11-17. Code: City of San Antonio Unified Development Code (UDC), Chapter 35.

## What was read

- UDC Art. III Div. 2 (Sec. 35-310.01 to 35-310.19, Table 310-1) and Div. 7 (Sec. 35-371, 35-373).
  The official copy is on Municode. Municode and its API returned a bot challenge (HTTP 403) to every request.
  The text was read from a third-party copy at zoneomics.com. Its amendment history runs through
  Ord. 2025-09-04-0580 (September 4, 2025), so it includes the 2022 UDC update (Ord. 2022-11-03-0831, effective 2023-01-01).
- The copy flattens Table 310-1 into a run of cells. Residential rows read cleanly. Commercial and office rows did not.
- City documents used as cross-checks: Explanation of Zoning Districts (R-4 4,000 sq ft / 35 ft wide, R-5 5,000 / 45,
  RM-4 4,000 / 15, MF-18/25/33 densities, C-2 25 ft, C-3 35 ft all match), the ADU permit page, ADU fact sheet,
  Information Bulletin 402, and the August 2025 fact sheet on the state-law amendments.
- Texas SB 840 and SB 15: enrolled bill text on capitol.texas.gov.
- Sec. 35-526 Table 526-3a (parking) from elaws.us, a copy that stops at Ord. 2018-11-01-0858.

## Districts covered (24)

RE, R-20, R-6, R-5, R-4, R-3, R-2, R-1, RM-6, RM-5, RM-4, MF-18, MF-25, MF-33, MF-40, MF-50, MF-65,
NC, C-1, C-2 (with C-2NA), C-2P (with C-2PNA), C-3 (with C-3NA, C-3R), O-1, O-1.5.

- R districts: 1 house per lot. Lot area per unit = minimum lot size.
- RM-6 / RM-5 / RM-4: Sec. 35-310.06(a)(1) lets a lot that meets the minimum size (6,000 / 5,000 / 4,000 sq ft)
  hold up to 2 / 3 / 4 units, even though the table density is 7 / 9 / 11 units per acre.
  `lot_area_per_unit_sqft` is minimum lot divided by the unit cap (RM-5 is 1,666, rounded down so a 5,000 sq ft lot gives 3).
  On a large RM tract the per-acre density governs and can allow more than the cap; the table does not model that.
- MF districts: 43,560 / units per acre. No minimum lot size. Minimum width 50 ft.
- Commercial and office rows: 670 sq ft per unit (65 units per acre) from the city's SB 840 fact sheet. This applies to
  projects of 3 or more units only.

## Not confirmed

1. **Sec. 35-312 text.** Only the city fact sheet was read (65 units per acre in commercial, office and light industrial
   zoning). The section's own height, setback and parking wording was not read. Heights for NC, C-1, C-2, C-2P, C-3 and O-1
   in `zoning_heights.csv` are the base district heights; SB 840 sets a 45 ft floor for qualifying projects. Whether 1 or 2
   dwellings are allowed in these districts was not confirmed.
2. **FAR and lot coverage.** The UDC has no FAR. Table 310-1 has no lot coverage column. It caps "individual building size"
   at 70% / 50% / 45% of lot area in R-3 / R-2 / R-1 and 65% in RM districts. The text does not say whether that is
   footprint or floor area. `far` and `max_lot_coverage` are blank on every row.
3. **Parking.** Table 526-3a values (1 per unit for houses, townhouses, duplexes; 1.5 per unit for 3-family, 4-family and
   multi-family; maximum 2) come from a 2018 copy. Not checked against the current table.
4. MF-50 and MF-65 height: the table shows no number. No height row written.
5. O-2 and D (Downtown): heights and housing rules not read cleanly. Left out. L (light industrial) also falls under
   Sec. 35-312 per the fact sheet; left out as industrial.
6. Commercial rows of Table 310-1 (frontage, width, setbacks): cells could not be aligned. Width left blank.
7. Sec. 35-398.03 (small lot single-family, SB 15): text not read. Only the fact sheet and the bill.
8. ADU districts come from the city's ADU page (R-1 to R-6, RM-4/5/6, multi-family lots with fewer than 5 units), since
   the use table in Sec. 35-311 was not available. Sec. 35-371 also gives RE a 1,200 sq ft ADU cap, but the city page
   does not list RE, R-20 as ADU districts, so they are left out.
9. Setbacks (10 ft front, 5 ft side, 10 to 30 ft rear) were read but the contract has no column for them.

## Zoning layer

- `https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/COSA_Zoning/FeatureServer/12`, field `Base`.
- 790,222 polygons. 273,815 are `OCL` (outside city limits), 14,568 `UZROW`, 24,240 null (special district only).
- `SpecDistrict` is filled on about 72,000 polygons (PUD 47,570, NP-8 4,317, NP-10 3,368, IDZ and IDZ-1/2/3 about 3,000,
  MXD 671). Those lots are not covered: the special district replaces the base numbers.
- `SpecCondition` CD (5,911) and S (2,982) mark lots with a council-approved conditional or specific use.
- One stored code has a trailing space: `DR ` (Development Reserve). Not covered.
- Overlays are separate layers (historic, NCD, RIO, MPOD, AHOD, MAOZ). See `region.json`.

## Permits

- CKAN datastore on data.sanantonio.gov, dataset `building-permits`. Two files: 2020-07-20 to 2024-12-31 (368,297 rows)
  and 2025-01-01 onward (155,980 rows on 2026-11-15).
- No unit count. Declared valuation is blank on most residential rows, so a cost index from permits will be thin.
  `AREA (SF)` is filled. X/Y coordinates mix lon/lat and state plane feet.

## Appraisal data

- BCAD has no free bulk export. Its site offers search and a records request form only.
- Bexar County GIS serves BCAD parcels free: `https://maps.bexar.org/arcgis/rest/services/Parcels/MapServer/0`
  (729,183 rows; TotVal, LandVal, ImprVal, YrBlt, GBA, Acres, Nbhd, State_cd). 1,000 rows per request, so a full pull is
  about 730 requests.
- The layer does not state the tax year. It holds 12,132 parcels built in 2025 and 23 in 2026, so it is recent.
- No sale prices anywhere. Texas is a non-disclosure state.

## State law

- SB 840 is in `state_overrides` for the 7 commercial and office districts. San Antonio's highest residential density is
  65 units per acre, so the city floor is 65, above the state's 36.
- SB 15 only reaches unplatted tracts of 5 acres or more. It does not change an existing infill lot.
- Both laws exclude land within 3,000 ft of an airport or military base. San Antonio has several bases; no free layer
  with that 3,000 ft buffer was found. MAOZ and the county Military_Installations layer are the closest.

## Rezoning targets

Editorial picks, not code. IDZ is the most common small-lot infill request in the older city and is not modeled.
HB 24 (2025) raised the protest threshold to 60% of land within 200 ft; added-housing cases pass council by simple majority.
