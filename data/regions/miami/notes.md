# Miami notes

Checked 2026-11-17. City of Miami only (Miami-Dade County). Zoning code: Miami 21.

## What was read

- Miami 21 Code on codehub.gridics.com. The City's own page ("View City of Miami Zoning Code (Miami 21)") names this site as the complete codification. The full text was pulled from the site's public JSON endpoint (`/api/v1/codehub/45?_format=json`, 1,565 sections, 4.4 MB) and read as text.
- The amendments list on that copy runs through Ord. 14484 (2026-07-28). The site carries a notice that it may lag the latest legislation.
- Sections read: 1.1 and 1.2 (definitions), 3.3, 3.4, 3.5, 3.12.2, 3.18, Article 4 Tables 2, 3 and 4, Article 5 sections 5.3 to 5.6 with Illustrations 5.3, 5.4, 5.5, 5.6 (T6-8, T6-12), 5.3.8, Article 6 Table 13 (T3, T4), 7.1.2.8, 7.2.7.
- Fla. Stat. 166.04151(7) (Live Local Act) on leg.state.fl.us.
- GIS: every layer in region.json was queried on 2026-11-17 and returned data.
- Not used as a source: the PDF sheets at gis.miami.gov/Miami21Docs (T3.PDF and so on). They are dated January 2018 and are out of date for ADUs and density.

## Districts covered (15)

T3-R, T3-L, T3-O, T4-R, T4-L, T4-O, T5-R, T5-L, T5-O, T6-8-R, T6-8-L, T6-8-O, T6-12-R, T6-12-L, T6-12-O. The `match` codes are the exact `M21_ZONE` values in the zoning layer.

## How Miami 21 numbers were converted

- Density is in units per acre. `lot_area_per_unit_sqft` = 43,560 / units per acre: 9 -> 4,840, 18 -> 2,420, 36 -> 1,210, 65 -> 670.15, 150 -> 290.4.
- T3-R and T3-L are single-family, so `lot_area_per_unit_sqft` is the 5,000 sq ft minimum lot (per the contract), and `max_units` is 1.
- T3-O: `max_units` 2. The code says 2 units may be built on any single lot. The engine's floor(lot / 2,420) gives 1 unit on a lot under 4,840 sq ft, which is lower than the code allows.
- T3, T4 and T5 have no FLR. `far` is a ceiling from coverage x stories: T3-R/L 0.50 + 0.30 = 0.8 (second floor is capped at 30% coverage); T3-O 0.50 x 2 = 1.0; T4 0.60 x 3 = 1.8; T5 0.80 x 5 = 4.0. Setbacks and open space will cut these further.
- T6 uses Floor Lot Ratio (FLR): 5 for T6-8, 8 for T6-12. FLR is entered as `far`. Public Benefit bonuses (25% and 30%) are not included.
- Heights: T3 is 25 ft and T4 is 40 ft in the code. T5 (5 stories), T6-8 (8) and T6-12 (12) have no limit in feet, so 12 ft per story is used: 60, 96 and 144 ft. The code allows up to 14 ft per story and 25 ft at ground level (Sec. 3.5.2), so real buildings can be taller than these figures.

## Uncertain or not confirmed

1. Live Local Act zones. The statute covers areas "zoned for commercial, industrial, or mixed use". The file lists the L and O zones because the Miami 21 use table allows commercial uses there. The City's own list of qualifying zones was not found. R zones are left out.
2. T4 lot area. Article 4 Table 2 says "1,400 s.f. - 20,000 s.f." Illustration 5.4 says 5,000 sq ft minimum (1,400 with rear vehicular access) and 40,000 maximum. The Illustration is used. The two parts of the code disagree on the maximum.
3. ADUs in T5 and T6. Table 3 allows an ADU on single-family lots in T5 and T6, but Table 13 gives size limits only for T3-L, T3-O and T4. Those zones are in `also_allowed_no_size_row`, not `by_district`.
4. Rounding. No rule was found for rounding a fraction of a unit in the density math. Rounding down is used.
5. T6-8A-O and T6-8B-O appear in the zoning layer (4 polygons). The base code text read has no T6-8A or T6-8B standards. They are not matched and will show as not covered.
6. Density bonuses are flagged, not modeled: Diagram 9 increase areas, Sec. 3.4.5 station areas, Resilience Fund Area, affordable and workforce programs, TOD density transfer.
7. NCD-1, NCD-2 and NCD-3 (Appendix A) change lot and building rules in Coral Gate and Coconut Grove. Appendix A was not read. The overlay layer is recorded so the app can flag these lots.
8. Historic rules are in Chapter 23 of the City Code (Municode). Municode blocked fetches (HTTP 403), so Chapter 23 was not read.
9. HVHZ. The source is a Florida Building Commission flyer (2012) that states HVHZ is Miami-Dade and Broward counties. The current Florida Building Code text was not read.
10. `fhfa_metro` 33124 (Miami-Miami Beach-Kendall metropolitan division) is from memory, not checked against the FHFA file.
11. The Historic_Districts layer was last edited in 2021. Districts designated since then may be missing.
12. ADU count. Sec. 3.18 speaks of "an ADU" on a lot with a single-family house. One per lot is used; the code has no sentence that states the count.

## Not covered

- T6-24 and higher, CI, CI-HD, CS, D1, D2, D3, T1.
- Special Area Plans, NRD-1 and NRD-2 (Wynwood), SD-16.3, SD-27.1, SD-27.2.
- Setbacks, frontage, open space and green space rules (read, but the contract has no columns for them). T3: 20 ft front, 5 ft side with 20% of lot width in total, 20 ft rear, 25% green space. T4: 10 ft front, 0 ft side, 5 ft rear (20 ft next to T3), 15% open space. T5 and T6: 10 ft front, 0 ft side and rear, 10% open space.
- Waterfront standards (Sec. 3.11).

## Data sources

- Zoning layer: `M21_Zoning/FeatureServer/0` on the City's ArcGIS Online org, field `M21_ZONE`, 1,130 polygons, 36 values, last edited 2026-05-07.
- Permits: `Building_Permits_Since_2014/FeatureServer/0`, 237,663 rows, issued dates 2012-03 to 2026-11-16. `ScopeofWork = 'NEW CONSTRUCTION'` returns 52,656 rows, which looks high for new buildings alone; it likely counts sub-permits. `TotalCost` is text. There is no unit count, so units must come from another source.
- Rezoning fact for small developers: a rezoning needs 40,000 sq ft of land or 200 ft of frontage on one street, unless it extends an existing transect boundary. Most single 5,000 sq ft lots do not qualify alone.
