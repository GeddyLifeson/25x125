# Tampa zoning rules: notes

Checked 2026-11-17. Code: City of Tampa Code of Ordinances, Chapter 27 (Zoning and Land Development).

## What was read

- The official host (library.municode.com and api.municode.com) blocks automated requests. It was not read directly.
- Chapter 27 text was read from a third-party copy of the Municode text: zoneomics.com/code/tampa-FL, chapters 2, 3, 4, 6 and 7. The copy carries ordinances through January 8, 2026 (Sec. 27-178) and Ord. 2024-76 on Sec. 27-156.
- Sec. 27-156 Table 4-2 was cross-checked against the City's own reproduction (ABCs of Zoning, tampa.gov, 2023). All 19 residential, office and commercial rows match: lot area, lot width, area per unit and height.
- City pages: tampa.gov/ADU (updated 07/15/2026), the 08/19/2026 news release on ADU rule changes, the Seminole Heights and East Tampa ADU guides.
- Fla. Stat. 166.04151(7) (Live Local Act) from leg.state.fl.us.
- Someone should open Municode in a browser and confirm the numbers before they reach a screen.

## Districts covered (18)

- RS-150, RS-100, RS-75, RS-60, RS-50: one unit per zoning lot. Minimum lot 15,000 / 10,000 / 7,500 / 6,000 / 5,000 sq ft. Height 35 ft.
- RM-12, RM-16, RM-18, RM-24, RM-35, RM-50, RM-75: 5,000 sq ft minimum lot, 50 ft wide; 3,630 / 2,723 / 2,420 / 1,815 / 1,243 / 871 / 580 sq ft of lot per unit.
- RO, RO-1, OP, OP-1, CN: densities from Table 4-2.1. Note 2 says the Comprehensive Plan caps density in these districts.
- SH-RS (Seminole Heights single-family detached): 5,000 sq ft, 50 ft wide, 35 ft.

## Things the tables cannot show

- No FAR and no lot coverage. Table 4-2 leaves FAR blank and note 17 sends it to the Comprehensive Plan. The `far` and `max_lot_coverage` columns are blank for every row. Setbacks and height set the envelope. Setbacks were read (front 20-30 ft, side 7 ft, rear 15-20 ft in RS and RM) but the file has no column for them.
- The Future Land Use category caps density on every lot and can be lower than the zoning number. No Future Land Use layer was loaded.
- RM-12, RM-16, RM-18: two-family, semi-detached and attached are by right. Multiple-family (3+ units) needs an S-1 special use permit and direct access to an arterial or collector street (Sec. 27-132). The CSV gives the density number without that condition; the flag `multifamily_special_use` carries it.
- RO allows only single-family detached houses (Table 4-1). The row has no `max_units` because a large lot can be split.
- RM-75 has no height number in Table 4-2 ("n/a", yards grow 1 ft per 4 ft above 30 ft). No height row.
- Taller RM-24, RM-35, RM-50, OP and OP-1 buildings need wider yards (Table 4-2 notes 2 and 3). On a 50 ft lot the full height is not reachable.

## Left out (engine reports "not covered")

- CG, CI: housing needs an S-1 permit and density comes only from the Comprehensive Plan. No per-unit lot area in the code.
- SH-RS-A, SH-RM, SH-RO, SH-CN, SH-CG, SH-CI, SH-PD: lot area per unit is "Per Future Land Use Category". Heights read: SH-RS-A 35 ft, SH-RM 38 ft (60 ft on R-35 or denser land), SH-RO 38 ft.
- NMU-35 (and NMU-16, NMU-24, which are not in the GIS layer): 5,000 sq ft minimum lot; height 35 / 60 / 85 ft; density from the Comprehensive Plan.
- YC-1 to YC-9 (Ybor City): Table 8-2 (dimensional regulations) is an image in the copy read and could not be confirmed. Minimum lot areas in Table 4-2.1: YC-2 2,500 sq ft, YC-8 4,356 sq ft. Ybor parking is 1 space per dwelling unit (Sec. 27-178 Table 8-1); none required in YC-1 and YC-3.
- RM-24/18 appears in the GIS layer. No such district was found in the code text. Left out.
- CBD-1, CBD-2, CD-1 to CD-3, PD, PD-A, M-AP, UC, IG, IH and the county codes A, AS-1, CU.

## ADU

- Size cap 950 sq ft; owner must live on the property; 2 unrelated occupants at most; S-1 permit reviewed yearly (Sec. 27-132).
- Allowed only in the mapped eligible areas (Table 4-1 note 17). `by_district` lists districts, so the engine will show an ADU path on lots outside those areas. The `adu_area` flag and the `eligible_area_layer` param (layer 37, field CRITERIA) are there so the engine can test the lot. Until it does, treat the ADU path as "check the map".
- Table 4-1 also marks CG as X/S1 for ADUs; CG is not in the CSV so it is not in `by_district`. SH-RS-A, SH-RM, SH-RO, SH-CG, SH-CI also allow ADUs (Table SH-25.1) and are left out for the same reason.
- The city ADU page (07/15/2026) says "the main residence must be owner-occupied". The 08/19/2026 news release says the owner may live in the main house or the ADU. The code text read says "resides on the property". The file follows the code text.
- ADU parking: not confirmed for the general case. A 2022 draft (1 space for ADUs over 600 sq ft) was found, and the Tampa Heights Overlay has that rule, but the Sec. 27-283.7 table read has no ADU row.
- Seminole Heights accessory buildings: floor area capped at 15% of the lot, 950 sq ft at most; 22.5 ft high (Table 211.2.1b).

## Parking

- Sec. 27-283.7 sets parking by building type and bedrooms, not by district. The per-district numbers assume 1-2 bedroom units plus 0.25 visitor spaces in RM-24 and up. Everything else uses 2 per unit.

## Rezoning targets

- The targets are the next denser districts in the same family. The code does not list them. Each one also has to fit the lot's Future Land Use category (Sec. 27-21 consistency matrix, not read in detail).

## State rules

- Live Local Act: recorded as a flag, with no unit count. The highest density Tampa allows anywhere was not confirmed, so no state-law path is computed. The list of districts it applies to is this file's reading of "commercial, industrial or mixed use"; the city decides.
- No statewide ADU mandate in Florida.

## GIS and permits

- Zoning layer tested 2026-11-17: field ZONECLASS, 55 distinct values. Codes used in `match`: RS-150, RS-100, RS-75, RS-60, RS-50, RM-12, RM-16, RM-18, RM-24, RM-35, RM-50, RM-75, RO, RO-1, OP, OP-1, CN, SH-RS. Other values seen: A, AS-1, CBD-1, CBD-2, CD-1, CD-2, CD-3, CG, CI, CU, IG, IH, M-AP-1 to M-AP-4, NMU-35, PD, PD-A, RM-24/18, SH-CG, SH-CI, SH-CN, SH-PD, SH-RM, SH-RO, SH-RS-A, UC, YC-1 to YC-9.
- FEMA's own NFHL server reset the connection twice; the Hillsborough County copy (effective 2022) worked and is recorded.
- Permits: the two city layers hold current and recent permits only (2,588 and 1,045 rows). No free bulk history and no job values. A cost calibration from permits is not possible with these.
- `center` and `fhfa_metro` were copied from docs/regions.md and not checked.
- SH-RS has no rezoning target: the Seminole Heights targets (SH-RS-A, SH-RM) are not in the CSV.
