# Zoning capacity and parcel data: methods review of choices (a)-(g)

Scope: established methods for parcel-level zoning capacity and parcel data processing, checked against what 25x125 already built (`engine/zoning.py`, `jobs/build_parcel_site.py`, `jobs/build_lot_use.py`, `db/migrations/0004_shapes_zoning.sql`, `data/rules/zoning_steps.json`). Researched 2026-10-30.

Research limits: the shared web-fetch budget (100 calls per hour across all agents) ran out partway through. Primary code text was fetched from American Legal (codelibrary.amlegal.com) for 17-2-0300, 17-10-0200 and 17-13-1000. Several literature items (Monkkonen, Kaufmann, Been, MPC, CMAP, UrbanSim, Up for Growth, geocoding error studies) could not be fetched and are listed under Gaps rather than cited. Claims marked "from repo" come from reading our own code. Claims marked "inference" are my own arithmetic or reasoning.

## Q1. How published capacity and buildout studies compute capacity, and whether ignoring setbacks overstates capacity on 25x125 Chicago lots

### Takeaway
Established parcel models take the most restrictive of several caps (units per lot, density x area, FAR massing, height x coverage massing after setbacks); ours uses only density and FAR. On a standard 25 x 125 Chicago lot the setback envelope does not bind in RS-3 or RT-4 and binds by only about 4% in RM-5, so V1 is sound for interior standard lots. The bigger gaps are rules we skip that change units or parking (Type A exclusions, conversion-unit bonus, parking ratios by district) and the gap between zoned and realized capacity, which the literature puts at 1-2% of parcels developing per 5 years.

