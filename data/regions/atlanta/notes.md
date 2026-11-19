# Atlanta notes

Checked 2026-11-17. Code encoded: the current zoning ordinance, Part 16 of the Atlanta Code of Ordinances. The ATL Zoning 2.0 rewrite is not adopted and is not encoded.

## What was read

- The official copy (library.municode.com) and the Municode API both returned a browser check and could not be fetched. The text was read on the Zoneomics mirror of the Municode chapters (`https://www.zoneomics.com/code/atlanta-GA/chapter_N`). It is a third-party copy. It carries ordinance history through Ord. 2025-15 (June 2025). Spot-check the numbers against Municode in a browser before launch.
- Chapters read in full for the numbers used: 3 (R-1), 4 (R-2), 4A, 4B, 5 (R-3), 5A, 6 (R-4), 6A (R-4A), 6B (R-4B), 7 (R-5), 8 (RG), 9 (R-LC), 34 (MRC), 35 (MR), 36A (BeltLine affordable housing), 37 (Westside affordable housing). Parts read: 27 (amendments), 28 (16-28.004 accessory buildings, 16-28.014 parking), 29 (definitions), 36 (BeltLine scope and procedure).

## Third-party figures checked against the code

| Figure | Code | Result |
|---|---|---|
| R-4: 9,000 sq ft, 70 ft, FAR 0.50, 50% coverage | 16-06.007(2), 16-06.008(5)-(6) | Confirmed |
| R-4A: 7,500, 50 ft, 0.50, 55% | 16-06A.007(1), 16-06A.008(5)-(6) | Confirmed. Lots under 7,500: lesser of 3,750 sq ft or FAR 0.65 |
| R-4B: 2,800, 40 ft, 0.75, 85% | 16-06B.007(1), 16-06B.008(5)-(6) | Confirmed. Lots under 2,800: lesser of 2,100 sq ft or FAR 0.90 |
| R-5: 7,500 (2,500 zero-lot-line), 50 ft, duplex FAR 0.60 | 16-07.007(2)-(3), 16-07.008(5) | Confirmed. Single-family FAR is 0.50. Coverage 55% |
| ADU: detached only, R-4, R-4A, R-5, 750 sq ft, 20 ft | 16-06.004(12), 16-06A.004(11), 16-07.004(12), 16-29.001, 16-28.004(3) | Confirmed. Also capped at 30% of the main house's floor area and 25% of the rear yard. No parking. Lot total may not exceed 2 units |
| BeltLine inclusionary zoning at 10+ rental units | 16-36A.001, 16-36A.004 | Confirmed: 15% at 80% AMI or 10% at 60% AMI, 20 years minimum, in-lieu fee option |
| Westside overlay | 16-37.001, 16-37.004 | Same rule, 10+ new rental units |

## Districts covered (24 rows)

R-1, R-2, R-2A, R-2B, R-3, R-3A, R-4, R-4A, R-4B, R-5, RG-1 to RG-5, R-LC, MR-1, MR-2, MR-3, MR-4A, MR-4B, MRC-1, MRC-2, MRC-3. Each row matches the base code and its conditional form (`R-4 R-4-C`).

There is no plain "MR-4" district in the code; it is MR-4A and MR-4B.

## Important: 14 rows have no lot area per unit

RG, R-LC, MR and MRC limit floor area (FAR), not units per lot. The code gives no lot area per unit or units per acre for them. `lot_area_per_unit_sqft` is blank on those 14 rows. `engine/rules.py` skips rows with a blank value, so today the engine reports those districts as not covered, and rezoning targets that point at them are dropped. The 10 R rows load and work.

To use the 14 rows the engine needs a rule such as units = floor(lot area x FAR / assumed unit size). The unit size would be a product assumption, not a code number, so it was not put in the rules file.

## Uncertain or simplified

