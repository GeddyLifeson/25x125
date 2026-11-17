# Dallas, Texas: notes

Checked 2026-11-17. Estimates, not tax, legal, zoning or appraisal advice.

## What was read

- **District standards.** The City of Dallas zoning district pages, one per district
  (https://dallascityhall.com/departments/sustainabledevelopment/planning/Pages/zoning-districts.aspx).
  32 pages were read: height, density, FAR, lot coverage, lot size. They are the city's own summary of
  Dallas Development Code Chapter 51A, Article IV. Each page says "general guidelines ... there may be exceptions".
- **Parking.** The adopted parking ordinance, file 25-0763 (DCA190-002), passed 2025-05-14, 170 pages. Read
  Sec. 51A-4.209(b)(2)(C), (5)(C), (6)(C) and Sec. 51A-4.301(a)(2). The ordinance number is not legible in the scan.
- **ADUs.** Ordinance 30931 (Sec. 51A-4.510, ADU overlay) and Ordinance 30930 (Sec. 51A-4.209(b)(6)(E), Board of
  Adjustment special exception), both passed 2018-06-27, plus the city ADU page.
- **State law.** The city's SB 840 information sheet (2025-08-25) and SB 15 information sheet (2025-09-08), and the
  enrolled bill text of both on capitol.texas.gov.
- **GIS, permits, appraisal data.** All tested with real requests on 2026-11-17 (below).

## What could not be read

- **The code itself on American Legal** (codelibrary.amlegal.com/codes/dallas). The site returned HTTP 403
  (Cloudflare challenge) to every automated request. The Wayback Machine is blocked from this environment. So the
  district numbers come from the city's summary pages, not the code text. Someone should open Sec. 51A-4.112 to
  51A-4.125 in a browser and compare. The city pages carry no revision date.
- **Section numbers.** The city pages cite only "51A-4.100". The parking ordinance confirms Sec. 51A-4.124 (central
  area), 51A-4.126 (multiple commercial), 51A-4.127 (urban corridor), 51A-4.209 and 51A-4.301. The numbers used for
  the other districts (4.112 single family, 4.113 duplex, 4.114 townhouse, 4.115 clustered housing, 4.116
  multifamily, 4.121 office, 4.122 retail, 4.123 commercial service, 4.125 mixed use) follow the ordinance's section
  list but were not read on a page that names them. Subsection letters are left out for that reason.
- **Minimum lot width.** The city pages give none for any district. The column is blank. Not confirmed against the
  code or the subdivision rules (Article VIII).
- **Whether the ADU rules changed after 2018.** The city ADU page still describes the 2018 rules and says a 2020
  amendment case was suspended. No later ADU ordinance was found. Not confirmed against the current code.
- **Rules for 3 to 8 unit buildings in the zoning code.** On 2025-04-23 the council changed the building code so
  buildings of up to 8 units can use the residential code. The city's release says this was done "without changing
  zoning". No 2025 or 2026 ordinance that cuts minimum lot sizes in R districts was found.
- **Zoning reform.** The city released "Dallas Development Code Public Draft #1" on 2026-11-06. It is a draft.
  Public meetings run 2026-11-18 to January 2027. No adoption date. When it passes, every row here needs a recheck.

## How the tables were built

- 32 districts: R-1ac(A), R-1/2ac(A), R-16(A), R-13(A), R-10(A), R-7.5(A), R-5(A), D(A), TH-1(A), TH-2(A),
  TH-3(A), CH, MF-1(A), MF-1(A)(SAH), MF-2(A), MF-2(A)(SAH), MF-3(A), MF-4(A), MU-1, MU-2, MU-3, and 11 office,
  retail and commercial districts where housing is allowed only by SB 840: NO(A), LO-1, LO-2, LO-3, MO-1, MO-2,
  GO(A), NS(A), CR, RR, CS.
- `match` uses the codes exactly as stored in `ZONE_DIST` on the city layer.
- **No FAR in R, D, TH, CH, MF-1 and MF-2.** The `far` column is blank and the engine derives floor area from lot
  coverage and height. No story limit applies in these districts.
- **TH and CH density** is units per acre in the code: 6, 9, 12 (TH-1, 2, 3) and 18 (CH). Converted with 43,560 /
  units per acre. TH lots need 2,000 sq ft for a single family structure and 6,000 for a duplex; the table carries
  the 2,000 figure.
- **MF districts set lot area per unit by bedroom count.** The table uses the two-bedroom figure: 1,800 (MF-1),
  1,200 (MF-2), 550 (MF-3), 325 (MF-4). Studios and one-bedrooms need less; each bedroom over two adds 200, 150,
  50 and 50 sq ft. Under SB 840 the city says it cannot enforce these minimums for buildings of 3 or more units.
- **MU-3 has no density cap.** The engine needs a number, so the row carries 1,210 sq ft per unit (36 units per
  acre, the SB 840 floor). That is a stand-in, not a code figure. FAR 3.2 is the real limit.
- **Office, retail and commercial rows.** The base code does not allow multifamily there. The rows exist so the
  engine can show the SB 840 path. They use 1,210 sq ft per unit (36 per acre), no FAR, the district's lot coverage,
  and the greater of the district height and 45 ft. Known gap: on a lot under 3,630 sq ft the engine shows 1 or 2
  units, but SB 840 covers only 3 or more. The `tx_sb840_commercial_only` flag says so on every such lot.
- **Heights** are in feet in the code; no story conversion was needed. NO(A) and NS(A) allow 35 ft with a gable,
  hip or gambrel roof and 30 ft otherwise; the base figure is 30 and the table shows the 45 ft SB 840 floor.
  MU-1 and MU-2 rise to 120 and 180 ft only in a mixed use project with retail; the table uses 90 and 135.
- **Residential proximity slope.** In CH, MF, MU and non-residential districts, anything over 26 ft must sit under
  a slope from nearby R, D and TH lots. The table height can be out of reach next to houses. It is a flag, not a
  computed limit.
- **Rezoning targets** are a judgment about what a small developer would ask for. They are not from the code.

## State overrides

- **SB 840** (Local Government Code Ch. 218, effective 2025-09-01). 3 or more units by right where office,
  commercial, retail or warehouse use is allowed. Density floor 36 units per acre, height floor 45 ft, setback
  ceiling 25 ft, no FAR, at most 1 parking space per unit. Dallas reads the density rule as no cap at all, because
  some Dallas districts have no cap. The city's sheet lists A(A), NO(A), LO-1/2/3, MO-1/2, GO(A), NS(A), CR, RR, CS,
  LI and MC-1 to MC-4 as newly opened to housing. The engine path uses 36 per acre because that is the only number
  in the law; the real ceiling is height, setbacks, coverage and parking.
- The override is also applied to CH, MF and MU rows. The city's sheet says the standards apply "regardless of the
  district" and its map legend lists MF, MU and CH. The statute text ties the standards to multifamily and
  mixed-use residential development. A lawyer should confirm the reach in MF-only districts.
- Exclusions (IR and IM, 1,000 ft from heavy industry, 3,000 ft from an airport or military base, clear zones)
  are not mapped here. The city said it would publish a GIS layer; none was found on gis.dallascityhall.com.
- **SB 15** (effective 2025-09-01) only helps unplatted tracts of 5 acres or more. It is a flag with no unit path.

## Data sources tested

- **Zoning layer:** https://gis.dallascityhall.com/arcgis/rest/services/sdc_public/Zoning/MapServer/15, field
  `ZONE_DIST`. 60 distinct values (listed in region.json). 1,004 of the polygons are PD. A point query worked.
- **Overlays on the same service:** historic (layer 2, 158 features), NSO (5, 13), conservation district
  subdistricts (8, 25), PD subdistricts (9, 1,259), deed restrictions (0, 975), height map (12), demolition delay
  (19, 4). No ADU overlay layer exists on the service, so ADU overlay areas cannot be mapped.
- **Flood:** FEMA NFHL layer 28. No city floodplain layer was found.
- **Permits:** Socrata `e7gq-4sah` on www.dallasopendata.com. 397,045 rows, 2018-01-01 to 2026-11-17, updated
  daily. `issued_date` is text in MM/DD/YY form, so sort and filter with `like`. No unit count, coordinates or
  parcel ID. Permit type names changed at some point (new names in 2026 rows). No newer dataset was found.
- **DCAD:** `DCAD2026_CURRENT.ZIP`, 206,556,643 bytes, 14 CSV files dated 2026-11-09, free. Market value, year
  built, living area and land area per account are all there (field names in region.json). No sale prices.
- **Parcels:** city copy of DCAD parcels at .../Basemap/DallasTaxParcels/MapServer/0, `ACCT` joins to
  `ACCOUNT_NUM`.

## Not covered

- PD (planned development) and CD (conservation district) zoning: each has its own ordinance.
- A(A), MH(A), P(A), IR, IM, LI, CA-1(A), CA-2(A), MC-1 to MC-4, UC, the form districts (WMU, WR), MU-1(SAH),
  MU-2(SAH), MU-3(SAH), and the old Chapter 51 codes still on the map (MF-2, GR, O-2).
  MC and LI are open to housing under SB 840 but their pages were not usable (MC) or the district is industrial (LI).
- Mixed Income Housing Development Bonus (extra height and coverage for affordable units).
- Setbacks. The city pages list them but the table has no column for them.
- Dallas County cities other than Dallas, and the parts of Dallas in Collin, Denton, Kaufman and Rockwall counties
  (DCAD covers Dallas County only).
