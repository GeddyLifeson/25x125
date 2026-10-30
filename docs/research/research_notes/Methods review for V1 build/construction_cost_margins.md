# Construction cost method and dollar margins for 2-6 unit buildings (Chicago)

Researched 2026-10-30. Scope: how to estimate hard cost for new 2-6 unit wood-frame buildings from free public data, and how wide the dollar margin should be at each estimate stage. Current defaults are in `data/rules/feasibility_defaults.json` (production $165/$170, standard $200/$215, high $250/$265 per sq ft; 5% contingency; 22% soft cost; margins -20/+30, -15/+20, -10/+15, -5/+5).

Method note: the web-fetch budget for the session ran out partway through (HTTP 403 from the proxy after about 100 fetches across all agents). The HUD MAP Guide fee limits, the Terner Center "Making It Pencil" assumptions and the Brookings cost breakdown could not be read and are listed under Gaps. One local analysis was run on the repo's own permit file (`data/reference/permits_2to6_clean_city.json`, 836 rows); its results are marked "local analysis".

## 1. AACE estimate classes and how they map to our stages

### Takeaway
The building-construction version of the AACE class system (56R-08, and ASTM E2516-11 built on it) gives a Class 5 (screening) range of -20% to -30% low and +30% to +50% high. Our feasibility band of -20% / +30% sits at the narrow end of Class 5. Our bid band of -5% / +5% is narrower on the high side than AACE allows for any class short of a near-complete check estimate. The ranges apply after contingency, around a point estimate set near the 50% confidence level, and are skewed upward at every class.

### Cited Findings
- Building and general construction matrix, "Adapted from ASTM E2516-11" and based on AACE practice (the document cites 56R-08 in its reference list), Alberta Infrastructure, Design & Technology Series #19, July 16, 2025 — [Alberta Infrastructure](https://www.alberta.ca/system/files/infra-tr-dt-series-19-estimates.pdf):

  | Class | Project definition | End use | Method | Low | High |
  | --- | --- | --- | --- | --- | --- |
  | 5 | 0-2% | Feasibility or screening | Building area factoring, parametric models, expert judgment | -20% to -30% | +30% to +50% |
  | 4 | 1-15% | Concept study | Parametric, assembly models, functional space pricing | -10% to -20% | +20% to +30% |
  | 3 | 10-40% | Budget control | Unit cost line items at assembly level | -5% to -15% | +10% to +20% |
  | 2 | 30-70% | Control or bid/tender | Detailed take-offs and unit costs | -5% to -10% | +5% to +15% |
  | 1 | 70-100% | Check estimate or bid/tender | Bottom-up, deterministic take-offs | -3% to -5% | +3% to +10% |

