# Construction cost per sq ft for Chicago 2-6 flats

Researched 2026-10-29 to set the build-spec presets without contractor data. Hard cost means construction only: no land, soft costs, financing, permits or developer fee.

## Result

| Preset | 2-3 units | 4-6 units | Use |
| --- | --- | --- | --- |
| Production | $165 / sq ft | $170 / sq ft | Small-builder spec flats; default where the area cost index is below 1.3 |
| Standard | $200 / sq ft | $215 / sq ft | Index 1.3 to 1.8 |
| High | $250 / sq ft | $265 / sq ft | Index 1.8 and up (Lincoln Park, Lake View level finishes) |

Range for production: about $150-190. Replace with real job costs when they exist.

## Evidence

| Source | Figure | Hard cost per sq ft it implies |
| --- | --- | --- |
| City of Chicago Missing Middle round 2 awards: West Chatham 3-flats | $308,333 per unit all-in, on city lots | ~$162 (3 x $308,333 / 4,058 sq ft = $228 all-in, divided by 1.41 for contingency, soft cost and financing) |
| Same: Morgan Park 3-flats (Superior Source) | $333,333 per unit all-in | ~$175 |
| Same: Morgan Park six-flats (Far South CDC) | $325,000 per unit all-in | ~$165 (6 x $325,000 / 8,400 sq ft = $232 all-in) |
| NAHB 2024 Cost of Constructing a Home | $428,215 for 2,647 sq ft = $162 per sq ft, national, single-family | x Chicago location index 1.174 (PNNL composite) = ~$190 for custom single-family |
| 37 test buildings (actual sales, spec gross area) | median sale-implied hard cost | ~$133, the ceiling builders could spend and still make 15% on $60,000 land |
| Spec default before review | $235 / $250 | High-spec level only |

Building sizes are Cook County Assessor medians for class 211 buildings built 2014 or later (`x54s-btds`, pulled 2026-10-29): 2-flats 2,730 sq ft (244 buildings), 3-flats 4,058 (512), 4-flats 6,190 (109), 6-flats 8,400 (221). The 1.41 factor is the spec's own cost stack: 5% contingency and 22% soft cost on hard cost, then about 11% financing and carry. Missing Middle budgets also carry developer fees, so the hard cost they imply is if anything lower.

With production at $165 / $170, 20 of 37 test buildings show a profit of $0 or more at their actual sale with $60,000 land, and the median return on cost is 0.9%. That matches the spec's expectation that new 3-flats outside stronger areas run thin margins.

## Sources

- [Missing Middle round 2 selected proposals](https://www.chicago.gov/city/en/sites/missing-middle/home/selected-proposals/round-2.html)
- [NAHB Cost of Constructing a Home, 2024](https://nahb.org/-/media/AB4EFC742624475A97A0A62189986FF8.ashx)
- [PNNL location factors report (Chicago composite 117.40)](https://www.energycodes.gov/sites/default/files/2021-11/Location_Factors_Report.pdf)
- [Chicago YIMBY: two East Garfield Park 3-flats at $450,000 reported cost each](https://chicagoyimby.com/2026/08/three-flats-permitted-for-3330-3332-west-walnut-street-in-east-garfield-park.html) (reported permit costs run low; context only)
