# Hand run: 10 test parcels through the spec math

Run 2026-10-29 by script (`scripts/research/2026-10-29/run10.py`) against the spec formulas, the production/standard/high presets, the 2,450-sale comp pool and live zoning, permit and Assessor data. Land is the $60,000 default. Marlon still needs to add the questions he would ask on a real deal.

## Results

4 of 10 sale estimates land within 15% of the actual sale. Two of the misses are problems with the test sale itself, not the estimate (see questions 1 and 2).

| Address | Area | Zoning | Lot sq ft | Units built | Units by right | Preset | Total cost | Sale estimate | Actual sale | Error | Profit at actual sale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3146 S SHIELDS AVE | Armour Square | RT-4 | 3,125 | 3 | 3 | production | $899,474 | $1,045,000 (15 comps, 1.5 mi) | $1,350,000 | -23% | $369,526 |
| 5843 W CORCORAN PL | Austin | RT-4 | missing | 3 | ? | production | $876,723 | $556,803 (8 comps, 0.75 mi) | $740,000 | -25% | $-181,123 |
| 2840 W 36TH PL | Brighton Park | RT-4 | 3,125 | 3 | 3 | production | $722,015 | $1,058,366 (58 comps, 3 mi) | $845,000 | +25% | $72,285 |
| 325 S RICHMOND ST | East Garfield Park | RT-4 | 3,166 | 2 | 3 | production | $724,037 | $643,333 (57 comps, 1.5 mi) | $659,000 | -2% | $-104,577 |
| 6106 N HERMITAGE AVE | Edgewater | RS-3 | 6,075 | 2 | 2 | production | $727,323 | $1,283,851 (47 comps, 1.5 mi) | $1,115,000 | +15% | $320,777 |
| 4317 S INDIANA AVE | Grand Boulevard | B3-3 | missing | 3 | ? | production | $967,728 | $1,020,000 (20 comps, 0.75 mi) | $1,075,000 | -5% | $42,772 |
| 1244 N KEDZIE AVE | Humboldt Park | RT-4 | 4,125 | 4 | 4 | production | $1,019,191 | $2,460,000 (40 comps, 0.75 mi) | $575,000 | +328% | $-478,691 |
| 3035 N SHEFFIELD AVE | Lake View | B2-2 | 3,125 | 3 | 3 | high | $1,445,641 | $2,815,682 (114 comps, 0.75 mi) | $1,300,000 | +117% | $-223,641 |
| 6853 W BELMONT AVE | Montclare | B3-1 | missing | 4 | ? | production | $961,892 | $1,418,431 (6 comps, 1.5 mi) | $1,370,000 | +4% | $325,908 |
| 2132 W RICE ST | West Town | RT-4 | 2,952 | 3 | 2 | standard | $1,169,868 | $1,965,000 (172 comps, 0.75 mi) | $2,050,000 | -4% | $757,132 |

## Questions the tool could not answer

1. **Is the test sale the whole building?** 1244 N Kedzie recorded $575,000 twice (February 2025 and May 2026), both on "Other" deeds. That looks like a transfer between related parties, not a market sale. The test set needs a deed-type and repeat-price filter, and this building should come out of it.
2. **Was the building finished when it sold?** 3035 N Sheffield sold for $1,300,000 in March 2026 on a warranty deed. That is $216 per sq ft in Lake View, where new 3-flats sell for about twice that. It may have sold as a shell. The comp pool needs a check that the sale came after the certificate of occupancy (or the Assessor's first full-year value).
3. **Where is the lot size when the PIN changed?** 3 of 10 parcels have no lot size in the Assessor's residential characteristics. 5843 W Corcoran and 4317 S Indiana still show as vacant land (class 100) on the permit PIN, because the finished building moved to new condo PINs. 6853 W Belmont is commercial (class 590). The engine needs lot area from parcel polygons as the fallback, and a link from the old PIN to the new condo PINs.
4. **Which approval path did 2132 W Rice use?** The lot is 2,952 sq ft. RT-4 allows 2 units by right (1,000 sq ft per unit), but 3 were built. The 90% administrative adjustment covers it (2,700 sq ft needed). The engine has to show that path by name.
5. **How big is the building?** The spec sizes a 3-flat at 4,032 sq ft (1,200 per unit x 1.12). Assessor sizes for these buildings run 4,044 to 6,028 sq ft. Sale and cost both move with size, so the parcel page needs a building-size input and the pattern library sizes.
6. **Sell as condos or as one building?** Per-unit comps mix condo sales and whole-building sales. On the North Side, condo units sell for much more per unit than whole buildings. The feasibility screen needs a sale-structure choice that picks the matching comps.
7. **How far is too far for comps?** 2840 W 36th Pl (Brighton Park) had to reach 3 miles for 6 comps and came out 25% high. The margin should widen at 3 miles, as the spec says, and the screen should say why.
8. **What does land cost?** Every run used $60,000. The land value map (step 3) replaces this; until then the user types a price.
9. **Which ground-floor rule applies?** 4317 S Indiana (B3-3) and 6853 W Belmont (B3-1) need the ground-floor residential flag: B3 is not B2. The engine flagged nothing because the lot size was missing, so the flags must not depend on lot size.
10. **What does the Open Space Impact Fee add?** Per the 2025 city worksheet and the 2024 ordinance, the fee depends on unit size, not area. In 2026 it is $1,044 per unit for 800-1,599 sq ft units, so about $3,100 on a 3-flat. It is now a cost line.

Sources: [Chicago zoning (dj47-wfun)](https://data.cityofchicago.org/resource/dj47-wfun.json), [building permits (ydr8-5enu)](https://data.cityofchicago.org/resource/ydr8-5enu.json), [Assessor residential characteristics (x54s-btds)](https://datacatalog.cookcountyil.gov/resource/x54s-btds.json), [Assessor sales (wvhk-k5uv)](https://datacatalog.cookcountyil.gov/resource/wvhk-k5uv.json), [OSIF worksheet 2025](https://www.chicago.gov/content/dam/city/depts/zlup/Sustainable_Development/Publications/OSIFworksheet2025_fillableform.pdf), [OSIF ordinance 2024](https://chicago.gov/content/dam/city/depts/zlup/Sustainable_Development/Publications/SubstituteOrd_OSIF_2024.pdf).