- The same Alberta document is internally inconsistent: its narrative gives Class 5 as "-30% to +50%", and it says "the accuracy range should always be determined through risk analysis" and not set in advance. It gives no contingency percentages by class — [Alberta Infrastructure](https://www.alberta.ca/system/files/infra-tr-dt-series-19-estimates.pdf)
- The process-industry version (AACE 18R-97, February 2, 2005 revision) is wider: Class 5 -20% to -50% / +30% to +100%; Class 4 -15% to -30% / +20% to +50%; Class 3 -10% to -20% / +10% to +30%; Class 2 -5% to -15% / +5% to +20%; Class 1 -3% to -10% / +3% to +15% — [AACE 18R-97 mirror, PDF4PRO](https://pdf4pro.com/view/18r-97-cost-estimate-classification-system-as-applied-2e8aba.html). The same tables are reproduced without attribution by [EPCLand](https://epcland.com/aace-estimate-classification-system/) and, using the outer bounds only, by [Mastt](https://www.mastt.com/guide/cost-estimate-classes).
- 18R-97 footnote: the ranges are the "typical percentage variation of actual costs from the cost estimate after application of contingency (typically at a 50% level of confidence) for given scope" — [AACE 18R-97 mirror](https://pdf4pro.com/view/18r-97-cost-estimate-classification-system-as-applied-2e8aba.html)
- AACE terminology (10S-90): contingency "is generally included in most estimates, and is expected to be expended"; it excludes major scope changes, management reserve and escalation — [Wikipedia, Cost contingency, quoting AACE 10S-90](https://en.wikipedia.org/wiki/Cost_contingency)

### Inferences
- Stage mapping:

  | Our stage | What exists | AACE class | AACE band (building) | Current band |
  | --- | --- | --- | --- | --- |
  | Feasibility (screening) | Parcel, unit count, $/sq ft preset | 5 | -20..-30 / +30..+50 | -20 / +30 |
  | Layout (site study) | Massing and unit plan from the layout planner | 4 | -10..-20 / +20..+30 | -15 / +20 |
  | Drawings (schematic to design development) | Plans, assembly-level quantities | 3 | -5..-15 / +10..+20 | -10 / +15 |
  | Bids | Priced subcontractor or GC bids | 2 (1 only when every trade is bid) | -5..-10 / +5..+15 | -5 / +5 |

- Feasibility -20/+30 is defensible only because the presets were checked against Missing Middle budgets and actual sales. Our method is pure "building area factoring" with no contractor input yet, which is the bottom of Class 5. A high side of +35% to +40% is within AACE until the contractor session confirms the presets.
- Layout at +20% is the narrowest Class 4 high; +25% is the midpoint.
- Bids at +5% is below the Class 2 range (+5 to +15) and is a Class 1 figure. Small-builder bids leave allowances, exclusions and change-order exposure, so +10% is the better default.
- The 18R-97 footnote puts the point estimate near P50 after contingency. So the central figure is a median, and contingency belongs in the central figure because it is expected to be spent.
- AACE ranges are often described as roughly 80% to 90% confidence intervals. I could not confirm the exact confidence level from a primary AACE text in this session (see Gaps). If the high end is about P90, labeling it "P80" (as `cost_confidence` does now) overstates the confidence of the P80 figure.

### Gaps
- The 56R-08 text itself is behind AACE's paywall. The table above is Alberta's adaptation of ASTM E2516-11, which follows 56R-08. I could not read 56R-08 directly to confirm every cell, or its statement on the confidence level of the range.
- No public study tests AACE ranges on 2-6 unit residential buildings.

## 2. Reference class forecasting and overrun distributions

### Takeaway
Every source that reports a distribution finds cost error skewed upward: medians are well below means, and the upper tail is long. For "standard buildings" the UK Treasury's optimism-bias guidance puts the capital-cost uplift between 2% (late, well-defined) and 24% (early). An asymmetric margin, with a larger high side, is justified. No public reference class exists for US 2-6 unit buildings.

### Cited Findings
- UK Green Book supplementary guidance (from Mott MacDonald 2002, "Review of Large Public Procurement in the UK"), capital expenditure optimism bias: standard buildings upper 24%, lower 2%; non-standard buildings upper 51%, lower 4%; standard civil engineering 44% / 3%. Works duration for standard buildings: 4% / 1%. The values are "indicative starting values", and the upper bound "does not represent the highest possible values" — [NHS Wales Specialist Estates, Optimism bias](https://nwssp.nhs.wales/ourservices/specialist-estates-services/specialist-estates-services-documents/ircf-business-case-and-scrutiny-guidance-misc-docs/optimism-bias/); also [GOV.UK Green Book supplementary guidance](https://www.gov.uk/government/publications/green-book-supplementary-guidance-optimism-bias)
- Oxford Global Projects (Budzier, supervised by Flyvbjerg), reference class of 89 light-rail extensions: cost overrun mean 32%, P50 17%, P80 57%, P90 86%, P95 104%. New-build projects were "statistically significantly different from extensions" and were excluded. No date on the document — [City of Edinburgh, Reference Class Forecast for York Place to Newhaven](https://www.edinburgh.gov.uk/tramstonewhaven/downloads/file/90/the-university-of-oxford-report-reference-class-forecasting)
- Love, Wang, Sing and Tiong (2013), "Determining the probability of project cost overruns", Journal of Construction Engineering and Management 139(3): 321-330, DOI 10.1061/(ASCE)CO.1943-7862.0000575. Overruns from contract award on 276 Australian construction and engineering projects were not normally distributed; the best overall fit was a three-parameter Fréchet distribution (a heavy right tail). Contracts under A$1 million fit a Cauchy distribution — [PolyU research portal](https://research.polyu.edu.hk/en/publications/determining-the-probability-of-project-cost-overruns/)
- Repo context: `feasibility_defaults.json` already follows Homes England practice, treating the central figure as P50 and the high margin as P80, with a refit once 20 or more completed projects exist (`docs/international-practices.md`).

### Inferences
- The overrun evidence covers large public projects. Small private buildings have a shorter tail because there is less scope churn, a single owner-builder and short schedules. The UK "standard buildings" band (2% to 24%) is the closest public analog. It suggests about +24% of optimism at the earliest stage, sitting on top of a central estimate that is itself unbiased, and less than 5% once design is complete.
- A lognormal model makes the asymmetry concrete. If the high margin H is the P90, then sigma = ln(1 + H) / 1.2816. For H = 30%: sigma = 0.205, P10 = -23%, P80 = +19%. For H = 35%: sigma = 0.234, P10 = -26%, P80 = +22%. So -20 / +30 is close to a lognormal with sigma of about 0.2, and the asymmetry comes from the shape and needs no hand-tuning.
- A small builder at screening stage should therefore expect a P50 overrun near 0% against a calibrated estimate, with a P80 of about +20% and a P90 of about +30% to +35%. This is inferred from the shapes above, not from a measured residential reference class.
- The Love et al. finding that contracts under A$1 million fit a Cauchy distribution (undefined mean, very fat tails) is a warning: small jobs have rare but very large overruns. These tend to come from foundations, soil or utility surprises, which is why a site-condition flag should widen the high side.

### Gaps
- No US study of cost overruns on 2-6 unit residential buildings was found. Search results for residential overrun studies returned only non-US or non-peer-reviewed sources.
- Flyvbjerg's "How Big Things Get Done" (2023) appendix with mean overrun by project type, including buildings, could not be read in this session.
- The fitted Fréchet parameters and probability tables in Love et al. (2013) are behind the ASCE paywall.

## 3. Per-sq-ft cost evidence for 2-6 unit wood frame, Chicago and Midwest, 2023-2026

### Takeaway
Public evidence brackets small-builder hard cost in Chicago at about $150-$200 per sq ft in 2024-2026 dollars, which supports the production preset of $165/$170. National cost tables times an old Chicago location factor give $182-$200. Missing Middle budgets carry a prevailing-wage and MBE/WBE premium, so backing hard cost out of them likely overstates the cost for a private small builder.

### Cited Findings
- ICC Building Valuation Data, August 2025, national average square-foot construction cost: R-2 (multifamily) Type VA $162.43, VB $155.12; R-3 (one- and two-family) VA $182.23, VB $170.80. It includes foundation, structure, electrical, plumbing, mechanical and interior finishes, excludes land, and "does not take into account any regional cost differences". The next update is February 2026 — [ICC BVD, Aug 2025 (City of Kirkland copy)](https://www.kirklandwa.gov/files/sharedassets/public/v/2/development-services/pdfs/building-pdfs/icc-august-2025.pdf)
- NAHB Cost of Constructing a Home, 2024 (fall 2024 survey, published January 20, 2025; 41 usable builder responses out of 4,000; national only). Average price $665,298; construction cost $428,215 (64.4% of price) for 2,647 sq ft, about $162 per sq ft; overhead and general expenses 5.7%; financing 1.5%; marketing 0.8%; commission 2.8%; profit 11.0%; lot 13.7%. In 2022 the figure was $153 per sq ft on 2,561 sq ft. Construction cost by stage: interior finishes 24.1%, rough-ins 19.2%, framing 16.6%, exterior finishes 13.4%, foundations 10.5%, site work 7.6%, final steps 6.5%, other 2.1% — [NAHB, Cost of Constructing a Home 2024](https://nahb.org/-/media/AB4EFC742624475A97A0A62189986FF8.ashx)
- NAHB analysis of Census Survey of Construction, 2024 single-family starts: contractor-built (custom) median $166 per sq ft nationally ($162 in 2023); spec homes excluding lot $153 ($150 in 2023). East North Central (includes Illinois) custom median $186 per sq ft. Figures exclude land and are regional medians — [NAHB Eye on Housing, Oct 2, 2025](https://eyeonhousing.org/2025/10/square-foot-prices/)
- Chicago Missing Middle round 2, market-rate for-sale units, 108 in total, all on city lots (per-unit figures are total cost divided by units): Project Simeon 2000, West Chatham, 4 three-flats, $3.7M, $308,333 per unit; Far South CDC, Morgan Park, 4 six-flats, $7.8M, $325,000; Superior Source, Morgan Park, 6 three-flats, $6.0M, $333,333; Famor, Morgan Park, 6 three-flats + 2 four-flats, $8.8M, $366,667; Toro Construction, 3 three-flats + 2 four-flats, $7.1M, $417,647; NHS Redevelopment, South Chicago, 4 two-flats + 5 townhomes, $6.0M, $461,538 — [City of Chicago, Missing Middle round 2](https://www.chicago.gov/city/en/sites/missing-middle/home/selected-proposals/round-2.html)
- Missing Middle North Lawndale selections (webinar of April 11, 2025; per unit derived): Alteza 23 units at $6.4M (about $278,000 per unit); Beauty for Ashes 11 at $3.4M (about $309,000); Trumbull Collective 16 at $5.6M (about $350,000); CBBC 16 at $5.9M (about $369,000); Sunshine Management 33 at $18M (about $545,000). Subsidy is $50,000-$150,000 per unit, capped at $5M per applicant — [City of Chicago, Missing Middle webinar 041125](https://www.chicago.gov/content/dam/city/sites/missing-middle/webinar_041125.pdf)
- Missing Middle program conditions that raise cost: "Projects must pay prevailing wage rates for all construction jobs"; at least 26% of qualified project costs to MBEs and 6% to WBEs; Chicago residents must perform at least half of construction-worker hours; vertical construction must start within 60 days of the RDA. Lots sell for $1 — [Missing Middle Program Guide, April 2025](https://chicago.gov/content/dam/city/sites/land-sales/2025/Missing_Middle_Program_Guide_April2025_FINAL.pdf)
- Terner Center (March 2020, California, 2018 dollars): prevailing-wage projects cost about $30 more per sq ft after controls; hard costs are "more than sixty percent" of total development cost; statewide average hard cost $222 per sq ft in 2018 — [Terner Center, The Hard Costs of Construction](https://ternercenter.berkeley.edu/wp-content/uploads/2020/08/Hard_Construction_Costs_March_2020.pdf)
- Repo: `docs/construction-costs-2026-10-29.md` backs out about $162-$175 per sq ft of hard cost from the Missing Middle round 2 three-flats and six-flats, using the spec's 1.41 all-in factor and Assessor median building sizes (3-flat 4,058 sq ft, 6-flat 8,400).

### Inferences
- The national figures closest to a 2-6 unit wood-frame building in 2025 are ICC R-2 VB $155 and R-3 VB $171. Times the Chicago residential composite of 1.174 (2011, see question 7) they give $182 and $200. NAHB's $162 times 1.174 gives $190. These national figures include builder overhead and profit to different degrees (NAHB's $162 excludes the 5.7% overhead and 11% profit; ICC's inclusions are not stated in the excerpt I read). They support standard ($200/$215) as an "outside-contractor, typical spec" figure, and production ($165/$170) as an owner-builder or low-overhead figure.
- Missing Middle budgets include prevailing wage, MBE/WBE participation and resident-hiring rules. Terner's California estimate puts the prevailing-wage premium alone at about $30 per sq ft (2018). Backing $162-$175 out of these budgets therefore probably overstates a private small builder's hard cost. The production preset is not too low on this evidence. The existing note that developer fees push the implied hard cost lower points the same way.
- The Missing Middle per-unit spread is wide: $278,000-$545,000 across 11 selections, or $308,000-$462,000 in round 2. Around a round 2 median of about $350,000 that is -12% / +32%. This is a ready-made local check on the feasibility-stage band, and it is consistent with -20 / +30.

### Gaps
- RSMeans square-foot model values for 1-3 story apartments in Chicago: no publicly quoted 2024-2026 figure was found. RSMeans data is paid and was not used.
- Chicago Housing Trust, ARO in-lieu fee analyses, ULI Chicago, MPC and IHDA cost-per-unit reports: not reached before the fetch budget ran out.
- Terner Center "Making It Pencil" (December 2023) assumptions could not be fetched in this session (the URL is already cited in `feasibility_defaults.json`).
- Census/HUD Survey of Construction does not publish multifamily cost per sq ft by metro.

## 4. Reliability of permit reported cost

### Takeaway
Chicago's reported cost on new-construction permits is a rounded applicant estimate. 69% of the 836 values are exact multiples of $50,000. The fee is set by floor area, construction type and scope, so the spec's explanation ("reported costs run low because permit fees are based on them") does not hold for new construction. The values are usable as a coarse relative index. They should not be used as a dollar level, and the 3-flat group is clearly low against every other source.

### Cited Findings
- Chicago's permit fee calculator asks for "construction type, occupancy type, area in square feet, and project scope". The page does not mention reported cost or valuation as a fee input. It reflects the 2024 fee structure — [City of Chicago, Permit fee calculator](https://chicago.gov/city/en/depts/bldgs/provdrs/permits/svcs/permit_fee_calculator.html). This matches the repo's own permit-fee formula (`gfa x construction_factor x scope_factor`).
- ICC publishes its valuation table so building departments can set a permit valuation independent of the applicant's figure: "Bid prices also do not change the value used for permit fees" (paraphrase from the August 2025 table) — [ICC BVD, Aug 2025](https://www.kirklandwa.gov/files/sharedassets/public/v/2/development-services/pdfs/building-pdfs/icc-august-2025.pdf)
- Local analysis of `data/reference/permits_2to6_clean_city.json` (836 permits, 2022-2026; 102 self-certified):

  | Units | Permits | Median reported | P25-P75 | Median per sq ft (Assessor median size) |
  | --- | --- | --- | --- | --- |
  | 2 | 213 | $450,000 | $350,000-$750,000 | $165 (2,730 sq ft) |
  | 3 | 490 | $450,000 | $380,000-$625,000 | $111 (4,058 sq ft) |
  | 4 | 58 | $903,000 | $600,000-$1,200,000 | $146 (6,190 sq ft) |
  | 6 | 62 | $1,200,000 | $734,400-$1,658,100 | $143 (8,400 sq ft) |

  69.0% of reported costs are exact multiples of $50,000, and 82.4% are multiples of $10,000.
- Repo: sale prices ran a median 2.3 times reported permit cost on the test set (`docs/v1-spec.md`).

### Inferences
- The heaping at $50,000 shows that applicants enter a round guess. Each value carries up to ±$25,000 of rounding alone, which is ±5% on a $450,000 3-flat.
- The 3-flat median ($450,000, the same as the 2-flat median, on 49% more floor area) points to a habitual figure rather than a measured cost. A 3-flat at $111 per sq ft is about 33% below the production preset and about 40% below ICC R-2 VB times 1.174 ($182). The 2-flat median of $165 per sq ft happens to match production.
- Since fees do not depend on the figure, understatement comes from habit, applicants entering only part of the scope (shell, or the GC contract without owner-bought items), and possibly concern that the figure feeds assessments. That last point is unverified.
- Using permits only to rank areas, within unit-count groups (already done in v2), at half weight, is the right call. The index needs a test: it is reliable only if the understatement ratio is the same across areas, and that cannot be checked without actual job costs. Until then, keep the half weight and treat the index as a rough ordering.

### Gaps
- No published study comparing US permit valuations with audited final costs was found. Searches returned only forum threads and local news.
- I could not confirm whether the Cook County Assessor uses permit reported cost in valuation.

## 5. Soft costs, contingency and developer fee norms

### Takeaway
Housing finance agencies require at least 5% hard-cost contingency on new construction (10% on rehab), cap combined A/E fees near 3.3% of total development cost, and cap GC profit, overhead and general requirements at 6% / 2% / 6% of construction cost. The 22% soft-cost line is plausible. Its parts are not verified, so it should be broken into named lines.

### Cited Findings
- New Mexico MFA 2025 Universal Multifamily Underwriting Supplement (Nov 7, 2024): "New construction costs will be underwritten to include a minimum construction contingency of 5% of hard construction costs"; rehab and adaptive reuse minimum 10%; builder profit up to 6% of construction cost (4% with identity of interest); builder overhead up to 2%; general requirements up to 6%; architect and engineering combined "capped at 3.3 percent of Total Development Cost"; developer fee up to 14% of TDC (4% LIHTC), and for 9% LIHTC the lesser of $2.5M or 14% — [NM MFA 2025 Underwriting Supplement](https://housingnm.org/uploads/documents/2025_Universal_Multifamily_Initial_Underwriting_Supplement_11.07.2024.pdf)
- IHDA underwriting guide changes, January to October 2023: hard cost contingency is computed "as a percent of trade payments and site work" (October 2023; January had included general conditions and GC overhead and profit); soft cost contingency "up to 5%" in January 2023, "Not mentioned" in October 2023; total developer fee with an Authority soft loan capped at $2,000,000 (down from $2,500,000) — [IHDA, Comparison Chart UW Guide 2023](https://www.ihda.org/wp-content/uploads/2023/11/Comparison-Chart-UW-Guide-January-2023-to-October-2023.pdf)
- NAHB 2024 builder cost stack, as a share of sale price: overhead and general expenses 5.7%, financing 1.5%, marketing 0.8%, commission 2.8%, profit 11.0% — [NAHB CCH 2024](https://nahb.org/-/media/AB4EFC742624475A97A0A62189986FF8.ashx)

### Inferences
- The 5% contingency matches the HFA floor for new construction at bid stage. Because AACE treats contingency as expected spend and puts the range on top (question 1), keep 5% in the central figure at every stage and let the stage margin carry the design uncertainty. Raising contingency at early stages would push up the central figure that was calibrated against Missing Middle and sales at 5%. To stay consistent, production would have to drop to about $153 per sq ft ($228 all-in / (1.10 x 1.22 x 1.11)). The total would be unchanged, so the change would only reshuffle the lines.
- The 22% soft cost needs a breakdown, so users can see and override each part. A starting split for review: A/E 6-8% of hard on a small building (above the 3.3%-of-TDC LIHTC cap, which assumes large projects; unverified for 2-6 units); survey, soils and testing 1-2%; insurance and builder's risk 1-2%; legal, title and closing 1-2%; GC general requirements and overhead 6-8% if a third-party GC is used. Permit fees, the Open Space Impact Fee and financing are already separate lines. Each of these splits is an assumption for Marlon's contractor to check, not a sourced figure.
- An owner-builder that is also the GC earns its profit through the developer margin. So GC profit should not appear twice in the hard cost and in "return on cost". Production assumes no third-party GC markup; standard and high presets carry one. State this in the preset notes.

### Gaps
- HUD MAP Guide 4430.G allowances (builder's general overhead, profit, A/E limits) could not be fetched after the budget ran out. The [gocodebook copy, section 5.12.3](https://gocodebook.com/library/us/federal/us-hud-map-guide-4430-g-2020-rev2021-03-19/5.12.3-allowances-and-fees) is the URL to read.
- IHDA's current QAP total-development-cost limits were not retrieved.
- No public source for A/E fee percentages on 2-6 unit Chicago buildings. Marlon's architect or contractor should supply one.

## 6. Cost escalation indices

### Takeaway
The series in the defaults now (WPUIP2311001) covers goods inputs to residential construction only and excludes labor, so on its own it misstates the change in hard cost. Use a blend of materials and labor, or the Census constant-quality under-construction index, and keep Turner and ENR as context only.

### Cited Findings
- FRED series WPUIP2311001 is titled "Producer Price Index by Commodity: Inputs to Industries: Net Inputs to Residential Construction, Goods" — [FRED](https://fred.stlouisfed.org/series/WPUIP2311001)
- NAHB's description of the PPI inputs series used in its Remodeling Input Price Index: "both PPI measurements exclude labor, capital investment, and imports"; residential-inputs and remodeling-inputs 12-month changes correlate at 0.9991 since December 2014 — [NAHB RIPI methodology, Sept 2026](https://eyeonhousing.org/wp-content/uploads/2026/09/RIPI_Methodology_Document-FINAL.pdf)
- April 2026 PPI: inputs to residential construction up 5.9% year over year including energy; goods +6.1%; services +3.7%; building materials excluding energy +3.7%, "the fastest pace in three years"; softwood lumber +1.1%; diesel +74.4% — [NAHB, May 14, 2026](https://www.nahb.org/blog/2026/05/building-material-prices-increase-at-fastest-pace-in-three-years)
- Census price indexes of new single-family houses under construction: monthly, national, Laspeyres and Fisher; "Land and other nonconstruction costs are not included"; values come from regression on house characteristics in the Survey of Construction — [Census, comparison of price indexes](https://census.gov/construction/cpi/pdf/comparisonofpriceindexes.pdf); [Census CPI page](https://www.census.gov/construction/cpi/index.html)
- Turner Building Cost Index, Q2 2026: +1.4% quarter over quarter, +5.2% year over year. It is built from Turner's own projects (labor rates and productivity, materials, competition), and demand is driven by data centers and manufacturing — [Construction Dive](https://www.constructiondive.com/news/turners-building-cost-index-q2-2026/826514/)

### Inferences
- Materials are roughly half of hard cost for wood-frame residential (inferred from NAHB's stage shares; no direct labor/material split was found). A goods-only index moves about twice as much as hard cost when materials swing, as lumber did in 2021-2022, and misses labor inflation when they do not.
- Recommended rule: escalate presets by the Census constant-quality index of single-family houses under construction. It is an output price that includes labor and builder margin, excludes land, and comes out monthly. Show WPUIP2311001 beside it as a materials signal. If a residential-specific blend is wanted later: 0.5 x PPI goods inputs + 0.5 x BLS average hourly earnings for residential building construction (CES series to be confirmed).
- Turner and ENR are nonresidential and large-contractor indices. They are context only for 2-6 unit wood frame.
- Escalate to the expected construction midpoint, not just to today. With 2-3 months of permit time (median 50-85 days in the defaults) plus half of a 12-month build, that is about 8-9 months forward. At the 3.7%-5.9% annual input inflation of 2026, this adds about 2.5%-4%. Show it as its own line, since AACE contingency excludes escalation.

### Gaps
- The current value and recent change of the Census under-construction index were not shown on the page fetched.
- The exact BLS CES series ID for residential building construction earnings was not verified.

## 7. Location factors and a within-city index

### Takeaway
The only free Chicago factor found (117.40) dates from 2011. It is driven by labor (labor index 150.27, materials 95.75) and is residential. Labor and material prices barely vary within one city, so neighborhood cost differences mostly reflect finish level, building type and site conditions. That supports applying the permit index at half weight or less, and not on top of a preset that it also selects.

### Cited Findings
- Faithful+Gould for PNNL, "Residential Energy Efficiency Measures: Location Factors", December 21, 2011 (revision of January 12, 2012). Chicago composite 117.40; labor index 150.27 (union 151.73, Davis-Bacon 167.77, BLS 131.30); materials index 95.75. The composite averages labor, materials and three proprietary indices (RSMeans Residential 2011, Compass 2010, A.C.E.). Indices "are applied to the total estimated national average costs" — [PNNL / energycodes.gov](https://www.energycodes.gov/sites/default/files/2021-11/Location_Factors_Report.pdf)
- ICC valuation data is a national average and leaves regional modifiers to the local authority — [ICC BVD, Aug 2025](https://www.kirklandwa.gov/files/sharedassets/public/v/2/development-services/pdfs/building-pdfs/icc-august-2025.pdf)

### Inferences
- With labor at 150 and materials at 96, the Chicago premium is a labor premium (union and prevailing-wage rates). Non-union small builders sit nearer the BLS labor index (131), which would put the composite closer to about 1.10 (inferred; F+G does not publish that split). This is another reason production should sit below NAHB or ICC times 1.174.
- Double counting: the spec text and `neighborhood_adjustment` apply `1 + 0.5 x (index - 1)` to every area, with Lincoln Park's 1.94 becoming 1.47. The same index also selects the high preset. On the spec as written, a Lincoln Park 3-flat is costed at $250 x 1.47 = $368 per sq ft. The calibration scripts do something else: they apply the adjustment only on the production preset, capped at index 1.3, and use 1.0 for standard and high (`scripts/research/2026-10-29/cal.py` line 26, `run10.py` line 60). The JSON and spec should be changed to match the calibrated rule. Otherwise the engine will reproduce the double count.

### Gaps
- No free, current (2023-2026) Chicago city cost index was found. ENR's Chicago city cost index pages exist but are paywalled.
- No study measures construction cost variation within one US city by neighborhood.

## Recommendations (each tied to the findings above)

1. **Presets: keep production at $165/$170.** It sits inside $150-$190 from four independent checks: Missing Middle back-out $162-$175 (an upper bound because of prevailing wage); NAHB $162; ICC R-2 VB $155; 2-flat permits $165. Relabel standard ($200/$215) as "with third-party GC markup", which matches ICC or NAHB times 1.174 ($182-$200). Keep high for luxury finish. Write the calibrated adjustment rule into the JSON: adjustment applies only on production, capped at index 1.3; standard and high use 1.0.
2. **Margin bands (asymmetric, AACE building classes, applied after contingency):**
   - Feasibility, Class 5: **-20% / +35%** until the contractor session confirms the presets, then -20% / +30%. Keep the +10 points when area data is thin.
   - Layout, Class 4: **-15% / +25%**.
   - Drawings, Class 3: **-10% / +15%** (no change).
   - Bids, Class 2: **-5% / +10%** (high side up from +5%).
3. **P80 label:** treat the high margin as about P90 and compute P80 as central x exp(0.8416 x ln(1 + high) / 1.2816). That gives +19% at a +30% high and +22% at +35%. The alternative is to rename the high end "high case" and drop the P80 claim.
4. **Contingency:** keep 5% of hard cost in the central figure at all stages (HFA new-construction floor; AACE treats contingency as expected spend). Do not stack early-stage contingency on top of margins that already carry it.
5. **Soft costs:** replace the single 22% with named, overridable lines (A/E, survey and soils, insurance, legal and closing, GC general requirements and overhead when there is a third-party GC). The defaults should sum to about 22% until the contractor supplies real figures. Show developer or builder profit only as return on cost, never inside hard cost for production.
6. **Escalation:** switch the preset escalator to the Census constant-quality under-construction index. Show the PPI goods index as a materials signal. Add an escalation line to the construction midpoint (about 8-9 months, 2.5%-4% at 2026 rates), outside contingency.
7. **Permit index:** keep it within unit-count groups at half weight. Record on screen that reported costs are rounded applicant estimates (69% are multiples of $50,000) and do not set fees. Fix the spec's stated reason. Replace the index with actual job costs when they exist.
8. **Refit:** keep the Homes England rule. Once 20 or more completed jobs exist, set the bands from the observed P10 and P90 of actual cost against the stage estimate.
