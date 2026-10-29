# Practices adopted from other countries

Researched 2026-10-29. Each practice is adopted as a product mechanic; none of them changes Chicago law. The live table is in the review doc (https://claude.ai/artifact/BbGMmUHCyGKz2KPs4g4xjf).

| Country | What they do | What 25x125 adopts | When | Rules file |
| --- | --- | --- | --- | --- |
| Germany | Valuation committees publish official standard land values (Bodenrichtwerte) by zone from recorded sales, free through the BORIS portals | Land value map by Assessor neighborhood, with sale count and date | V1 step 3 | `feasibility_defaults.json` `land_value_map` |
| Singapore | Land sale results published per sq ft of permitted floor area | Land price per buildable sq ft beside price per lot | V1 step 3 | same |
| UK | Residual valuation: value minus costs and profit equals land value, checked against existing-use value plus a premium | Residual land value naming, profit as percent of value and of cost, existing-use check on parcels with buildings | V1 step 4 | `residual` |
| UK (Homes England) | Reference class forecasting with P50 and P80 cost uplifts; 10% contingency gave a 35% chance of hitting budget in their worked example | Cost shown at P50 and P80; margins refit from actual job costs | V1 labels; refit Phase 4 | `cost_confidence` |
| UK (BCIS) | Location cost indices with recent quarters weighted 1.00, 0.75, 0.56; thin districts tied to their region | Recency-weighted permit index; thin areas blended with their side of the city | V1 step 3 | `cost_index_method` |
| Canada (BC), Australia (NSW), Germany | Standard design catalogs: BC multiplex designs, NSW Pattern Book (10-day approvals), GdW's nine fixed-price model buildings at EUR 2,000-3,200 per sq m for five years | Chicago pattern library sized for 25 x 125 lots; scenarios pick a pattern; permit-ready plan sets with partner architects later | V1 data; plans Phase 2 | `building_patterns.json` |
| Netherlands, UK | Machine-readable rules with question trees; national planning data platform (73 of 311 authorities feeding it) | One rule schema with location, effective dates and citation; incentive toggles as eligibility questions | V1 steps 2 and 4 | `incentive_questions.json` |
| Japan, NSW, Singapore | By-right building under 12 national zones; complying development in as little as 20 days vs 70; Singapore's 7 agencies at 4 gateways with one consolidated comment set | Fast-path filter and badge; entitlement tracker built as gateways with consolidated comments | V1 filter; Phase 2a | `fast_path` |
| New Zealand | Auckland's 2016 upzoning added about 11,044 permits by 2021, mostly attached homes | Policy mode: rerun all parcels under a proposed ordinance | After V1.1 | none yet |

## Sources

- [BORIS-D, Berlin valuation committee](https://www.berlin.de/gutachterausschuss/service/glossar/artikel.789821.php)
- [Britain publishes what homes sold for, Singapore publishes what the land cost](https://www.uktech.news/other_news/britain-publishes-what-homes-sold-for-singapore-publishes-what-the-land-cost)
- [UK financial viability for housing-led projects](https://www.gov.uk/guidance/financial-viability-for-housing-led-projects)
- [Optimism bias and contingency at Homes England](https://www.gov.uk/government/publications/optimism-bias-and-contingency-at-homes-england/optimism-bias-and-contingency-at-homes-england-accessible-version)
- [BCIS location indices](https://www.pbctoday.co.uk/news/planning-construction-news/bcis-location-indices-changes-and-challenges/37922/)
- [BC standardized housing designs](https://globalnews.ca/news/10732766/standardized-housing-designs-b-c)
- [NSW complying development](https://planning.nsw.gov.au/the-planning-system/development-assessment/planning-approval-pathways/complying-development)
- [GdW serial construction framework agreement](https://vergabeblog.de/2018-05-30/serielles-bauen-europaweiter-wettbewerb-liefert-zukunftsweisende-konzepte-fuer-schnellen-kostenguenstigen-wohnungsbau-in-hoher-qualitaet/)
- [Dutch applicable rules (toepasbare regels)](https://iplo.nl/digitaal-stelsel/toepasbare-regels-maken-aanleveren/toepasbare-regels-aanleveren-omgevingsloket/)
- [How does Tokyo build so much housing?](https://morehousing.substack.com/p/tokyo)
- [Singapore CORENET X approval process](https://www1.bca.gov.sg/regulatory-info/building-control/corenet-x/corenet-x-faq/new-regulatory-approval-process)
- [The impact of upzoning on housing construction in Auckland](https://www.eresearch.auckland.ac.nz/project/the-impact-of-upzoing-on-housing-construction-in-auckland/)

# Round 2: other countries, states and bodies

Researched 2026-10-29, after the first nine. This round looks wider: other US states and cities, research groups, lenders, and federal data. Each item says whether it changes V1 or goes on the roadmap, and what it changes.

## Changes to V1

| # | Who | What they do or publish | What 25x125 does with it | Where |
| --- | --- | --- | --- | --- |
| 1 | NSW and Singapore (timing), City of Chicago permit data | NSW publishes approval days by pathway (about 20 vs 70). Chicago's permit dataset `ydr8-5enu` has `processing_time` and `review_type` for each permit | Permit wait comes from the city's own data by review path and adds land carry. For the 836 permits behind the cost index: self-certification median 50 days (25th-75th: 8-100), standard plan review 85 days (56-161) | `feasibility_defaults.json` `permit_duration`; step 3 |
| 2 | Terner Center (UC Berkeley), "Making It Pencil" 2023 | Hold test: return on cost at least 1.0 point over the cap rate; lenders size to DSCR 1.3; loan-to-cost fell from 65% (2019) to about 55% (2023) | Hold results show the spread over cap rate, DSCR and the loan a lender would size. These show as reference lines, not as a verdict | `hold.reference_tests`; step 4 |
| 3 | Australian and UK feasibility practice (ARGUS EstateMaster, RICS) | Lenders look at development margin on cost, typically 15-20% for small residential; also margin on revenue | Sell results show margin on cost and margin on revenue, with the 15-20% band as a reference line | `sell.reference_margin_on_cost`; step 4 |
| 4 | Fannie Mae, FHA (HUD) | Owner-occupant loans for 2-4 units: Fannie Mae 5% down since November 2025; FHA 3.5% down. 2026 FHA limits in Cook County: $693,050 (2 units), $837,700 (3), $1,041,125 (4). Five or more units go to commercial lending and commercial appraisal (Spokane builders name this as the main financing cliff) | Each scenario shows its buyer financing class (owner-occupant residential vs commercial) and whether the sale price sits under the FHA limit. A 4-flat and a 5-flat look very different to a buyer | `sell.buyer_financing`; step 4 |
| 5 | FHFA House Price Index | Free annual house price index by census tract and ZIP, public domain, can be shown on screen (unlike Zillow) | Time adjustment of comps uses the FHFA index for the comp's tract or ZIP, falling back to the Chicago metro quarterly index | `sale_comps.time_adjustment`; step 3 |
| 6 | US Bureau of Labor Statistics (via FRED) | Monthly producer price index for net inputs to residential construction (`WPUIP2311001`, 355.2 in September 2026) | Cost presets carry a base month and move with this index monthly, the way BCIS indexes move UK costs. The screen shows the base month and the change | `build_spec_presets.escalation`; step 3 |
| 7 | City of Chicago Open Space Impact Fee | Fee per new dwelling unit, $313 to $1,253 by community area | Added as its own cost line by community area. The fee table needs the current worksheet from the city | `open_space_impact_fee`; step 4 |
| 8 | City of Chicago ChiBlockBuilder and Missing Middle | Over 600 city lots opened April 1, 2026, priced about $5,000 to $1 million; 30 Missing Middle lots in South Chicago and West Englewood in clusters of 5-8, with up to $150,000 per unit construction help and owner-occupant buyers required | City lots for sale show as a map layer with asking price and the program's terms. The Missing Middle incentive row already exists; its parcel test now reads the current round's lots | step 6 layer; `incentives_v1.csv` |
| 9 | City of Chicago ADU ordinance | Coach houses and basement units became permanent citywide on April 1, 2026; alderpeople can still block areas; the city publishes an ADU eligibility map | The ADU path reads the city's eligibility map instead of a list of opted-in wards. This replaces the "ADU areas" layer that was missing from the data portals | `v1-spec.md` step 5; `datasets.csv` |
| 10 | Pending rules: Chicago single-stair ordinance, Illinois BUILD | Chicago O2025-0017571 (single stair in apartment buildings; hearing June 4, 2026, no vote). Pritzker's BUILD plan (lot size, density, parking) stalled in June 2026 and will come back. NYC, Seattle, Honolulu and Tennessee already allow single-stair buildings of 4-6 stories; estimated savings 6-13% | Pending rules sit in a data file with status and expected effect, so they can switch on as a data edit if passed. The pattern library marks which patterns a single-stair rule would change (4+ stories on a 25-ft lot) | `pending_rules.json` |

## Roadmap

| Who | What they do | Use later | When |
| --- | --- | --- | --- |
| Canada (Housing Design Catalogue, March 2025) | About 50 free designs (rowhouses, fourplexes, sixplexes, ADUs) with a construction cost summary for each design in each region | Model for the pattern library's plan sets: a cost sheet per pattern per side of the city | Phase 2, with the plan sets |
| Washington State (Commerce permit-ready plans), Spokane | 150+ pre-approved plans across 18 jurisdictions with a public dashboard. Spokane allowed 4 units per lot in 2022 and 6 near transit in 2023; middle housing rose from 3-4% of permitted units (2020-22) to 17% in 2025 | Pattern library adoption tracking; evidence when talking to aldermen and the city about pre-approved plans | Phase 2 |
| ICC and Archistar | Automated plan checks against the building code, used by Los Angeles and Austin | Partner or reference for the layout planner's code check | Phase 2 |
| Japan and Korea (land readjustment) | Owners pool small lots, re-plot them and share the gain | Assembly finder: adjacent vacant or city-owned lots, and lots under one taxpayer name, flagged as combinable | V1.1 |
| Houston (lot size reform, 1998 and 2013) | Minimum lot size cut to 1,400 sq ft, producing tens of thousands of fee-simple townhomes | Scenario for selling as fee-simple townhomes where zoning allows, beside condo sale | V1.1 |
| FHFA Uniform Appraisal Dataset | Quarterly appraisal statistics by census tract for single-family | Appraisal-gap check: whether an area's appraisals support the estimated sale | V1.1 |
| Michigan (MSHDA Missing Middle program) | Cost-gap grants paid to developers for moderate-income housing | Template for Illinois incentive rows when IHDA or the city starts similar programs | When one exists |
| Modular and panelized builders (BoKlok in Sweden and the UK; Katerra's 2021 failure in the US) | Factory-built flats at fixed prices; Katerra shows the risk of tying to one supplier | Cost preset for panelized wood frame once a local supplier quotes | Phase 4 |

## Sources for round 2

- [Chicago building permits dataset (ydr8-5enu)](https://data.cityofchicago.org/resource/ydr8-5enu.json), queried 2026-10-29
- [Terner Center, Making It Pencil 2023](https://ternercenter.berkeley.edu/wp-content/uploads/2023/12/Making-It-Pencil-December-2023.pdf)
- [Development margin on cost vs revenue (Australia)](https://www.feasly.com.au/guides/development-margin-on-cost-vs-revenue-australia)
- [Fannie Mae 5% down on 2-4 unit homes](https://themortgagereports.com/107690/fannie-mae-introduces-5-down-payment-option-for-multifamily-homes)
- [2026 FHA loan limits in Illinois](https://www.lendingtree.com/home/fha/fha-loan-limits-in-illinois/)
- [Spokane middle housing permits](https://www.spokanejournal.com/articles/18294-missing-middle-housing-gains-traction-in-spokane)
- [FHFA House Price Index datasets](https://www.fhfa.gov/data/hpi/datasets)
- [FRED: PPI net inputs to residential construction, goods](https://fred.stlouisfed.org/series/WPUIP2311001)
- [Chicago Open Space Impact Fee](https://chicago.gov/city/en/depts/dcd/supp_info/open_space_impactfee.html)
- [Early April 2026: ADU goes permanent, ChiBlockBuilder opens](https://www.chicagocityscape.com/blog/four-early-april-2026-dates-adu-chiblockbuilder-jackson-park)
- [Chicago ADU ordinance passed with aldermanic control](https://www.axios.com/local/chicago/2025/09/26/city-council-chicago-adu-reform-leadership-delay)
- [Chicago single-stair ordinance hearing](https://www.chicagocityscape.com/blog/single-stair-benefits-for-chicagoans-20260330)
- [Chicago single-stair status, May 2026](https://hoodline.com/2026/05/city-stair-rules-trip-up-chicago-s-neighborhood-housing-boom/)
- [Single-stair rules across the US (Niskanen Center)](https://www.niskanencenter.org/understanding-single-stair-reform-efforts-across-the-united-states)
- [What's next for Pritzker's stalled housing plan](https://www.dailyherald.com/20260607/real-estate/whats-next-for-pritzkers-stalled-housing-plan/)
- [Canada Housing Design Catalogue](https://www.canada.ca/en/housing-infrastructure-communities/news/2025/03/federal-government-unveils-designs-as-part-of-the-housing-design-catalogue.html)
- [Washington permit-ready plan dashboard](https://www.commerce.wa.gov/new-permit-ready-plan-resources-and-dashboard-now-available/)
- [ICC and Archistar](https://www.iccsafe.org/about/periodicals-and-newsroom/international-code-council-collaborates-with-archistar-to-modernize-permitting-and-accelerate-housing-development)
- [Land readjustment in Japan (World Bank)](https://documents1.worldbank.org/curated/en/481571569562840686/pdf/Land-Readjustment-in-Japan-Case-Study.pdf)
- [Learning from Houston's townhouse reforms (Mercatus)](https://www.mercatus.org/node/89801)
- [FHFA Uniform Appraisal Dataset aggregate statistics](https://www.fhfa.gov/uniform-appraisal-dataset-aggregate-statistics)
- [MSHDA Missing Middle Housing Program](https://www.ncsha.org/hfa-news/mshda-launches-new-housing-production-program-to-increase-attainable-housing-stock/)