### Cited Findings
- Terner Housing Policy Simulator: maximum density is "the most restrictive" of (1) a units-per-lot limit, (2) units per acre x parcel acreage, (3) an FAR-and-footprint massing exercise, (4) a height-and-lot-coverage massing exercise; a condition the code does not set is ignored. Developable area is reduced first for slopes, easements and roads; construction assumed impossible above 30% slope. — [Terner Labs methodology](https://www.ternerlabs.org/terner-housing-policy-simulator-full-methodology)
- Same model: footprint is treated as a square reduced by twice the average setback on each side; parking takes 330 sq ft per surface stall and 400 sq ft per structured stall; units are modeled as 2-bedroom at 900-1,100 sq ft; it tests 60 project sizes from 2 to 1,000 units and drops those over the caps. It does not say how lot width or frontage is measured. — [Terner Labs methodology](https://www.ternerlabs.org/terner-housing-policy-simulator-full-methodology)
- Zoned vs realized capacity, Los Angeles (Romem and Wilkinson, Terner Center, 2021-08-03): about 1 in 80 parcels saw units permitted each year in 2015-2019, a 5-year development probability of about 1.2%; about half of units permitted exceeded observed zoned capacity (mostly via upzoning); sites zoned 5+ units, if developed, reach roughly 40-90% of bonus-zoned capacity; probability-weighted capacity within 5 years was 29,505 units, 6.5% of a 456,643-unit RHNA, despite raw excess capacity several times RHNA. — [Terner Center, Creating a Stronger Housing Element](https://ternercenter.berkeley.edu/research-and-policy/stronger-housing-element-los-angeles/)
- National Zoning Atlas maps zoning districts, not parcels; it records per district the residential uses allowed, permitting procedure, minimum lot sizes, parking mandates, height caps, ADU and PRD permissions; it cleans slivers and overlaps and removes rights-of-way, water and protected land. The public "how" page does not mention parcels, split parcels, setbacks or lot coverage; the full method is in "How To Make a Zoning Atlas 2.0" (2024) and an internal wiki. — [National Zoning Atlas, How](https://www.zoningatlas.org:443/how)
- Chicago bulk rules for the envelope check (17-2-0300): front setback in RT/RM is 15 ft or 12% of lot depth, whichever is less, or the block average; assumed front setback on vacant lots is 20 ft or 16% of depth in RS-3 and 15 ft or 12% in RT-3.5 to RM-5 (17-2-0305). Rear setback 28% of lot depth or 50 ft, whichever is less, for detached houses; 24% or 50 ft for buildings of 19 units or fewer with at least 33% accessible units (17-2-0306). Rear yard open space RS-3 225 sq ft/unit, RT-4 65, RM-4.5 50, RM-5 36 (or 6.5% / 5.25% of lot area) (17-2-0307). Side setbacks combined 20% of lot width, each at least 2 ft or 8% of width; in RT/RM "no side setback is required to exceed 5 feet" (17-2-0309). Height RS-3 30 ft, RT-3.5 35, RT-4 38 (42 with 25% Type A units, 19 units or fewer), RM-4.5 and RM-5 45 ft under 32 ft frontage and 47 ft at 32 ft or more (17-2-0311). — [Chicago Zoning Ordinance 17-2-0300](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-48935)
- Rules in 17-2-0303 that our engine does not model: ground-floor Type A units are generally excluded from lot-area-per-unit counts in RS-3, RT-3.5 and RT-4; detached houses and two-flats are restricted in certain RT and RM districts near transit; conversion units under 17-2-0303-C may add 33% density to qualifying older buildings. — [17-2-0300](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-48935)
- Chicago Cityscape's "Standard 6-3" (6 units, RM-5+, at least 2,400 sq ft, transit-served) matched 9,560 properties and "Standard 8-3" (8 units, at least 2,880 sq ft in RM-5) matched 7,823 at publication. — [Chicago Cityscape, Standard 6-3 / 8-3](https://publish.obsidian.md/chicagocityscape/standard6383)

### Inferences
- Envelope check, 25 x 125 interior lot (3,125 sq ft), using the rules above (inference, arithmetic):
  - RS-3: FAR 0.9 gives 2,812 sq ft. Envelope: width 25 - 5 = 20 ft; depth 125 - 20 front - 35 rear = 70 ft; 1,400 sq ft footprint x about 2.5 floors under 30 ft = about 3,500 sq ft. FAR binds; setbacks do not change the answer.
  - RT-4: FAR 1.2 gives 3,750 sq ft, 3 units (3,125 / 1,000). Envelope: 20 x (125 - 15 - 35) = 1,500 sq ft x 3 floors under 38 ft = 4,500 sq ft. FAR binds.
  - RM-5: FAR 2.0 gives 6,250 sq ft, 7 units (3,125 / 400). Envelope: 1,500 sq ft x 4 floors under 45 ft = 6,000 sq ft (about 4% under FAR); with the 24% accessible rear setback, 20 x 80 = 1,600 x 4 = 6,400 sq ft and FAR binds again. 7 units in 6,000 sq ft gross is about 857 sq ft each.
  - 25 x 100 RM-5 lot (2,500 sq ft): FAR gives 5,000; envelope 20 x (100 - 12 - 28) = 1,200 x 4 = 4,800 (about 4% under).
  - Conclusion: on standard Chicago interior lots the error from skipping setbacks is 0% in RS/RT and up to about 5% of floor area in RM-5. Units by lot area per unit are not envelope-limited at these sizes. Expect larger errors on corner lots, very shallow or wide-shallow lots, irregular lots and B/C lots where commercial ground floor and rear setbacks interact; I did not fetch the B/C setback text (17-3-0500 series) to quantify.
- Cheap V1 fix: compute the Terner-style envelope cap (frontage, depth, the four setback rules above, height in floors) as a check, not a path, and flag when it is below FAR floor area. That keeps the four-cap method without building the layout planner.
- The realized-capacity literature supports rule 5 (show the math, do not recommend): zoned units are an upper bound, and in LA fewer than 2% of parcels develop in 5 years.

### Gaps
- Monkkonen et al., Kaufmann, Been et al., Urban Institute, Lincoln Institute, Up for Growth, UrbanFootprint/UrbanSim, Envelope, CMAP parcel models and Metropolitan Planning Council capacity numbers were not fetched (budget ran out). No numbers from them are given here.
- No published count found of how many Chicago parcels can legally build 2-6 flats by right; Cityscape's 6-3/8-3 counts are the closest public figures.
- B and C district setback and rear yard rules (17-3-0500 series) not checked.

## Q2. Lot frontage and depth from polygons (choice a)

### Takeaway
The oriented minimum bounding rectangle (OMBR) short side equals frontage on rectangular interior lots, which most Chicago residential lots are. It fails on wide-shallow lots (reports depth as frontage), corner lots (picks the short street side, which may or may not be the code's front), and irregular or notched lots. Frontage drives height in B/C and RM-4.5/RM-5 (32-ft break) and parking exemptions (33-ft break), so errors near those breaks change results. A street-aware method using the address street's centerline is buildable from public data and should replace or check the OMBR.

### Cited Findings
- Our `lot_measures` takes `ST_OrientedEnvelope` of the lot in EPSG:3435 and returns the shorter side as frontage and longer as depth; the column comment calls it "an estimate". — from repo, `/home/user/25x125/db/migrations/0004_shapes_zoning.sql`
- Frontage thresholds in the code that make frontage error matter: RM-4.5/RM-5 height 45 ft under 32 ft frontage, 47 ft at 32 ft or more — [17-2-0311](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-48935); no parking for detached houses or two-flats on lots of record 33 ft wide or less without an improved alley — [17-10-0207](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-50685); RS-1/RS-2 minimum frontage 25 ft (17-2-0302); RS side setbacks are a share of lot width (17-2-0309); setback AA for 20-ft house on a 24-ft-plus lot (17-13-1003-H) — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)
- Terner's simulator does not publish a frontage method; it uses a square footprint — [Terner Labs](https://www.ternerlabs.org/terner-housing-policy-simulator-full-methodology)
- Esri community threads on "calculating frontage" and "identify front" for setbacks exist (practitioners split parcel boundaries into edges and select edges that touch or are near the street right-of-way or centerline); I could not fetch their content, so no method details are cited from them — [Esri community thread list](https://community.esri.com/t5/arcgis-pro-questions/property-setbacks-identify-front/td-p/1001606)

### Inferences
- Better method (inference, buildable now): (1) explode each lot boundary into edges in EPSG:3435; (2) take the lot's address street from `parcel_address` and select that street's segments from the street centerline dataset pr57-gg9e; (3) frontage = total length of lot edges that are within (half right-of-way width + about 5 ft) of that centerline and within about 20 degrees of parallel to it. Chicago residential streets are mostly 66 ft right-of-way (33 ft half width; unverified, check against the centerline file's width field if present). (4) depth = lot area / frontage, or the OMBR side perpendicular to the frontage edge. (5) Corner lot = edges qualify on two different named streets; record both and use the address street as front. Keep the OMBR value as a fallback and flag when the two methods differ by more than 3 ft.
- Cheap checks without the new method: flag when OMBR short side is under 20 ft or over 60 ft, when lot area / (short x long) is under 0.85 (irregular), and when short / long > 0.6 (near square, so front is ambiguous).
- Expected error (inference): near 0 for rectangular interior lots; for wide-shallow lots the reported frontage is the depth (e.g., a 50 x 40 lot reports 40 frontage, 50 depth). Without the database I could not measure the share of Chicago lots affected; measure it on the 35 test parcels plus a random 500-lot sample.

### Gaps
- No published error rates for OMBR vs surveyed frontage found.
- Chicago Zoning Ordinance definitions of "lot frontage", "front lot line" and corner-lot front (17-17 definitions) not fetched.

## Q3. Assigning zoning to parcels (choice b)

### Takeaway
Point-on-surface plus an area share is a reasonable V1 practice, but the lot should take the district with the largest share of its area, not whatever district the point lands in. The point can fall in the minority district on L-shaped or split lots, and the 90% flag then reports the wrong district.

### Cited Findings
- Our job takes the first zoning polygon intersecting the lot's point-on-surface, then stores the share of the lot polygon in that district; `engine/zoning.py` flags under 0.9 and says "Results use that district". — from repo, `/home/user/25x125/jobs/build_parcel_site.py`, `/home/user/25x125/engine/zoning.py`
- The National Zoning Atlas works at the district level and cleans slivers and overlaps before analysis; it does not publish a parcel assignment rule on its public page. — [National Zoning Atlas, How](https://www.zoningatlas.org:443/how)

### Inferences
- Change to area-weighted majority: for each lot, `st_area(st_intersection(lot, district))` over all intersecting districts, take the largest, store the top two with shares. Cost is small (one lateral join). Keep point-on-surface only when the polygon is missing.
- Sliver handling: ignore intersections under about 50 sq ft or 2% of lot area, which come from small boundary misalignments between the county parcel layer and the city zoning layer.
- Chicago-specific risk (inference): B/C strips along arterials often have a fixed depth with R zoning behind, so deep lots along those streets are split. The split-zoned flag should show both districts and both shares, since each part has its own lot area per unit.
- Expected error: unknown share; probably small citywide, concentrated on arterials. Measure the count of lots with top share under 0.9 once the data is loaded.

### Gaps
- No published assessor or atlas standard for parcel-to-district assignment was retrieved.

## Q4. Block face definition for the RS-3 two-flat test (choice c)

### Takeaway
The code tests buildings on the same side of the street between the two nearest intersecting streets. The hundred block is a proxy that both merges and splits real block faces in parts of Chicago. Street centerline segments with address ranges give the real definition from public data. Separately, the denominator should be buildings, not lots.

### Cited Findings
- 17-2-0303 note: in RS-3 minimum lot area per unit may be reduced to 1,500 sq ft, for a two-unit building only, when 60% or more of same-side lots on the block segment have multi-unit buildings (American Legal summary). — [17-2-0300](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-48935)
- Chicago Cityscape quotes it as "If 60 percent or more of the buildings on the same side of the block have two or more units", then "the minimum lot area per dwelling unit is reduced to 1,500 square feet". — [Chicago Cityscape blog](https://www.chicagocityscape.com/blog/restrictive-single-family-only-zoning-district-actually-allows-2-flats-under-extreme-conditions-1dbe9d3cfef0). Note the two sources differ: "lots" (summary) vs "buildings" (Cityscape). The exact code wording needs a direct read.
- ADU caps are counted per "block face and opposite block face combined" (17-7-0573), so the same block-face structure is needed for ADUs. — [Zoneomics mirror, Chapter 17-7](https://www.zoneomics.com/code/chicago-IL/chapter_7)
- Our job builds block face as street + even/odd + hundred block from the first PIN's address; `_block_share` divides multi-unit lots by all lots on the face. — from repo, `/home/user/25x125/jobs/build_lot_use.py`, `/home/user/25x125/engine/zoning.py`

### Inferences
- Where the hundred block fails (inference): Chicago runs 800 address numbers per mile. Where cross streets are 1/16 mile apart (about 330 ft, 50 numbers), one hundred block holds two block faces; where blocks are long or a cross street sits mid-hundred (diagonals, short streets, parks, rail), one block face spans two hundreds. Both change the 60% share.
- Better method: use pr57-gg9e segments. Each segment breaks at intersections and carries from/to address ranges per side (standard for street centerline files; confirm field names in the Chicago file). Assign a lot to the segment of its address street whose range contains its house number and side; a block face = segment + side, merged across consecutive segments only where the break is not an intersection with another named street (alleys and driveways do not count). TIGER/Line edges with address ranges are a fallback.
- Denominator: if the code says buildings, vacant lots should leave the denominator. Today they stay in, which lowers the share and makes the test conservative (misses some qualifying lots). If the code says lots, today's method is right. Resolve with the code text.
- Add a check: show the lots on the block face on the parcel page so the user can confirm the count.

### Gaps
- Exact 17-2-0303 note wording not fetched verbatim. Chicago centerline field names (L/R from/to, ROW width) not confirmed.

## Q5. Point-to-parcel matching tolerance for violations and 311 (choice e)

### Takeaway
A 15 m nearest-lot rule is wider than a standard 25-ft (7.6 m) lot, so a point on the sidewalk or street can land on a neighbor. Most of these records carry an address; matching by address first and using geometry as fallback is the standard approach.

### Cited Findings
- Our job uses the source PIN where given, else the lot containing the point, else the nearest lot within 15 m. — from repo, `/home/user/25x125/jobs/build_parcel_site.py`
- No geocoding-error study could be fetched in this session (budget).

### Inferences
- Geometry (inference): a typical Chicago lot is 25 ft wide (7.6 m). A 15 m radius covers about two lots either side. Points interpolated along a street centerline sit about 10 m (33 ft) from the lot line, so the nearest lot is decided by along-street interpolation error, which is often more than half a lot width.
- Change: match on normalized address (house number, direction, street name, type) to `parcel_address` first; then point-in-lot; then nearest lot within 15 m only when the matched lot's address street equals the record's street; keep a `match_method` column and show it. Counts of violations and 311 calls are score inputs (up to 20 points), so a wrong match moves scores on the neighbor.
- Add a check: report the share of signals matched by each method in the nightly job log.

### Gaps
- Typical positional error of Chicago address points and of 311/violation coordinates: not found. Published literature exists (address-point vs parcel vs street geocoding comparisons) but was not retrieved, so no numbers are given.

## Q6. Counting existing units from Assessor data (choice d)

### Takeaway
The class-code approach is standard but has three concrete defects in our code: only the first card's apartments are used (coach houses on second cards are missed), condo PINs that are parking or storage units may count as dwellings, and 313-399 may include non-apartment class-3 codes. Each is a data check, not a rewrite.

### Cited Findings
- Our job: 299 counts 1 per PIN; 211/212 take `apartments` from the latest-year first card (`distinct on (pin) ... order by pin, tax_year desc, card`), defaulting to 2 for 211 and 1 for 212; 202-210, 234, 278, 295 count 1; regex `^3(1[3-9]|[2-9][0-9])$` counts at least 7. — from repo, `/home/user/25x125/jobs/build_lot_use.py`
- Units now feed the RS-3 block-face share, the Pilsen 3+ rule, the 606/Pilsen demolition surcharge ($20,000 per unit or $60,000 per building) and the "zoning upside" score. — from repo, `/home/user/25x125/engine/zoning.py`, `/home/user/25x125/docs/v1-spec.md`
- 17-13-1003-BB allows certifying existing density up to 1 unit above original construction, which means legal units can differ from Assessor units. — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)

### Inferences
- Multi-card PINs: sum `apartments` across all cards of the latest tax year, and count a second residential card as a building. Today a 2-flat plus coach house reads as 2 units, not 3.
- Condo PINs: Cook County deeded parking spaces and storage units are, as far as I know, also class 299 (unverified). Use the Assessor condominium characteristics dataset's parking/common-area flags to drop them. Without that, a 3-unit condo with 3 deeded parking PINs reads as 6 units.
- Class 3 range: confirm every code in 313-399 against the Assessor class definitions; drop any non-dwelling codes. Unverified whether codes such as 390-399 are all apartments.
- Cross-check: city building footprints (stories, year built) and permit history for 2+ unit permits; flag lots where sources disagree.

### Gaps
- Cook County class code definitions, condo characteristics field names and `apartments` field fill rates were not fetched.

## Q7. Transit-served flag (choice f) and parking rules (17-10-0207)

### Takeaway
Testing the lot point inside the city's TSL buffers is sound, but the parking rule it feeds is wrong in two ways: outside TSLs the ratios vary by district and building type, and Metra-only TSLs still need an administrative adjustment for more than a 50% cut.

### Cited Findings
- 17-10-0207 residential ratios: RS-1/RS-2 2 spaces per unit (no parking for detached houses on lots of record 33 ft or less wide without an improved alley); RS-3 2 per unit for detached houses and 1.5 per unit for two-flats; all other districts 1 per unit, with no parking for detached houses or two-flats on lots of record 33 ft or less wide without an improved alley; B/C -1 to -3 1 per unit; B/C-5 1 per unit for the first 100 units then 0.60. — [17-10-0200](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-50685)
- 17-10-0102-B (as shown on American Legal): TSL = within 2,640 ft of a CTA or Metra rail station entrance or exit, or within 1,320 ft of a CTA bus corridor segment; bike parking at least 1 space per dwelling unit (B.2). The page still shows the older text: up to 100% reduction, more than 50% needs an AA under 17-13-1003-EE, districts RM-5 and up, B, C, D, M. — [17-10-0200](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-50685)
- Ordinance O2025-0015577, adopted 2025-07-16: zero parking by right in TSLs in every district except D; reductions now apply to all R districts (before, only RM); an AA is still needed to go below 50% in D districts and where the lot is transit-served only because of a Metra station. — [Taft Law bulletin](https://www.taftlaw.com/news-events/law-bulletins/chicago-eliminates-parking-requirements-for-transit-served-locations/)
- Effective 2025-09-25; covers 74% of the city. — [Chicago Cityscape](https://www.chicagocityscape.com/blog/chicago-eliminates-parking-requirements-across-most-of-the-city-8d87a6b21f)
- Our engine sets 1 space per unit outside TSLs for every district and 0 inside any TSL, including Metra-only. — from repo, `/home/user/25x125/engine/zoning.py`, `/home/user/25x125/data/rules/zoning_steps.json`

### Inferences
- American Legal's 17-10-0102-B appears not yet updated for O2025-0015577. Use the ordinance text as the rule source and note it.
- Changes: put the 17-10-0207 table in data (by district and building type, with the 33-ft no-alley exemption); for Metra-only TSLs show 50% by right and 0 with an AA. Parking alone changes a 3-flat in RS-3 or a two-flat on a 30-ft lot without an alley; the 33-ft test also depends on correct frontage (Q2).
- TSL edge cases: point-on-surface misses lots partly inside a buffer. Test the lot polygon with `st_intersects` as well and flag "partly inside". Whether the code measures to any part of the lot is not confirmed.

### Gaps
- O2025-0015577 text and current 17-10-0102-B wording not fetched; measurement point (lot line vs building) not confirmed.

## Q8. Administrative adjustment, lots of record and ADU rules (choice g and spec step 4-5)

### Takeaway
The code text on American Legal allows a 10% reduction of minimum lot area (17-2-0301-A), not of lot area per unit. Practitioners (Chicago Cityscape) treat it as reducing lot area per unit. This conflict decides the whole administrative adjustment path and must be resolved before that path is shown. The +10% height is conditional for new buildings. RS ADUs need an administrative adjustment and have per-block annual caps.

### Cited Findings
- 17-13-1003-A, verbatim: "The Zoning Administrator is authorized to approve an administrative adjustment to permit development on a lot that would otherwise be prohibited solely because the lot does not comply with the minimum lot area standards of Sec. 17-2-0301-A, but in no event may the area of the lot be less than 90% of the required minimum lot area." A-2: must meet the general criteria of 17-13-1007-B. A search of 17-13-1000 found no mention of "lot area per unit", "17-2-0303" or "17-3-0402". — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)
- 17-2-0301 minimum lot area: RS-3 and RT-3.5 2,500 sq ft; RT-4 through RM-6.5 1,650 sq ft. Lots of record: "A detached house may be established on any lot of record regardless of the size of the lot", also when an enlarged lot still falls short. — [17-2-0300](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-48935)
- Contrary practice: Cityscape says an AA is needed "to allow eight units on a lot under 3,200 sq ft" in RM-5, and sets the Standard 8-3 floor at 2,880 sq ft (= 90% of 8 x 400). That is a 10% cut in lot area per unit. It also says more than two AAs push a project to the Zoning Board of Appeals. — [Chicago Cityscape, Standard 6-3 / 8-3](https://publish.obsidian.md/chicagocityscape/standard6383); the code says "more than 4 administrative adjustments" for new development must be reviewed as variations (17-13-1002) — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)
- 17-13-1003-L: up to 10% height increase; for a new building only when it "would not result in a building that was taller than buildings on abutting lots", is consistent with the block, and meets 17-13-1007-B (L-3). — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)
- 17-13-1003-I: up to 50% setback reduction to match the predominant yard depth on the block (not townhouses). 17-13-1003-H: side setback cut up to 50% for a 20-ft-wide house on a lot 24 ft or wider. Notice to abutting owners; no decision until at least 10 days after mailing (17-13-1006). — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)
- ADUs in RS areas (17-7-0570 series, Zoneomics mirror): annual cap on conversion units and coach houses per block face and opposite block face combined: 1 in RS-1, 2 in RS-2, 3 in RS-3 (17-7-0573(1)); owner must live in the principal building when it is a detached house (17-7-0573(2)); "No conversion unit or coach house may be authorized without approval of an administrative adjustment" under 17-13-1003-QQ (17-7-0573(3)); ADU areas are amendments to 17-7-0574 covering at least a block face and its opposite face (17-7-0575). — [Zoneomics, Chapter 17-7](https://www.zoneomics.com/code/chicago-IL/chapter_7). American Legal's 17-13-1003 list ends at LL with no QQ, so one of the two copies is out of date — [17-13-1000](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818)
- Secondary summary of the permanent ordinance: permanent citywide 2026-04-01 (Council vote 46-0 in September 2025); eligible parcels grew from about 116,000 to over 320,000; RT, RM and some B/C as of right; RS needs alderperson opt-in (34 of 50 wards at writing); owner occupancy for properties of two or fewer units (one to three in the West, South and Southeast pilot areas); no rentals under 30 days; 2+ ADUs: at least 50% at or below 60% AMI for 30 years; coach house up to 60% of the required rear setback area, 22 ft tall, within the rear 50% of the lot. Not an official source. — [aduzoning.org](https://www.aduzoning.org/blog/chicago-adu-ordinance-what-changed-2026/)

### Inferences
- Engine impact: `units = floor(lot / (0.9 x lot area per unit))` follows Cityscape practice, not the code text found. On a 25 x 108 RT-4 lot (2,700 sq ft) it shows 3 units by AA; under the code text it stays at 2. Until a direct read of the current code (or DPD guidance) settles it, label the AA path "practice, see source" and cite both.
- Height +10%: show it with the L-3 condition ("not taller than buildings on abutting lots"); use footprint stories of neighbors when loaded.
- ADU in RS: approval label should be "administrative adjustment (17-13-1003-QQ)", not "ADU permit"; add the per-block annual cap and owner-occupancy flags, using the same block-face structure as Q4.

### Gaps
- Current official ADU ordinance text and section numbers not fetched from the city; the Zoneomics copy may be the 2021 pilot version. DPD administrative adjustments page could not be fetched (budget).

## Summary verdicts

| Choice | Verdict | Reason and source | Expected error |
|---|---|---|---|
| (a) Frontage = OMBR short side | Add a check now; change to street-aware frontage in M1 | Exact on rectangular interior lots; wrong on wide-shallow, corner and irregular lots. Frontage sets height at 32 ft (17-2-0311) and parking exemption at 33 ft (17-10-0207). Build from pr57-gg9e + address street. | Near 0 on standard lots; depth reported as frontage on wide-shallow lots; share not measured |
| (b) Zoning at point-on-surface, flag under 90% | Change | Use the district with the largest area share; keep top two shares. NZA cleans slivers first ([NZA](https://www.zoningatlas.org:443/how)). | Small citywide, concentrated on split B/C-R lots along arterials |
| (c) Block face = street + parity + hundred block | Change (and resolve denominator) | Code: same side between nearest intersecting streets; hundred blocks merge two faces where cross streets are 50 numbers apart. Use centerline segments. "Buildings" vs "lots" wording conflict ([amlegal](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-48935) vs [Cityscape](https://www.chicagocityscape.com/blog/restrictive-single-family-only-zoning-district-actually-allows-2-flats-under-extreme-conditions-1dbe9d3cfef0)). Needed for ADU caps too. | Unknown; affects every RS-3 two-flat result and ADU cap |
| (d) Units from class codes | Keep, add three checks | Sum apartments across cards (coach houses); drop condo parking/storage PINs; confirm 313-399 list. | 1 unit per lot with coach house; up to double on condo buildings with deeded parking (unverified) |
| (e) Signals: point or nearest lot within 15 m | Change | Address match first; 15 m spans about two 25-ft lots each side. Store match method. | Neighbor mis-assignment likely common on 25-ft lots; not measured |
| (f) TSL flag at point-on-surface | Keep, add check; fix parking | Add polygon intersect for edge lots. Parking: district ratios from 17-10-0207 ([amlegal](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-50685)); Metra-only TSL needs AA below 50% ([Taft](https://www.taftlaw.com/news-events/law-bulletins/chicago-eliminates-parking-requirements-for-transit-served-locations/)). | RS-3 parking understated (2 and 1.5 per unit vs our 1); Metra-only lots overstated as 0 |
| (g) Capacity = LAPU, FAR, height; no setbacks | Keep for V1, add envelope check and missing rules | FAR binds before setbacks on 25 x 125 in RS-3/RT-4; RM-5 envelope about 4% under FAR. Terner uses four caps ([Terner Labs](https://www.ternerlabs.org/terner-housing-policy-simulator-full-methodology)). Add Type A, conversion-unit 33% bonus, AA height condition. Resolve AA lot-area-per-unit conflict ([17-13-1003-A](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-51818) vs [Cityscape](https://publish.obsidian.md/chicagocityscape/standard6383)). | 0% in RS/RT, up to about 5% floor area in RM-5 on standard lots; AA path could overstate by 1 unit per lot if the code text governs |
