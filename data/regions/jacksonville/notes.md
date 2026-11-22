# Jacksonville, Florida: zoning notes

Checked 2026-11-17. Consolidated City of Jacksonville / Duval County. Ordinance Code Chapter 656 (Zoning Code).

## What was read

- Chapter 656 Part 3 (Sec. 656.304 to 656.313), Part 4 (Sec. 656.403, 656.414), Part 6 (Sec. 656.604) and the Part 16 definitions.
- The official code is on Municode. Municode blocked automated requests, so the text was read from the Zoneomics mirror of the same code (URLs in region.json). The mirror's history notes run to Ord. 2025-448-E (10-28-25), so it is current to late 2025.
- Cross-check: the city's own district summary PDFs (dated 01.31.2022) match the mirror for RR-Acre, RLD, RHD and RO. They differ for RMD because the RMD densities were raised after 2022 (see below).
- Florida Statutes s. 166.04151(7) (Live Local Act) on the legislature's site.

## Districts covered: 19

RR-Acre, RLD-120, RLD-100A, RLD-100B, RLD-90, RLD-80, RLD-70, RLD-60, RLD-50, RLD-40, RLD-TNH, RMD-A, RMD-B, RMD-C, RMD-D, RHD-A, RHD-B, CRO, RO.

## How the numbers were set

- RLD districts allow one single-family house per lot. Lot area per unit is the minimum lot area. No duplexes.
- The code has no duplex use. "Dwelling, multiple-family" means any building with more than one unit, so a duplex follows the multiple-family rule.
- RMD-B, RMD-C, RMD-D: 6,000 sq ft for the first two units, then 2,900 / 2,100 / 1,340 sq ft per added unit, capped at 15 / 20 / 30 units per acre. The CSV has one number per district, so `lot_area_per_unit_sqft` is 43,560 divided by the cap (2,904 / 2,178 / 1,452). This is within one unit of the stepped rule on small lots. Since 2026-11-22 the engine reads the exact steps from `multifamily_minimums` in `zoning_steps.json` (6,000 sq ft for two, then the added area, capped per acre), so a 5,808 sq ft RMD-B lot gets 1 unit and a 12,000 sq ft RMD-D lot gets 6, not 8.
- RMD-B/C/D `min_lot_area_sqft` (4,000) and `min_lot_width_ft` (40) are the single-family minimums. Two or more units need 6,000 sq ft and 60 ft.
- RMD-C carries the words "only where the density requirements of the Comprehensive Plan are met".
- RHD-A: 1,100 sq ft per unit but no more than 32 units per acre. The cap is tighter (1,361 sq ft per unit), so the CSV uses 1,361. RHD-B: 735 sq ft per unit (60 per acre cap is looser).
- CRO and RO: the lot rule is 6,000 sq ft for two units plus 2,100 per added unit. The 20 units per acre figure comes from the Sec. 656.311 intro sentence, not the lot table.
- The code has no FAR. `far` is lot coverage x stories, with stories = height / 12 ft rounded down (35 ft = 2, 45 ft = 3, 60 ft = 5). A 3-story building can fit in 35 ft, so the 35 ft districts may be understated.
- RMD, RHD and CRO heights can go above the limit if every required yard grows (1 ft per ft, or 1 ft per 3 ft in RHD-B). The CSV uses the base height.
- RMD-A is entered as single-family (1 unit per 4,000 sq ft lot). Townhomes and cottages are also permitted there on 1,500 sq ft lots; see the `townhomes` and `cottages` steps. The code gives RMD-A no multiple-family density, so the townhome density in RMD-A is not confirmed.

## Recent ordinances (2022 onward)

