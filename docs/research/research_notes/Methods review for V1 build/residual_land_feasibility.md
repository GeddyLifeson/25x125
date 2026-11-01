# Residual land value and development feasibility for 2-6 unit projects: methods review against the V1 spec

Scope: judge the V1 feasibility math (docs/v1-spec.md "Feasibility math", data/rules/feasibility_defaults.json, data/rules/incentives_v1.csv) against established methods. Research date 2026-10-30. Worked numbers below marked "computed" were run in Python on the spec's own defaults (script at /tmp/claude-0/-home-user-25x125/8b22a33b-54d0-5e07-8c9b-16c20823ced6/scratchpad/rlv.py). Items marked UNVERIFIED come from memory or from search-result titles I could not open; the shared web-fetch budget ran out partway through, so several primary PDFs were not read.

## 1. How is residual land value formulated, and how is developer return expressed and benchmarked?

### Takeaway
The standard structure is: land value = gross development value (GDV) - build costs - fees and other costs - finance - developer return. Our formula matches that. Practice expresses return as profit on cost (most common for residential) or profit on GDV. UK benchmarks are 15-20% of GDV (about 17.6-25% on cost) and 20% on cost for permitted, low-risk sites, rising to 25% for riskier ones. US builder data show about 11% net profit and about 20.7% gross margin on revenue. Our 15% return on cost (13.0% on GDV) sits at or below the low end of every benchmark found.