- R-5 lots of record under 7,500 sq ft may still hold a two-family or duplex building (16-07.007(4)). The row uses 7,500 minimum and 3,750 per unit, so the engine shows 1 unit on those lots. A flag says so. Many older Atlanta R-5 lots are under 7,500 sq ft, so this matters.
- R-5 FAR is entered as 0.60 (duplex). A single-family house in R-5 gets 0.50.
- Small-lot floor area rules in R-4A, R-4B and R-5 (lesser of a fixed square footage or a higher FAR) are in the section text and a flag, not in the numbers.
- RG FAR is on gross land area (lot plus part of the street); MR and MRC are on net lot area, with a gross-lot option for residential. The engine multiplies by parcel area, so RG floor area is understated.
- RG has no height limit in RG-1 and RG-2 and a 45-degree transitional height plane in RG-3 to RG-5 near lower districts (16-08.006, 16-08.009). No RG rows are in zoning_heights.csv.
- MRC-1 and MRC-2 heights depend on distance to R, RG-1, RG-2, MR-1, MR-2 or PD-H districts. The lowest tier is recorded (35 ft and 52 ft). Away from those districts the limit is 225 ft.
- Parking for RG, R-LC, MR and MRC comes from Table I and changes with the project's FAR. The values entered are the Table I figures at each district's maximum FAR.
- No minimum lot area or width was found in Chapter 34 for MRC; those cells are blank.
- Setbacks are not in the contract's columns. Front yards are large in R districts (60 ft in R-1 and R-2, 50 ft in R-3, 35 ft in R-4, 30 ft in R-4A and R-5, 20 ft in R-4B) and will limit the building more than FAR on shallow lots.
- Rezoning targets are a judgment call. The code does not rank them. The hearing path (NPU, Zoning Review Board, City Council) is from Chapter 27.
- `fhfa_metro` is 12060 (Atlanta-Sandy Springs CBSA). It was not checked against the FHFA index file; FHFA may list the metro division code instead.
- Historic district chapters (Chapter 20) were not read. The flag only says they exist.

## Not covered

SPI districts (SPI-1 to SPI-26, with subareas), NC districts, C-1 to C-5, O-I, LW, I-MIX, MR-5A, MR-5B, MR-6, MR-MU, RG-6, PD districts, FCR-3, the HC-20 and Poncey-Highland base districts, and the overlays other than the two inclusionary rules. On the zoning layer, `MR-4-C` (3 polygons) and `MR-3A-C` (1 polygon) do not match any district in the code text and are not matched. C-1 and C-2 allow housing and are common (187 and 70 polygons); they are the first thing to add next.

## GIS layers (all tested 2026-11-17, no key)

- Zoning: `https://gis.atlantaga.gov/dpcd/rest/services/LandUsePlanning/LandUsePlanning/MapServer/0`, field `ZONECLASS`. 2,992 polygons, 245 distinct values. Sample values: R-1, R-2, R-2A, R-2B, R-3, R-3A, R-4, R-4-C, R-4A, R-4A-C, R-4B, R-4B-C, R-5, R-5-C, R-LC, R-LC-C, RG-1, RG-2, RG-2-C, RG-3, RG-3-C, RG-4, RG-5, MR-1, MR-2, MR-2-C, MR-3, MR-3-C, MR-4A, MR-4A-C, MR-4B, MR-4B-C, MR-5A, MR-MU, MRC-1, MRC-1-C, MRC-2, MRC-2-C, MRC-3, MRC-3-C, C-1, C-1-C, C-2, O-I, I-1, PD-H, PD-MU, SPI-3 SA2, NC-2.
- Overlays: same service, layer 1 (98 polygons), inclusionary zoning layer 2 (17), historic districts layer 6 (19).
- Flood: FEMA NFHL layer 28.
- Parcels: Fulton County `OpenData/Tax_Parcels/MapServer/0` (Atlanta = `TaxDist` starting with 05) and the city's own `AdministrativeArea/TaxParcel/MapServer/0` (171,174 parcels, both counties, has the zoning code on each parcel).

## Permit source

`https://services5.arcgis.com/5RxyIIJ9boPdptdo/arcgis/rest/services/building_permit_featureLayer/FeatureServer/0`: 38,953 permits opened 2022-09-20 to 2026-11-17, edited the day of the test. It feeds the city's Building Permit Tracker. No unit count field; `TypeCombo` separates "Residential New" (2,233) from "Multi Family New" (1,979). The item is described as "Test Official building permit data", so the URL could change.

