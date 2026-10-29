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