- Ord. 2022-448-E (November 2022): accessory dwelling units, Sec. 656.403(g). Footprint 25% of the house's gross floor area or 750 sq ft, whichever is less. Homestead exemption required. Behind the house. No inside door if attached.
- Ord. 2023-347-E and 2024-870-E amended Sec. 656.306. The current text has the higher RMD densities and the cottage rules. The city's 2022 summary shows the old RMD numbers (10 / 15 / 20 units per acre). Which ordinance changed which number was not traced.
- Ord. 2023-387-E amended the townhouse section (Sec. 656.414).
- Ord. 2024-0868 and 2024-0869 ("missing middle": duplexes, triplexes, quadplexes in existing neighborhoods) were withdrawn by Council on 2025-04-08, 18-0. They are not law.
- Ord. 2026-0311 (target growth areas: 15 to 40 units per acre, smaller lots, parking relief, in exchange for affordable units or resiliency measures) passed committee 6-0 on 2026-06-16 with a Council vote set for 2026-06-23. The outcome was not confirmed, and nothing from it is in these files.

## Zoning GIS layer

- `https://maps.coj.net/coj/rest/services/CityBiz/Parcels/MapServer/0`, field `ZON_LABEL`. It is the city's parcel layer (409,714 parcels) with zoning on each parcel. `RE` is the RE number.
- The city's zoning polygon services need a token, so they were not used.
- Distinct `ZON_LABEL` values on 2026-11-17 (48): blank, AGR, CCBD, CCG-1, CCG-1-M, CCG-2, CCG-2-M, CCG-S, CN, CN-S, CO, CRO, CRO-S, CSV, IBP, IH, IL, IW, PBF-1, PBF-2, PBF-3, PBF-M, PUD, PUD-SC, RHD-A, RHD-B, RLD100A, RLD100B, RLD-120, RLD-40, RLD-50, RLD-60, RLD-70, RLD-80, RLD-90, RLD-M, RLD-TNH, RMD-A, RMD-B, RMD-C, RMD-D, RMD-MH, RMD-S, RO, ROS, ROS-M, RR-Acre, WT.
- RLD-100A and RLD-100B are stored without the hyphen.
- A parcel split by two districts shows one label. How the city picks it is not documented.

## Not covered

- CN, CCG-1, CCG-2, CCBD. CN permits multi-family only above a ground-floor use; CCG-1 permits it only by exception; none of them give a lot area per unit, so no row could be confirmed. CCG-2 housing rules were not confirmed.
- CO: only houses originally built as single-family.
- RLD-TND: in the code (4,000 sq ft, 40 ft, 65% coverage) but no parcel carries it in the layer.
- Springfield districts (RMD-S, CRO-S, CN-S, CCG-S; Sec. 656.368), Mayport districts (-M), RMD-MH (mobile homes), PUD, PUD-SC, AGR, industrial, PBF, CSV, ROS.
- Zoning overlays (Riverside/Avondale, Springfield, San Marco and others in Part 3) were not read.

## Could not confirm

- The official Municode text directly. Everything rests on the mirror plus the 2022 city summaries.
- Impervious surface ratios (Sec. 654.129). Not read. They can limit coverage below the zoning figure.
- Land use category density caps for each parcel. The Comprehensive Plan caps gross density and no free land use layer was found.
- Whether Ord. 2026-0311 passed and what it changed.
- Townhome density in RMD-A (the code points to the land use category). RLD-TNH is now counted at the Low Density Residential cap, 7 units per acre (Sec. 656.305), as the `townhomes` path.
- A free layer of local historic districts. Only National Register boundaries (NPS) were found and tested.
- A bulk building permit source. JaxEPICS has no public download or documented API. `permit_source.kind` is `none`.
- The rezoning approval path (Planning Commission, Land Use and Zoning Committee, City Council) was not read from Part 1 of the code.
- Which Jacksonville zoning codes the city treats as commercial, industrial or mixed use for the Live Local Act. The `applies_to` list is the commercial districts named in the code's definition plus IBP, IL and IH. IW (industrial waterfront) is left off because the Act excludes working waterfront in industrial zones.
- The income limits behind "affordable" (s. 420.0004) were not read.
- Meanings of the airport and military fields on the parcel layer (APZ, AICUZ and others).