### Cited Findings
- UK Planning Practice Guidance (PPG) on viability: for plan-making, "an assumption of 15-20% of gross development value (GDV) may be considered a suitable return to developers". A lower figure may suit affordable housing, where a guaranteed end sale "reduces risk" (para 019, ID 10-019-20190509). — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- PPG: benchmark land value "should be established on the basis of the existing use value" (EUV) of the land plus a landowner premium; "This approach is often called 'existing use value plus' (EUV+)" (para 014). The premium "should reflect the minimum return" at which a reasonable landowner would sell (para 017). EUV excludes hope value (para 016). — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- PPG: alternative use value is allowed only for uses that "would fully comply with up to date development plan policies", backed by evidence of costs and values, without double-counting the premium (para 018). — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- PPG: GDV for residential is total sales or capitalised net rental income (para 012). Site-specific assessments may use "market evidence (rather than average figures) from the actual site", adjusted, with outliers excluded. — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- PPG costs list (para 013, revised 12 Feb 2024): build costs, abnormals, infrastructure, policy contributions, "general finance costs including those incurred through loans", professional, sales and legal costs. "Explicit reference to project contingency costs should be included" in site-specific work. — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- PPG: "The price paid for land is not a relevant justification for failing to accord with relevant policies in the plan" (para 002, revised 16 Dec 2025). — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- Crosby, Devaney and Wyatt (University of Reading, research for RICS), RICS Land Journal, 12 March 2020:
  - Profit on cost is the most common cash-margin measure among residential developers and in most viability appraisals. Profit on GDV is used less often, and IRR rarely.
  - Required margins were mostly 15-20%. Residential developers commonly cited 20% on cost for sites with no significant risk (for example, with planning permission) and 25% for higher-risk sites. Larger developers using cash-flow models quoted 10-12% a year.
  - 20-25% on cost implies about 15-20% on GDV.
  — [RICS Land Journal, "Approaches to developer returns in appraisals"](https://ww3.rics.org/uk/en/journals/land-journal/approaches-to-developer-returns-in-appraisals.html)
- Same article, on the RICS guidance note *Valuation of development property* (1st edition, October 2019):
  - Finance can sit inside a residual as a rough stand-in for the development timeframe.
  - In a full cash-flow model, finance should not be mixed with revenues and costs; the cost of capital belongs in the discount rate.
  - Simple cash margins ignore when money arrives, so a residual can approximate a cash flow only if the target margin is adjusted for project risk.
  — [RICS Land Journal](https://ww3.rics.org/uk/en/journals/land-journal/approaches-to-developer-returns-in-appraisals.html); guidance note copy hosted at [Broxbourne CD2.18](https://www.broxbourne.gov.uk/downloads/file/1871/cd2-18-valuation-of-development-property-rics-1st-edition-october-2019) (not opened)
- NAHB Cost of Doing Business study (single-family builders): gross profit margin 18.2% (2020) rising to 20.7% (2023); net profit margin 7.0% (2020) rising to 8.7% (2023), highest in over three decades after the 10% peak in 1991. — [NAHB press release, April 2025](https://www.nahb.org/news-and-economics/press-releases/2025/04/nahbs-new-study-provides-statistics-and-data-on-builder-financial-performance)
- NAHB 2024 Cost of Construction Survey, shares of average sales price: construction 64.4%, finished lot 13.7%, builder profit 11.0%, overhead and general 5.7%, sales commission 2.8%, financing 1.5%, marketing 0.8%. — [NAHB Eye on Housing, Jan 2025](https://eyeonhousing.org/2025/01/cost-of-constructing-a-home-in-2024/)
- Profit on cost and profit on GDV convert as: on GDV = on cost / (1 + on cost). So 15% on cost = 13.0% on GDV; 20% = 16.7%; 25% = 20.0%. The UK range of 15-20% of GDV equals 17.6-25.0% on cost. (Arithmetic.)
- Feasly's 15-20% margin-on-cost band, already in feasibility_defaults.json, is an Australian practitioner guide, not a standard. — [Feasly](https://www.feasly.com.au/guides/development-margin-on-cost-vs-revenue-australia) (cited in repo; not re-read)

### Inferences
- Our formula structure is standard. Two details differ from practice:
  - Finance is a share of cost that includes land, so the spec's max-land formula `net sale / (1 + r) - (total cost - land)` is not exactly consistent. Changing land changes finance. Solving properly, with C0 = non-land cost before financing and f = finance-and-carry factor: **L = net sale / ((1 + r)(1 + f)) - C0**. On the spec defaults f = 0.65 x 0.08 x (1 x 0.55 + 0.5) + 0.015 x 1.5 = 0.0771 (computed).
  - Computed effect for the standard Humboldt Park 3-flat (3 x $308,333 sale, $165/sf, index 1.0): spec formula gives -$160,742; the exact solve gives -$144,941. The gap is $15,800, 1.7% of net sale. The gap grows with the finance factor.
- NAHB's 11% builder profit share of price is about 12.4% on cost (0.11 / 0.89). That is after overhead, which our model does not carry as a line. NAHB's 20.7% gross margin is about 26% on cost, before overhead. A small Chicago builder with no corporate overhead line would land between 12% and 26% on cost depending on what our 22% soft cost covers. The 15% default is defensible only as a low-end reference. It sits below the UK 20% on cost for permitted sites and well below the 25% "higher risk" figure. Most V1 parcels are unpermitted, which is the higher-risk class.
- PPG's "lower return where end sale is guaranteed" maps to the Missing Middle program, where buyers and price caps are set. It is a reason a single fixed target is a simplification.
- PPG para 002 lines up with our "show the numbers" rule: the residual is computed from GDV and costs, never backed out from an asking price.

### Gaps
- I did not open the RICS guidance note itself to quote its wording on profit or finance; only the RICS Land Journal summary.
- No public US standard for small-builder target return on cost found. The Appraisal Institute's "land residual technique" (The Appraisal of Real Estate) is paywalled; I found no public quote with numbers. US merchant-builder 15-25% on cost is a common practitioner figure, but I found no primary source in this session (UNVERIFIED).
- NAHB margin data are national, single-family, and skewed to larger members. No 2-6 unit or Chicago split was published on the pages read.

## 2. How sensitive is the residual, and what does best practice say about sensitivity tables, Monte Carlo and P50/P80?

### Takeaway
The residual is a small number left over after subtracting large ones, so input errors magnify in it. Computed on our own defaults, a 5% sale-value miss moves residual land value by 29%, and a 5% sale miss plus a 5% cost miss moves it by 52%. The literature recommends showing sensitivity grids and probability-based results instead of a single figure. Our current "-20%/+30% on every cost line plus 25th/75th sale percentile" corner case is wider than a probabilistic P10-P90. It also mislabels +30% as P80.

### Cited Findings
- Clapp, Cohen and Lindenthal (2023), "Are Estimates of Rapid Growth in Urban Land Values an Artifact of the Land Residual Model?", *J. Real Estate Finance and Economics* 66(2): 373-421, DOI 10.1007/s11146-021-09834-4:
  - Land-residual theory "overestimates structure value" in cross section and is correct only at the highest-and-best-use structure size.
  - In their model, near-teardown property has a true land ratio of 0.8, but the residual gives 0.57.
  - Maricopa regressions overestimate marginal land residual values by about $9,200 per $1,000 increase in the residual.
  - Residual-based land shares grew about 24% over six years, against about 11% in their option-value estimate.
  — [Springer](https://link.springer.com/article/10.1007/s11146-021-09834-4)
- Evans (1992), "Monte Carlo Analysis: A Practical Application to Development Appraisal", *Journal of Property Finance* 3(2), DOI 10.1108/09588689210033846. It argues deterministic site appraisal has shortcomings and that Monte Carlo on a residual (not a cash flow) gives a fuller picture. The abstract has no numbers. — [Emerald](https://www.emerald.com/insight/content/doi/10.1108/09588689210033846/full/html)
- Crosby and Wyatt (2016), "Financial viability appraisals for site-specific planning decisions in England", *Environment and Planning C*. — [SAGE](https://journals.sagepub.com/doi/abs/10.1177/0263774X16636118) (title and venue only; content not read)
- McAllister (University of Reading), response to the GLA draft viability guidance: "a standard profit assumption is clearly inappropriate"; "no standard method in practice" for applying the residual. He suggests reports present several land value estimates on different bases. — [GLA consultation response](https://www.london.gov.uk/media/37275/download)
- Homes England, *Optimism Bias and Contingency at Homes England*: reference-class P50/P80 uplifts. Our repo's international-practices note records the worked example in which a 10% contingency gave a 35% chance of staying on budget. — [GOV.UK accessible version](https://www.gov.uk/government/publications/optimism-bias-and-contingency-at-homes-england/optimism-bias-and-contingency-at-homes-england-accessible-version); [PDF](https://assets.publishing.service.gov.uk/media/65b93630ee7d49000d9849f7/Optimism_Bias_and_Contingency_at_Homes_England.pdf)
- AACE International 18R-97 estimate classes: the ranges are commonly quoted as Class 5 at -20% to -50% / +30% to +100%, Class 4 at -15% to -30% / +20% to +50%, and Class 3 at -10% to -20% / +10% to +30%. They are usually described as about an 80% confidence interval (UNVERIFIED; from memory, consistent with search-result titles at [epcland AACE summary](https://epcland.com/aace-estimate-classification-system/), not opened).
- Computed sensitivities on our defaults (f = 0.0771, target 15%), for a stylized parcel with net sale $1,500,000 and non-land cost $1,000,000, base residual $210,981:

  | Change | Residual | Change in residual |
  |---|---|---|
  | Sale -5% | $150,432 | -28.7% |
  | Sale -10% | $89,883 | -57.4% |
  | Cost +5% | $160,981 | -23.7% |
  | Cost +10% | $110,981 | -47.4% |
  | Sale -5% and cost +5% | $100,432 | -52.4% |
  | Target 10% / 15% / 20% / 25% | $266,026 / $210,981 / $160,524 / $114,103 | |

  Each $1 of net sale moves the residual by $0.81; each $1 of non-land cost moves it by $1.00. (computed)
- Computed corner case versus Monte Carlo, same parcel with land fixed at $200,000:
  - Central profit is $207,480.
  - Spec low corner (sale -10%, cost +30%): -$265,650. Spec high corner (sale +10%, cost -20%): +$572,900.
  - Monte Carlo with sale lognormal (sigma 0.148, so P25/P75 is about ±10%) and cost triangular (0.8, 1.0, 1.3), 100,000 draws: profit P10 -$122,632, P20 -$24,337, P50 $174,962, P80 $391,764, P90 $513,037. Chance of loss 23%.
  - The cost multiplier from that triangle is 1.026 at P50 and 1.125 at P80, not 1.30. (computed)

### Inferences
- The spec's `cost_confidence` labels "central x (1 + high margin)" as P80. With the -20%/+30% band read as a triangle, +30% is the P100 end. Read as an AACE-style 80% interval, it is about P90. Either way "P80" is mislabelled. Use the label "high case (+30%)", or compute P80 explicitly.
- Combining the worst sale percentile with the worst cost end assumes perfect adverse correlation, and gives a downside about twice the Monte Carlo P10 ($266k against $123k). It is honest as a stress case but should be named that, not called "the range".
- The 52% swing from two 5% errors is the main reason to show a sale-by-cost sensitivity grid next to the residual. It fits rule 5 (show the numbers): users see how much the answer depends on inputs.
- Clapp et al. suggest residual land values for parcels with existing buildings near teardown may be biased low compared with market land prices, because option value is ignored. That supports comparing the residual against observed land and teardown sales (section 5).

### Gaps
- Could not open Coleman, Crosby, McAllister and Wyatt, "Development appraisal in practice: some evidence from the planning system", *Journal of Property Research* (about 2013) (citation UNVERIFIED), or other Reading viability papers with published sensitivity elasticities. Our computed figures stand in for them.
- No published Chicago or US small-builder distribution of cost overruns or sale-price errors found. Our own test set (median sale error 12%; 65% within 15%) is the best local evidence. The P25-P75 sale band should be refit from it.

## 3. How should finance costs be modeled for small projects (draw curve, rates, fees, timing, absorption)?

### Takeaway
The simple-average draw method (average balance x rate x months) is accepted practice. A straight line or a symmetric S-curve averages about 50% drawn; front-loading (land and site work funded early) pushes it above 50%. Our 55% is reasonable. The 8% rate sits inside 2026 bank construction pricing (SOFR 3.64% plus 275-400 bp, about 7.0-8.75%). Missing pieces: loan fees, interest on land during pre-permit time, and the circularity between finance and land.

### Cited Findings
- Simple-average method: interest reserve ≈ average % outstanding x commitment x rate x months / 12.
  - A straight-line or symmetric S-curve averages about 50%; front-loaded draws push it above 50%, back-loaded or equity-first funding pulls it below.
  - Their worked S-curve: cumulative 12%, 42%, 70%, 90%, 100% at months 6/12/18/24/30. It averaged 53%, so the 50% shortcut understated interest by about 5%.
  - Interest funded from the loan creates circularity; solve it iteratively.
  - Cost of a delay with the loan fully drawn = loan x rate x delay months / 12.
  - Loan size = lesser of LTC x cost, NOI / debt yield, and LTV x value.
  — [APERS, Construction loans, draw schedules and interest reserves](https://apers.app/learn/capital-structure/senior-debt/construction-loans-draw-schedules-interest-reserves)
- 2026 rates (article dated 28 July 2026):
  - SOFR about 3.64% (July 2026 30-day average); Fed target 3.50-3.75%.
  - Banks: SOFR + 275-400 bp, about 7.00-8.75% all-in, 60-65% LTC, full or partial recourse.
  - Debt funds: + 400-650 bp, about 8.75-10.25%, 65-85% LTC.
  - Multifamily construction average about 7.6% (Buildermuse, April 2026).
  — [CORE Advisors, Construction loan rates 2026](https://www.coradvisors.net/2026/05/construction-loan-rates-2026.html) (secondary aggregator; numbers trace to Commercial Lending Solutions, Multi-Housing News, Buildermuse)
- PPG lists "general finance costs including those incurred through loans" as a cost. — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- NAHB: financing was 1.5% of sales price for single-family builders in 2024. — [NAHB Eye on Housing](https://eyeonhousing.org/2025/01/cost-of-constructing-a-home-in-2024/)
- Repo evidence:
  - Permit processing medians: 50 days self-certification, 85 days standard review (P25-P75 8-100 and 56-161). — feasibility_defaults.json `permit_duration`, from Chicago permits ydr8-5enu
  - Median permit-to-sale is 18 months on the 35-building test set. — v1-spec.md
- Origination fees: no public 2026 source read. Practitioner norms of 0.5-1.0% for bank construction loans, and 1-3 points for private lenders, are UNVERIFIED.

### Inferences
- Our 12 build + 6 sell = 18 months matches the measured permit-to-sale median, but it starts at permit issue. Land is held from closing through design and permit review, which takes 1.7-2.8 months at the median and up to 5.4 months at standard-review P75. The spec computes that carry in `permit_duration.use` but never adds it to the finance formula.
- The sell term charges interest on the full 65% loan for 6 months. That fits a whole-building sale of a 2-4 flat at completion. For condo sales, each closing pays the loan down, so average balance in the sell period is nearer 50%. The 6-month figure should come from measured completion-to-sale data (our test set has permit, completion if available, and sale dates).
- At 8% and 65% LTC, finance is 5.5% of cost before financing, plus 2.25% tax and insurance. NAHB's 1.5% of price is lower because production builders turn faster and use more equity. For a small Chicago builder, our figure is the more conservative.
- Computed sensitivity: a 6-month delay on the HP 3-flat (cost before financing $906,906, so loan $589,489 fully drawn) costs about $23,600 of interest plus $6,800 of tax and insurance. Time belongs in the sensitivity grid.

### Gaps
- No Chicago-specific small-builder construction loan survey found. Community banks and CDFIs (for example, the Chicago Community Loan Fund) may price differently; not checked.
- No public data on completion-to-sale (absorption) time for Chicago 2-6 unit new construction; it could be measured from our own permit and sale data.

## 4. How should the hold (rental) scenario be valued (cap rate, yield on cost, DSCR, expense ratio, Chicago figures)?

### Takeaway
Chicago multifamily cap rates averaged 5.5-6.0% (Northmarq) to 6.7% (Matthews) in 2025. Our 6.25% sits inside that range, but those figures cover all multifamily, not 2-6 unit buildings. Property tax is the biggest Chicago-specific risk to the hold math. The Cook County Assessor puts taxes inside the expense ratio and uses unloaded cap rates. A "loaded" cap rate (cap rate + effective tax rate) is the correct way to avoid a circular reference when taxes depend on value. Our flat 35% expense ratio (operating factor 0.65) probably understates expenses for new Chicago buildings once taxes are reassessed at new-construction value.

### Cited Findings
- Northmarq Chicago Q4 2025:
  - "Cap rates averaged between 5.5% and 6.0% in 2025", unchanged from 2024 and 25-50 bp above 2023.
  - Median $245,200 per unit.
  - Vacancy 5.2% citywide (Class A 7.2%, B/C 3.7%).
  - Asking rent $1,997 (+0.7% year over year); B/C $1,509.
  — [Northmarq Chicago Q4 2025 PDF](https://www.northmarq.com/sites/default/files/docs/NMMarketInsights-Q42025-Chicago.pdf)
- Matthews Chicago Q4 2025 (published 22 Jan 2026): average cap rate 6.7%, average $228,000 per unit, about $1.9B volume in 2025, vacancy 5.0%. No split by building size. — [Matthews](https://www.matthews.com/market_insights/chicago-il-multifamily-market-report-q4-2025)
- The two broker sources disagree by 70-120 bp. Both are broad market figures, not 2-6 unit figures.
- Cook County Assessor cap rate policy:
  - Sources are CBRE, JLL, Cushman & Wakefield, PwC and RERC surveys, comparable sales and band of investment.
  - The Assessor uses unloaded overall rates and "does not load the overall cap rate in any scenario". First-pass values apply "prevailing expense ratios that include property taxes".
  - A loaded rate adds an effective tax rate built from the equalizer, the assessment level and the prior tax rate.
  — [CCAO Cap Rate Policy, 24 Apr 2023](https://prodassets.cookcountyassessoril.gov/s3fs-public/event/Assessor%20Cap%20Rate%20Policy%20(FINAL)%204.24.2023.pdf)
- CCAO township reports:
  - The Chicago property tax rate is built into multifamily operating expense ratios, so cap rates are unloaded.
  - The multifamily level of assessment is 10%, against 25% for commercial.
  - Per-property vacancy, expense and cap figures sit in the township Excel worksheets (for example, Rogers Park 2024), not in the narratives.
  — [CCAO Rogers Park 2024](https://www.cookcountyassessoril.gov/rogers-park-2024-commercial); [worksheet xlsx](https://prodassets.cookcountyassessoril.gov/s3fs-public/reports/2024/2024.T75.PublicModel%20TJS_RPSC.xlsx) (not opened)
- Civic Federation: Chicago's effective tax rate on a median-value homestead was 1.52% (tax year 2022), against a 53-city average of 1.32%. Commercial was 4.01%. — [Civic Federation](https://civicfed.org/node/4141)
- Terner Center *Making It Pencil* (Dec 2023) reference tests already in our defaults: yield on cost at least 1.0 point over the cap rate, DSCR 1.3, LTC 55-65%. — [Terner Center PDF](https://ternercenter.berkeley.edu/wp-content/uploads/2023/12/Making-It-Pencil-December-2023.pdf) (in repo; not re-read)
- RealPage/NCREIF: average multifamily expense ratio 0.43 over 10 years to 2016. Large properties (150+ units) ran up to 58 bp lower than small. That figure includes non-operating costs such as interest, so it is not a clean opex ratio. — [RealPage, 2016](https://www.realpage.com/analytics/size-matters-investigating-operating-expenses-across-multifamily-product/)
- Cook County class 211/212 (2-6 unit apartments) are valued by the residential mass-appraisal (sales) model, not the commercial income model. The income-approach cap rates and expense ratios apply to class 3 (7+ units) and mixed-use (UNVERIFIED; consistent with the Rogers Park report covering "multifamily" as 7+ income property).

### Inferences
- Taxes as a share of NOI: at an effective rate t on value V = NOI / cap, taxes = t / cap of NOI. At t = 1.52% and cap 6.25%, that is 24% of NOI, or 15.8% of effective gross income with our 0.65 factor. At t = 2.0% (plausible for a non-homestead rental), it is 32% of NOI, or 20.8% of EGI. That leaves only 14-19% of EGI for insurance, repairs, management, water, reserves and common utilities, which looks thin. Our 0.65 factor likely overstates NOI on new buildings.
- Correct structure, mirroring the CCAO's loaded-rate idea: NOI before tax = EGI - non-tax opex, and value = NOI before tax / (cap + t). This removes the circular reference and makes tax a visible line with its source (effective rate from the Cook County tax rate, equalizer and 10% assessment level).
- For 2-4 unit hold scenarios, the end buyer is often an owner-occupant priced on comps, not a cap-rate investor. Showing both the comp-based value and the income value is more honest than income value alone.
- DSCR loan sizing for hold: max loan = NOI / (DSCR x mortgage constant). At 6.5% on 30-year amortization the constant is about 7.58%, so DSCR 1.25 gives a loan of 10.55 x NOI. Show it against the construction loan to flag a refinance shortfall. This is arithmetic; the rate is illustrative.

### Gaps
- No public 2025-2026 cap rate split for Chicago 2-4 units or 5-49 units read. The Arbor *Small Multifamily Investment Trends* report (5-49 units) exists ([Arbor Q3 2025 PDF](https://arbor.com/wp-content/uploads/2025/08/Arbor_Small-Multifamily-Investment-Trends-Report_2025_Q3.pdf)), but the fetch budget ran out before reading it.
- Freddie Mac small balance underwriting: minimum DSCR (commonly 1.20-1.30) and expense floors not verified this session.
- CCAO township worksheets with actual Chicago multifamily expense ratios and cap rates not opened. They are the best public local source and should be pulled into data/reference/.
- Non-homestead effective tax rate for new Chicago 2-6 unit buildings not found; it needs computing from CCAO assessed values and Clerk tax rates.

## 5. Should residual land value be compared with existing-use value, and how is the teardown decision modeled?

### Takeaway
Yes. UK policy uses existing-use value plus a premium as the threshold a residual must clear for a site to come forward. Chicago research shows teardown sale prices approximate land value, and teardowns cluster on small, older homes near transit and village centers. Our existing-use check (residual vs Assessor market value) follows the literature. A landowner premium and a check against observed teardown sale prices would make it closer to practice.

### Cited Findings
- PPG: benchmark land value = EUV + premium (EUV+); the premium is the minimum return at which a reasonable landowner would sell; EUV excludes hope value. — [GOV.UK PPG Viability](https://www.gov.uk/guidance/viability)
- Dye and McMillen (2007), "Teardowns and land values in the Chicago metropolitan area", *Journal of Urban Economics* 61(1): 45-63, DOI 10.1016/j.jue.2006.06.003. Teardown sale price is "approximately equal to its land value". Prime teardown candidates are small, older homes near public transit and traditional village centers. The model corrects for selection and misclassification. — [University of Illinois Experts](https://experts.illinois.edu/en/publications/teardowns-and-land-values-in-the-chicago-metropolitan-area/)
- McMillen and Singh, "Land Value Estimation using Teardowns" (slides, Lincoln Institute): 32,682 Chicago single-family sales 1995-2016 in six North Side community areas (Lakeview, Lincoln Park, Lincoln Square, Logan Square, North Center, West Town). There were 3,753 demolitions, 1,563 within 2 years of sale, and 97 vacant land sales. Methods: a Stein-rule blend of models with and without structure variables, and an unconditional-expectations model with selection correction (a duration model of time to demolition in Chicago). — [Lincoln Institute PDF](https://www.lincolninst.edu/app/uploads/2024/04/singh_and_mcmillen_land_value_estimation_using_teardowns.pdf)
- Clapp, Cohen and Lindenthal (2023): the residual ignores the option to redevelop. In their model, true land share near teardown is 0.8 against 0.57 from the residual. — [Springer](https://link.springer.com/article/10.1007/s11146-021-09834-4)
- Same paper, citing Munneke and Womack: only about 38% of Miami sales (1999-2002) had any redevelopment option value. — [Springer](https://link.springer.com/article/10.1007/s11146-021-09834-4)

### Inferences
- For a parcel with a building, the owner's floor is the higher of (a) existing-use value, from Assessor market value or comps of existing 2-flats with the same unit count, and (b) observed teardown and land prices nearby. Comparing the residual to (a) alone will miss areas where land already trades above existing-use value because others will redevelop.
- Show the existing-use check as two numbers with sources: "Assessor market value $X (tax year Y)" and "nearby teardown and vacant sales median $Z/sf (n sales, date range)". The gap to the residual is shown as dollars, with no verdict.
- A premium over existing-use value is a UK policy construct with no US standard. If shown at all, it should be a user-set field, default 0%, labelled as an assumption.
- Assessor market value for class 2 = assessed value / 10%. The Assessor's level of accuracy varies. CCAO publishes sales-ratio studies; their median ratio by township should set the margin on this number (not checked this session).

### Gaps
- Full Dye and McMillen text not read. Teardown price relative to vacant land price per square foot was not extracted.
- No Chicago study of 2-flat/3-flat teardowns specifically (the papers cover single-family) was found.

## 6. What does the evidence say about Chicago land values, and how should land value per sq ft be estimated from vacant and teardown sales?

### Takeaway
Three public bodies of evidence exist:
- FHFA tract and ZIP land price estimates (appraisal-based cost approach, 2012-2019 data plus 2024 index updates).
- Academic land value work on Chicago (McMillen; Ahlfeldt and McMillen; Albouy, Ehrlich and Shin for metro-wide values).
- Teardown-sale methods that treat teardown prices as land prices with selection correction.
Our land value map (vacant plus teardown sales, 36 months, by Assessor neighborhood) follows the teardown literature. FHFA tract estimates make a free, citable fallback and cross-check.

### Cited Findings
- Larson, Shui, Davis and Oliner, FHFA Working Paper 19-01, "The Price of Residential Land for Counties, ZIP codes, and Census Tracts in the United States" (2019, updated 2020). Uses millions of appraisals 2012-2019 to estimate land prices and land share of house value down to tract level. Downloads: [Land Prices June 2024 xlsx](https://www.fhfa.gov/document/land-prices_2024_20_june.xlsx), [Oct 2020 xlsx](https://www.fhfa.gov/sites/default/files/Land-Prices_DLOS_2020_26Oct.xlsx), [FAQ](https://www.fhfa.gov/document/faqs-land-10-28-20.pdf). FHFA calls these "works in progress". — [FHFA WP 19-01](https://fhfa.gov/research/papers/wp1901)
- Dye and McMillen (2007): teardown price ≈ land value. — [Illinois Experts](https://experts.illinois.edu/en/publications/teardowns-and-land-values-in-the-chicago-metropolitan-area/)
- McMillen and Singh: the teardown estimator for Chicago puts about 43% weight on the unrestricted model. The log land-area coefficient is 0.858, meaning price rises less than one-for-one with lot size. Distance to Lake Michigan has a significant negative coefficient (-0.124). — [Lincoln Institute PDF](https://www.lincolninst.edu/app/uploads/2024/04/singh_and_mcmillen_land_value_estimation_using_teardowns.pdf)
- Albouy, Ehrlich and Shin (2018), "Metropolitan Land Values", *Review of Economics and Statistics* 100(3): 454-466. Uses vacant land sales to estimate metro land values. — [IDEAS/RePEc](https://ideas.repec.org/a/tpr/restat/v100y2018i3p454-466.html) (citation from the URL; abstract not read)
- McMillen, Chicago land values 1913-2010 (Lincoln Institute article). — [Lincoln Institute](https://www.lincolninst.edu/es/publications/articles/land-values-chicago-1913-2010/) (not opened)
- Clapp et al. (2023): vacant-land indices swing less than residual-based indices (trough-to-peak about 2.5 against 3.0). — [Springer](https://link.springer.com/article/10.1007/s11146-021-09834-4)

### Inferences
- A land-area coefficient below 1 (0.858) means price per sq ft of lot falls as lots get larger. A neighborhood median $/sf from mixed lot sizes will overprice large lots and underprice small ones. Price per buildable sq ft (already in the spec) partly corrects this. A simple log-log fit of price on lot area within each neighborhood would correct it further.
- Teardown sales of single-family homes may carry a premium or discount compared with vacant lots, through demolition cost, environmental unknowns and the option already exercised. Report vacant and teardown medians separately with counts before pooling them.
- Use the FHFA tract land price as a third fallback (after Assessor neighborhood and community area), with its vintage shown. It is public domain and fits rule 2 (source and date).

### Gaps
- FHFA Chicago tract values not extracted. The spreadsheet needs downloading into data/reference/.
- Ahlfeldt and McMillen land value series for Chicago (Olcott's data) not reviewed.
- Albouy et al. Chicago figures not read.

## 7. How should incentives enter the pro forma (timing, present value, sell vs hold)?

### Takeaway
Incentives differ in who gets them, when cash arrives, and whether they survive a sale. In a correct pro forma, each one enters as:
- a cost reduction at the time it is incurred (sales-tax exemption),
- revenue or a reimbursement at the date paid (Missing Middle grant, TIF notes),
- an annual operating saving capitalized only in hold or sale value (property tax classes), or
- an investor-level tax benefit kept apart from project profit (OZ, depreciation, historic credits).
Several V1 programs don't apply to 2-6 unit buildings at all: AHSAP needs 7+ units, and the ARO triggers at 10+.

### Cited Findings
- Cook County Affordable Housing Special Assessment Program (AHSAP):
  - Eligibility: 7 or more units (or part of a qualifying development).
  - Tier 15 (15-34% of units at 60% AMI or below) cuts AV by 25%. Tier 35 (35%+) cuts it by 35%.
  - Term: 10 years with two 10-year renewals.
  - Rehab spend thresholds for 2026: $8.16/sf for Tier 15, $12.75/sf for Tier 35, $61.20/sf for LAC.
  — [CCAO Affordable Housing](https://www.cookcountyassessoril.gov/affordable-housing)
- Chicago ARO covers developments of "10 or more units" that need a Council-approved zoning change, a city land transaction or financial assistance (2021 ARO for approvals after 1 Oct 2021). — [City of Chicago ARO](https://chicago.gov/city/en/depts/doh/provdrs/developers/svcs/aro.html)
- Missing Middle Infill Housing Initiative, April 2025 guide:
  - Lots sell for $1. Eligible types: single-family with ADU, townhomes, 2-flats, 3-flats, 6-flats.
  - Developers may request $50,000-$150,000 per unit, capped at $5M per team.
  - The grant is paid as reimbursement: 50% after half the cluster's buildings are complete, 100% after the rest.
  - Sale prices must be affordable at 140% AMI; buyers must be owner-occupants. ARO units apply at 10+ units.
  — [Missing Middle Program Guide, April 2025](https://chicago.gov/content/dam/city/sites/land-sales/2025/Missing_Middle_Program_Guide_April2025_FINAL.pdf)
- Opportunity Zones under the One Big Beautiful Bill Act (OBBBA):
  - Made permanent. Investments under the old rules allowed through 31 Dec 2026.
  - Rolling redesignations start 1 July 2026, with new-zone investments from 1 Jan 2027. Deferred gains are recognized on a rolling 5-year schedule.
  - After 10 years, basis can step up to fair market value.
  - The bill also restores 100% bonus depreciation for property placed in service after 19 Jan 2025. Buildings don't qualify, but cost segregation can move components into 5-, 7- and 15-year classes.
  — [BNN CPAs on OBBBA](https://www.bnncpa.com/resources/qualified-opportunity-zone-enhancements-and-expansion-under-the-one-big-beautiful-bill-act-obbba/) (secondary; the statute was not read)
- Cook County Class 7/8 commercial incentives: 10% assessment level for 10 years (with a step-up in years 11-12 under the ordinance) against 25% commercial. Needs a municipal resolution (UNVERIFIED in this session; current CSV says 10% for 10 years).
- Federal historic tax credit: 20% of qualified rehabilitation expenditures, claimed ratably over 5 years since the 2017 tax act, with recapture on early sale. Rehab of certified historic structures only, so it does not apply to V1 new construction (UNVERIFIED in this session; from general knowledge).
- Chicago commercial effective tax rate is 4.01%, against 1.52% for residential homesteads (tax year 2022). This is why Class 7/8 matters for mixed-use ground floors. — [Civic Federation](https://civicfed.org/node/4141)

### Inferences
- Missing Middle: the grant arrives at completion, so it does not reduce construction interest. Enter it as a receipt at completion: it reduces the loan payoff, and its present value is discounted by the build period. The 140% AMI price cap must also replace the comp-based sale value. Showing "$150,000/unit" as an add-on to a comp-priced sale would overstate profit. The $1 land price replaces the land line. The program's net effect = grant + land saving - (comp price - capped price) x units.
- Opportunity Zone, sell scenario: the 10-year exclusion belongs to the QOF investor's gain, not to project profit. $0 for sell is right. For hold, the 23.8% x appreciation is a year-10 amount and should show as a present value at a user-set discount rate, with the year stated. The spec's "2018 list valid through 2028" needs restating against OBBBA dates (new investments in old zones end 31 Dec 2026; new zones from 1 Jan 2027).
- Bonus depreciation is a deferral. Its value is the PV of tax shifted forward, minus the PV of recapture at sale and of the depreciation given up in later years. "25% of hard cost x 37%" is the undiscounted first-year deferral. That meets rule 6 (maximum value) but should be labeled "first-year tax deferred, not profit", with a PV line. It applies only to hold scenarios and to owners who can use the losses (passive-loss limits).
- Enterprise Zone sales-tax exemption: a direct hard-cost reduction during construction (10.25% x materials share). It applies in both sell and hold. It should reduce cost before financing, so it also cuts finance cost.
- Property tax classes (Class 7/8, AHSAP): annual savings during operation. They count in hold value as part of NOI, and in sell scenarios only through a buyer's capitalized price. A 2-6 unit residential building gets nothing from AHSAP (7+ units required).
- TIF and SBIF: reimbursement after completion, so treat them like the Missing Middle grant (receipt at a date, then PV). Flag-only in V1 is reasonable.

### Gaps
- Chicago-specific Class 7/8 terms and current Cook ordinance text were not re-verified.
- No public Chicago data found on how often TIF assistance goes to projects under 10 units.
- The IL state historic tax credit program terms were not checked.

## 8. What should change in our formulas, default targets, finance modeling and uncertainty display?

### Takeaway
Keep the residual structure. Fix the finance-land circularity, add the missing pre-permit land carry and loan fees, and make property tax explicit in the hold scenario. Show return against a reference band of 15-25% on cost (with on-GDV beside it) rather than one 15% line. Replace the "P80 = +30%" label with a computed or honestly named high case. Add a sale-by-cost sensitivity grid.

### Cited Findings
- Benchmarks for return: [PPG para 019](https://www.gov.uk/guidance/viability) (15-20% of GDV); [RICS Land Journal 2020](https://ww3.rics.org/uk/en/journals/land-journal/approaches-to-developer-returns-in-appraisals.html) (20% on cost for low risk, 25% for higher risk); [NAHB](https://eyeonhousing.org/2025/01/cost-of-constructing-a-home-in-2024/) (11.0% profit of price); [NAHB CODB](https://www.nahb.org/news-and-economics/press-releases/2025/04/nahbs-new-study-provides-statistics-and-data-on-builder-financial-performance) (20.7% gross margin, 8.7% net).
- Finance: [APERS](https://apers.app/learn/capital-structure/senior-debt/construction-loans-draw-schedules-interest-reserves) (simple-average method; S-curve averages about 50-53%; circularity); [CORE Advisors 2026](https://www.coradvisors.net/2026/05/construction-loan-rates-2026.html) (bank 7.0-8.75%).
- Hold: [CCAO cap rate policy](https://prodassets.cookcountyassessoril.gov/s3fs-public/event/Assessor%20Cap%20Rate%20Policy%20(FINAL)%204.24.2023.pdf) (loaded rate = cap + effective tax rate); [Northmarq](https://www.northmarq.com/sites/default/files/docs/NMMarketInsights-Q42025-Chicago.pdf) and [Matthews](https://www.matthews.com/market_insights/chicago-il-multifamily-market-report-q4-2025) (5.5-6.7% caps); [Civic Federation](https://civicfed.org/node/4141) (1.52% effective residential rate).
- Uncertainty: [Evans 1992](https://www.emerald.com/insight/content/doi/10.1108/09588689210033846/full/html); [Homes England](https://www.gov.uk/government/publications/optimism-bias-and-contingency-at-homes-england/optimism-bias-and-contingency-at-homes-england-accessible-version); computed results in section 2.

### Inferences (recommendations)
**Formulas**
1. Max land price (residual). Replace with **L = net sale / ((1 + r) x (1 + f)) - C0**, where C0 = hard + sprinklers + contingency + soft + permit + fees, and f = LTC x rate x (build months / 12 x average drawn + sell months / 12) + tax-and-insurance rate x (build + sell months) / 12. The current spec understates the residual by $15,800 on the standard 3-flat. Keep the name "residual land value".
2. Add pre-construction land carry: land x (rate x LTC_land + tax rate) x (design months + permit days / 30) / 12. Default permit days come from `permit_duration` by review path (50 or 85). Design months are a user field, default about 2 (UNVERIFIED placeholder). This puts our measured permit wait into the money.
3. Add loan fees: origination fee % x loan, default 1.0% (UNVERIFIED; source needed before launch). Fold it into f.
4. Sell-period interest: whole-building sale keeps a 100% balance for the sell months. Condo sale uses about 50% (straight-line paydown). Set it by scenario type.
5. Hold value: compute NOI before tax = rent x 12 x units x (1 - vacancy) - non-tax opex. Value = NOI before tax / (cap + effective tax rate). Show tax as its own line: effective rate from the Cook equalizer x 10% assessment level x Chicago composite rate, with source and tax year. Default vacancy is 5% (Northmarq 5.2%; Matthews 5.0%). The non-tax opex default should come from CCAO township worksheets once pulled. Until then keep the total at about 35-45% of EGI and flag it as a placeholder.
6. Hold: add DSCR-based permanent loan = NOI / (DSCR x mortgage constant), shown against the construction loan payoff as a refinance gap in dollars. DSCR 1.25-1.30 is a reference line (Terner uses 1.3).
7. For 2-4 unit hold scenarios, show the comp-based sale value beside the income value, since the likely buyer is an owner-occupant.

**Default targets (reference lines, not verdicts)**
8. Show return on cost against a band of 15% / 20% / 25% on cost, each with its source (Feasly/NAHB low end; RICS 20% low-risk; RICS 25% higher-risk). Show margin on net sale beside it (13.0% / 16.7% / 20.0%), with the PPG 15-20% of GDV line. The residual uses the user's chosen target; default 20% on cost for unpermitted sites is the RICS figure. Changing 15% to 20% lowers the stylized residual by $50,457 (computed). Marlon to decide (see open questions).
9. Development score: the profit part saturates at 25% return on cost. That is consistent with the top of the band.

**Finance modeling**
10. Keep the simple-average method with 55% average drawn (APERS: 50-53% for an S-curve; 55% is reasonable for front-loaded land and site work). Set the rate from a dated source: SOFR + spread, default bank 8.0% (inside 7.0-8.75%). Store `verified_on` and refresh it monthly from FRED SOFR plus a stored spread.
11. Months: keep 12 build + 6 sell as defaults matching the 18-month permit-to-sale median. Refit build and sell months separately from our own permit, completion and sale data, and show P25-P75 months.

**Uncertainty display**
12. Rename the "+30%" cost to "high case (+30%)" or compute it. Under a triangular (-20%, 0, +30%) cost, P50 is +2.6% and P80 is +12.5% (computed). Showing "P80" at +30% contradicts the Homes England meaning of the term.
13. Label the current worst corner (low sale, high cost) "stress case". Add a Monte Carlo summary (10,000 draws are enough): sale from the comp distribution (P25-P75 fit to lognormal), cost triangular on the stage margins, months triangular from the permit and sale data. Show profit and residual at P10/P50/P80/P90 and the share of draws with a loss, all in dollars. In the stylized case, the P10 loss is -$122,632 against a -$265,650 corner. Fix the random seed so results are reproducible.
14. Add a 5x5 sensitivity grid next to the residual: sale value -10/-5/0/+5/+10% by cost -10/-5/0/+10/+20%, cells in dollars. Add one row for the target return (15/20/25%) and one for a 6-month delay.
15. Existing-use check: show Assessor market value and the nearby teardown and vacant sale median (count and dates) beside the residual, with the dollar gap. Add an optional landowner premium field defaulting to 0%.

**Incentives**
16. Model timing:
    - Enterprise Zone: reduce hard cost, which flows into finance.
    - Missing Middle: grant as a receipt at completion. Replace comp sale value with the 140% AMI price cap. Land at $1.
    - Opportunity Zone (hold): PV of the year-10 exclusion at a user discount rate. Restate dates per OBBBA.
    - Bonus depreciation: show undiscounted first-year deferral (maximum value) and its PV, outside profit.
    - Remove AHSAP/Class 9 from any 2-6 unit scenario (7+ units required). Keep ARO off below 10 units.

### Gaps
- Origination fee and design-months defaults need sources before launch.
- Chicago 2-6 unit cap rates, non-homestead tax rate and opex ratios need pulling from CCAO worksheets and Arbor/Freddie small-balance reports. The fetch budget ran out in this session.
- The sale-value distribution for Monte Carlo should be fit from our 35-building test set errors, not assumed.

Open questions for Marlon:
- Default target: keep 15% on cost, or move to 20% (the RICS low-risk figure) with 15% and 25% shown as reference lines?
- Should the hold scenario carry a separate property tax line at a non-homestead effective rate, replacing part of the 0.65 operating factor?
- Is a Monte Carlo summary acceptable in V1, or should V1 ship only the sensitivity grid and stress case?
- Which lender is the partner contractor using, and at what rate and fee? That would replace the 8% and the unsourced fee default.
