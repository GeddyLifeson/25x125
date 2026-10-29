# Calibration run, 2026-10-29

What changed in the data and defaults after the review, and how the estimates now score against the 37 test buildings. Scripts are in `scripts/research/2026-10-29/`.

## Sale values

The permit-to-sale match gave 37 comps citywide. The new pool uses the Assessor's year built instead:

- 2-6 unit buildings (class 211 in `x54s-btds`) built 2014 or later: 283 first sales after construction.
- Condo units in 2-6 unit buildings (`3r7i-mrz4`) built 2014 or later: 2,167 first unit sales, from 1,373 buildings.
- Total 2,450 comps, saved as `data/reference/new_construction_sales.csv`. 30 community areas and 43 Assessor neighborhoods now have 5 or more.

Method: same unit-count group within 0.75 mile, widening to 1.5 and 3 miles; at least 6 comps; sales within 4 years; inverse-distance weighted median per unit; the building's own sale left out.

| Method | Within 15% of actual | Median error |
| --- | --- | --- |
| Spec method, community-area median (37 comps) | 22 of 37 (59%) | not computed |
| New pool, weighted median per unit | 24 of 37 (65%) | 12% |
| New pool, $ per sq ft x default unit size | 18 of 37 (49%) | 16% |
| New pool, whole-building sales only | 21 of 37 (57%) | 13% |

The per-unit method is the new default. It is 5 points short of the 70% target. Most misses are 2-flats near pricier condo stock (Humboldt Park, North Lawndale, Hermosa, Edgewater) and one 4-unit Humboldt Park building that sold at $143,750 per unit. The next gains need building size for the subject (the user enters it, or the layout planner supplies it), then MLS closed sales once the MRED feed is approved. The spec now shows a sale range (25th to 75th percentile of the weighted comps) so the uncertainty is visible.

## Test set cleanup (later on 2026-10-29)

Two test sales were not market sales of finished buildings and came out of the test set (`data/reference/test_parcels_removed.csv`): 1244 N Kedzie ($575,000 recorded twice on "Other" deeds) and 3035 N Sheffield ($216 per sq ft in Lake View, likely sold before completion). The comp filters that would have caught them are in `feasibility_defaults.json` under `sale_comps.filters`.

On the remaining 35: sale estimate within 15% on 24 (69%), median error 8%. Profit of $0 or more at actual sale on 20 (57%), median return on cost 1.0%.

## Cost index

The old index mixed unit counts: reported cost per unit is $225,000 for 2-flats and $150,000 for 3-flats, so areas that build mostly 3-flats looked cheap. The new index (`cost_index_by_area_v2.csv`) divides each permit by the median for its unit-count group before taking the area median. It also drops 5 cancelled permits and 3 repeated addresses (828 permits used).

Biggest moves: Logan Square 1.51 to 1.16, North Center 1.70 to 1.33, Avondale 1.44 to 1.11, Austin 0.90 to 0.78, Armour Square 1.05 to 0.83.

## Base hard cost

At $235/$250 per sq ft, 4 of 37 test buildings show a profit at their actual sale with $60,000 land, and the median return on cost is -27.5%.

| Base, 2-3 / 4-6 units | Test buildings with profit of $0 or more | Median return on cost | Standard 3-flat, per unit, before land |
| --- | --- | --- | --- |
| $235 / $250 (old) | 4 of 37 | -27.5% | $402,544 |
| $185 / $200 | 12 of 37 | -9.2% | $317,049 |
| $165 / $180 | 20 of 37 | 0.9% | $282,851 |
| $155 / $170 | 24 of 37 | 6.8% | $265,752 |
| Presets by area (new default, production $165/$170) | 20 of 37 | 0.9% | $282,851 (production) |

New default: three build-spec presets. Production $165/$170 (set from published costs in `construction-costs-2026-10-29.md`; first pass was $160/$175), standard $200/$215, high $250/$265, chosen by the area's cost index (below 1.3, 1.3 to 1.8, 1.8 and up). A production 3-flat with $60,000 of land comes to about $303,000 per unit, inside the Missing Middle check ($308,000-365,000, -20%/+30%).

Thin margins at the median match what the spec expected for new 3-flats outside stronger areas. The production preset is backed by published costs in `construction-costs-2026-10-29.md`. Real job costs replace it when available.

## Other rule changes

- Financing is computed on cost before financing, so the formula is no longer circular.
- Cost margins apply to every line except land.
- Opportunity Zone value is $0 for build-and-sell (the exclusion needs a 10-year hold). Bonus depreciation is labeled as tax deferral.
- Rezoning takes a user-picked target district.
- Tax-delinquent points leave the V1 score until a licensed feed exists.

## Data portal check

All Chicago and Cook County datasets in `data/sources/datasets.csv` answered a one-row query on 2026-10-29. The parcel universe (`pabr-t5kh`) already carries ward, community area, census tract, Assessor neighborhood and TIF district for each PIN, which removes several spatial joins. Transit-served areas, fire limits, the 606/Pilsen districts and ADU areas are not on either data portal; they need the city's GIS layers or a hand-digitized map.