The permit layer given in the brief (`services5.arcgis.com/54falWtcpty3V47Z/.../BldgPermitIssued_Archive`) is City of Sacramento data. Its first row is 2929 42nd St, ZIP 95817. Do not use it for Atlanta.

## Sales source

Result: a free bulk source exists for 2018 to 2022 only.

- Works: `https://services1.arcgis.com/AQDHTHDrZzfsFsB5/arcgis/rest/services/Tyler_YearlySales/FeatureServer`, layers 2 to 6 (2018 to 2022), published by Fulton County GIS. Fields: `ParID`, `TaxYear`, `Price`. Row counts: 22,951; 26,347; 32,010; 43,627; 12,875. Rows over $10,000 with parcel prefix 14 or 17 (most of Atlanta): 9,098; 10,040; 12,903; 18,269; 5,691. Limits: last edited 2022-11-02; no sale date, only the year; no deed type or validity code; many rows have Price 0 or 10; one row per parcel per year; 2022 is a partial year. The prefix test is rough; join to the parcel layer and filter on `TaxDist` instead.
- Works, values not sales: Fulton County yearly parcel snapshots `Tax_Parcels2015` to `Tax_Parcels_2026` in the same folder carry appraised and assessed values per parcel. `Temp/GlobalSearch_Dialog/MapServer/2` on gismaps.fultoncountyga.gov is a table of appraised values by parcel and year (9,315,204 rows, 2013 on).

Dead ends:
- Fulton County `OpenData/Tax_Parcels` layer: no sale fields.
- City of Atlanta `TaxParcel` layer: appraised value only.
- qPublic (qpublic.schneidercorp.com, Fulton): HTTP 403 to a script. It is a per-parcel lookup, not bulk.
- fultonassessor.org: HTTP 403. iaspublicaccess.fultoncountyga.gov: connection reset. No download page was found by search.
- Fulton County open data hub (gisdata.fultoncountyga.gov) search for "sales": only business datasets.
- City of Atlanta ArcGIS Online folder: `AMS_District_Property_Sales` has 34 rows; `Fulton_Tear_Down_Centroids_with_Square_Footage_and_Sales_Info` has 1,897 teardown parcels with SalePrice and SaleDate, last edited 2021. Neither is a bulk source.
- Georgia Department of Audits sales ratio study (audits2.ga.gov/sales-ratio): the page text could not be read by the fetch tool. Search results show county-level ratio reports, no parcel-level sales file. Not confirmed either way.
- GSCCCA real estate transfer tax (PT-61) index: not tested; it needs an account, which is outside the free, no-sign-up rule.
- DeKalb County (the east part of Atlanta): no sales layer found.

So for 2023 onward the options are appraised values (label them as values, with a wider range) or asking Fulton County for a newer copy of the yearly sales layer.

## Comp pool (added 2026-11-19)

Atlanta's free parcel layer has the appraised value and units but no year built or floor area. The comp pool now
comes from the City of Atlanta permit export (2019-2024): a lot with a finished "Residential New" permit (CO issued,
complete, closed or no CO required) takes the permit's status year as its year built, and its 2025 Fulton
appraised value becomes an appraised-value comp, as in Texas (`jobs/load_permits_year_built.py`).

Measured with `python -m jobs.check_region`:

| | |
|---|---|
| Finished new-house permits | 1,734 |
| Comps kept | 2,189 |
| Leave-one-out median error (800) | 42.7%, 18.2% within 15% |
| Fitted 80% range | -73% to +148% (after the 10-point appraisal widening) |

The error is high because the pool has no floor area: a 1,600 sq ft townhome and a 4,500 sq ft house a few blocks
apart are priced as the same unit. Counting "Multi Family New" permits too made it worse (43.7%), because condo unit
parcels under a new building took the building's year. A free per-parcel floor area source would fix most of this;
none has been found (Fulton's qPublic pages show it but are not a bulk download).
