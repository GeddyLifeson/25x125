# 25x125: Illinois Development Pipeline, Lot to Sale or Lease

Oct 28, 2026 · @Marlon

## Summary

Build an Illinois deal pipeline, starting in Chicago, for small brokerages and owner-operators that develop 2-6 flats, small commercial, and mixed-use buildings. Start with two modules: a **site finder** that surfaces lots and old buildings worth developing, and a **feasibility screen** that tells the user in minutes what the city allows on that parcel and whether the numbers work.

The rest of the pipeline (entitlements, permits, financing, construction, closeout, sale or lease-up) gets added later, one module at a time, all tied to the same property record.

**Who it's for.** Small Chicago brokerages and investor-builders who already find deals and know the market, but run the middle stages of development on spreadsheets, email, and memory. Your own company and your partner managing contractor are the first test users.

**Why Illinois, starting with Chicago.** Zoning districts, aldermanic sign-off, permit paths, water and sewer connections, and Cook County taxes are all local. National tools treat them generically. A product that knows these rules at the parcel level is hard for a national competitor to copy quickly.

**Expansion order.** Chicago first. Then the Cook County suburbs, which share the county assessor and tax system but have their own zoning. Then Lake County, then McHenry County, then the rest of Illinois. State rules (the license law, mechanics liens, the film credit, the state parking law, historic credits) carry over everywhere; each municipality adds its own zoning and permit rules. Markets outside Illinois are on hold.

**Why start with finding and feasibility.** Every project starts with the question "should we buy this, and what can we build?" It happens weekly, money is committed on the answer, and the people asking are brokers, which matches your license and network. Once a deal lives in the product, every later stage can attach to it.

The sections below walk the full pipeline stage by stage, with the Chicago rules that apply, where projects typically go wrong, and the data 25x125 should track at each step.

## The pipeline at a glance

&#91;embedded content: development pipeline · 8 stages, 8 modules\]

Each stage on the left gets one software module on the right, and every module reads and writes the same property record. The two highlighted modules are the first release; the rest follow in the phases shown.

## Stage 1: Find and tie up the site

Most of the data needed to find Chicago development sites is free, public, and available through APIs. The gaps are foreclosure filings, current tax-sale lists, and Cook County Land Bank inventory, which need paid data or manual intake.

**What happens at this stage.** A broker or owner spots a vacant lot, a teardown, a distressed building, or an underused commercial parcel. They find the owner, make contact, negotiate, and put the property under contract with time to check feasibility before closing.

**Who's involved.** Broker, owner or seller, attorney, title company, sometimes a lender for the land purchase.

**Where it goes wrong.** Good sites are found by driving around or by word of mouth, so coverage is patchy. Owners of distressed property are hard to reach. Buyers sign contracts with too little time to check zoning and costs.

**Competitors at this stage**

- **Chicago Cityscape** ($1,375 a year) already combines city permits and violations, Assessor data, Clerk recordings, tax sale lists, Land Bank and city land, TIF, and zoning. [source](https://www.chicagocityscape.com/vs/siteselection) 25x125 has to go past map layers: rank sites by what can be built and whether it pencils, connect straight into feasibility and the rest of the pipeline, and help with owner outreach.
- **DealMachine** (about $99-279 a month) is the model for the mobile side: drive a neighborhood, tap a building, and get the owner and property data. 25x125 adds Chicago zoning and feasibility on the spot, so a tagged building shows what it could become and whether it pencils. [source](https://resimpli.com/blog/dealmachine-pricing/)
- **BatchLeads** ($119-749 a month) covers national lead lists: 140+ filters, skip tracing, dialing, and direct mail, now under the same owner as PropStream. It has no zoning, feasibility, or construction tools, so 25x125 should import its lists rather than rebuild them. [source](https://resimpli.com/blog/batchleads-pricing/)

**Free public data the site finder can use**

| Signal | Source | Dataset ID | What it shows |
| --- | --- | --- | --- |
| City-owned land for sale | [Chicago Data Portal](https://data.cityofchicago.org) | aksk-kvfp | About 12,000 city-owned parcels with zoning, size, value, sale status |
| Vacant land | [Cook County Assessor](https://datacatalog.cookcountyil.gov) | pabr-t5kh (class 100, 190, 241) | Every parcel with class code, location, ward, census tract, flood flag |
| Recent sales | Cook County Assessor | wvhk-k5uv | Sale prices for comps and land values |
| Vacant building complaints | Chicago 311 | v6vf-nfxy | About 4,800 vacant/abandoned building complaints so far in 2026 |
| Code violations | Chicago Data Portal | 22u3-xenr | Building violations, updated daily |
| Scofflaw list | Chicago Data Portal | rz4d-qp2m | Owners with serious unresolved violations |
| Teardown signal | Chicago Data Portal | qhb4-qx8k | Asbestos and demolition notices, updated daily |
| Permits | Chicago Data Portal | ydr8-5enu | New construction, renovation, wrecking permits |
| Zoning | Chicago Data Portal | dj47-wfun | Current zoning district for every parcel |
| TIF and Enterprise Zones | Chicago Data Portal | eejr-xtfb, 64xf-pyvh | Incentive boundaries |
| Historic status | Chicago Data Portal | 2u8t-236p, uct4-hrvh | Orange/red rated buildings and landmarks (demolition limits) |
| Transit distance | Assessor + CTA/Metra | ydue-e5u3, 8pix-ypme | Distance to stations, for transit-served location rules |

All of these are queryable through the Socrata API, which worked without a key in testing; a free app token avoids throttling. [source](https://dev.socrata.com/docs/app-tokens)

**Sources that need extra work**

- **Cook County Land Bank:** pre-qualified buyers browse an inventory that changes daily; no public API found. [source](https://cookcountylandbank.org/what-are-you-looking-for/)
- **ChiBlockBuilder:** the city's lot sale program. The spring 2026 round offered more than 600 lots, including 30 "Missing Middle" lots for 2-6 flats with up to $150,000 per unit in construction help. [source](https://chicagocityscape.ngrok.io/blog/four-early-april-2026-dates-adu-chiblockbuilder-jackson-park)
- **Tax sales:** a state law signed in February 2026 moved the Tax Year 2023 annual sale deadline to December 1, 2026, while Illinois reworks tax-sale rules. It may move again. [source](https://legiscan.com/IL/bill/HB0598)
- **Foreclosures and probate:** searchable case by case at the Clerk of Court, with no bulk feed. Realistic options are ATTOM (API from $500 a month) or PropStream ($99-699 a month). [source](https://www.attomdata.com/solutions/delivery/property-data-api/pricing/) [source](https://www.propstream.com/news/how-much-does-propstream-cost)
- **MLS listings (MRED):** licensed data only. A product sold to other brokerages needs its own vendor license, or each customer connects their own MRED account. Since you have MRED access through your brokerage, you can prototype the listings layer for your own use first, then apply for a vendor license before selling it. Scraping is prohibited. [source](https://www.rismedia.com/2026/09/15/court-denies-zillow-in-mred-case/)
- **CoStar, LoopNet, Zillow:** terms ban scraping and resale. Don't use them as data sources.

**What the software tracks at this stage:** parcel (PIN), address, owner of record, zoning, lot size, class code, distress signals, outreach history, offer and contract terms, contingency deadlines.

**Outreach rules:** calls and texts to owners fall under the TCPA, email under CAN-SPAM, and broker advertising under the Illinois license law.

## Stage 2: Feasibility and underwriting

New small multifamily in Chicago costs roughly $308,000-365,000 per unit all-in, based on the city's 2026 Missing Middle awards. A deal works only if sale prices or rents cover that plus land and profit. The feasibility screen's job is to show that math in minutes for any parcel, priced for that parcel's neighborhood (see Neighborhood-level pricing). The citywide figures below are only defaults.

**What the screen calculates**

1. **What can be built.** Units, floor area, and height under current zoning (Stage 3 table), plus what an administrative adjustment, ADU, or rezoning would add.
2. **Code thresholds that change cost.** The layout and cost planner section lists them; the biggest are below.
3. **Cost.** Land, hard costs, soft costs, contingency, financing, permit fees.
4. **Incentives.** Dollar value of each program that applies (Incentives map), defaulting to maximum with toggles.
5. **Exit.** Sale value, or rent and net operating income if held, with transfer taxes and property tax.
6. **Result.** Profit, return on cost, and the maximum land price that still works, side by side for each scenario.

**Chicago cost benchmarks**

| Item | Figure | Source |
| --- | --- | --- |
| New multifamily hard cost | $220-490 per sq ft | [RLB Q1 2026 via City That Works](https://citythatworks.substack.com/p/an-agenda-for-family-friendly-housing) |
| Missing Middle 2026 awards, all-in | About $365,000 per unit average (108 units, $39.4M) | [City of Chicago](https://www.chicago.gov/city/en/sites/missing-middle/home/selected-proposals/round-2.html) |
| West Chatham three-flats | About $308,000 per unit | Same |
| Morgan Park six-flats | About $325,000 per unit | Same |
| Gut rehab | $100-200 per sq ft; kitchens $25-55k, baths $23-53k | [Block Renovation](https://www.blockrenovation.com/guides/the-ultimate-guide-to-home-renovation-costs-in-chicago-2026) |
| Soft costs | Roughly 20-30% of hard cost, plus 10-15% contingency (industry range) | Unverified for Chicago |
| Underground parking | About $36,000 per space | [City That Works](https://citythatworks.substack.com/p/lets-make-it-cheaper-to-build) |
| Building permit, new residential up to 3 units | Construction factor x 0.75 x gross area, $2,000 minimum | [2025 fee tables](https://www.chicago.gov/content/dam/city/depts/bldgs/general/Permitfees/2025%20Bldg%20Permit%20Fee%20Tables.pdf) |
| Building permit, 4+ units or mixed use | Construction factor x 1.0 x gross area, $3,000 minimum | Same |

These published figures are the starting point. Users can override every cost, and your own job costs replace them as you collect them.

**Code thresholds that move the budget**

- **3 units or fewer:** no sprinkler system required (residential up to 4 stories). A 4th unit triggers sprinklers. [source](https://www.chicago.gov/content/dam/city/depts/bldgs/general/CodeModernization/HBAGC%20August%2013%202019%20for%20web.pdf)
- **3 stories or fewer:** one exit stair can serve up to 4 units per story, and stairs can be wood. Going to 4 stories requires two stairs. [source](https://dev-codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2547444)
- **4+ units:** ground-floor units must meet Fair Housing accessibility (Type B); walk-up upper floors are exempt. [source](https://www.chicago.gov/content/dam/city/depts/bldgs/general/Self_Cert_Program/2019/05-ACCESSIBILITY.pdf)
- **4+ units:** a Certificate of Occupancy is required (Stage 7).
- **Fire limits** (inside Halsted, Division, Roosevelt, and the lake): wood frame mostly not allowed.
- **Architect required** for any building of 3+ units, mixed use, or ADU. [source](https://www.ilga.gov/legislation/ilcs/fulltext.asp?DocName=022503050K3)

Each threshold adds a fixed cost that the units above it have to carry, so unit count is the first thing the feasibility screen and the layout planner test.

**Where it goes wrong.** Buyers pay a land price based on units the zoning won't allow. Hard costs are estimated per unit from an old project. Incentives are counted that the project can't actually claim.

## Neighborhood-level pricing

Every number in the feasibility screen is priced for the parcel's own neighborhood. A 3-flat in Andersonville and one in the Loop or West Englewood have different land costs, sale prices, rents, taxes, and even build costs, and a citywide figure gives the wrong answer in all of them.

**How prices are localized**

| Number | Local basis | Data source |
| --- | --- | --- |
| Land value | Recent vacant-land and teardown sales within the same Assessor neighborhood, widened to the community area only when there are too few sales | [Assessor parcel sales](https://catalog.data.gov/dataset/assessor-parcel-sales) (wvhk-k5uv), MLS closed sales |
| Sale price per unit or sq ft | Closed sales of similar buildings (age, unit count, size) nearby, weighted by distance and recency | MLS (MRED) closed sales, Assessor sales |
| Rent | Recent leases for similar units nearby | MLS rental listings and leases; Census ACS median rent by tract as a check; Zillow's free rent index by ZIP (check terms before commercial use) |
| Property tax | The parcel's own tax rate and the Assessor's neighborhood model | Assessor and Treasurer data; [Assessor neighborhood boundaries](https://catalog.data.gov/dataset/cook-county-assessors-residential-neighborhood-boundaries) |
| Hard cost | Citywide base cost adjusted for site factors (below) | Published ranges, then your own job costs |
| Incentives | Parcel-specific (TIF, zone, tract) | Incentives map |

**Geography levels, from finest to broadest:** block face, Assessor neighborhood, census tract, community area (77 in Chicago), ward. The Assessor builds its own values from neighborhood-level models and draws appeal comparables from within neighborhoods, so its neighborhoods are the natural default unit. [source](https://catalog.data.gov/dataset/cook-county-assessors-residential-neighborhood-boundaries)

**Site factors that change build cost from block to block**

- Inside the fire limits (downtown core): wood frame mostly not allowed.
- Alley access or not: affects staging, deliveries, and garage or parking options.
- Public-way permits for staging on busy streets.
- Demolition surcharge in the 606 and Pilsen districts.
- Historic rating or landmark district: 90-day demolition hold and design review.
- Existing utility service size and age on the block.
- Soil and groundwater conditions, which call for a geotechnical report on ground-up projects.

**Showing the work.** Each localized number shows how many comparables it rests on, how recent they are, and how far away. When data is thin (few sales in a small neighborhood), the screen says so and shows the range instead of a single figure. Users can open the comps, drop ones that don't fit, and override any number.

**Cost margins.** Every cost shows a central estimate followed by minus and plus margins in dollars, for example $1,375,000 (-$275,000 / +$413,000). The percentages below set those dollar margins; the screen never shows the percentages themselves. The margin follows how construction estimators class estimates: wide and tilted upward early, narrowing as design and bids come in, because overruns are more common than savings.

| Project stage | What exists | Margin shown |
| --- | --- | --- |
| Site finder and feasibility | Parcel, zoning, neighborhood data | -20% / +30% |
| Layout planner | Unit layout and floor area | -15% / +20% |
| Architect drawings priced by unit costs | Drawings, quantities | -10% / +15% |
| Subcontractor bids in hand | Signed or firm bids | -5% / +5% |

The central estimate comes from published Chicago cost ranges adjusted by a neighborhood index built from city permit data. A first test on 292 new 2-6 unit permits since 2022 put Humboldt Park at 0.77 of the West and Northwest Side median and Logan Square and West Town at about 1.6. Reported permit costs run low because fees are based on them, so they set the neighborhood index and trend, not the dollar amount. Where a neighborhood has fewer than 10 recent permits, the margin widens and the screen says the sample is thin.

## Incentives map

The incentives that matter most for small Chicago projects in 2026 are 100% bonus depreciation, Opportunity Zones, the Missing Middle program on city lots, historic credits, and Cook County's commercial tax classes for mixed-use space. Two federal energy credits ended June 30, 2026, and several local programs face sunsets in 2026-2028. Not tax or legal advice.

**What each program is worth and how the software flags it**

| Program | What it's worth | Who qualifies | How the software finds it | Status |
| --- | --- | --- | --- | --- |
| Bonus depreciation | 100% first-year write-off of short-life parts of the building (found by cost segregation) | Property acquired after Jan 19, 2025 | Applies to every scenario | Permanent [source](https://www.nixonpeabody.com/insights/alerts/2025/07/16/low-income-housing-and-community-development-tax-credits-in-the-big-beautiful-bill) |
| Section 179 | Expensing up to $2.56M in 2026 | Business property, phase-out from $4.09M | Applies to every scenario | Annual limits [source](https://www.currentfederaltaxdevelopments.com/blog/2025/10/9/2026-inflation-adjustments-for-tax-professionals-revenue-procedure-2025-32-analysis) |
| Opportunity Zones | Capital gains deferral, 10% basis step-up, tax-free appreciation after 10 years | Investors putting capital gains into a fund; Chicago projects must more than double the building's basis within 30 months | Census tract match; two layers: 2018 zones (valid through 2028) and 2027 zones once certified | Permanent; Illinois nominated 238 tracts for 2027 [source](https://www.forvismazars.us/forsights/2026/07/opportunity-zones-permanent-under-ob3-2026-round-insights) [source](https://gov.illinois.gov/news/press-release.32858.html) |
| Missing Middle (city lots) | Lots sometimes $1; up to $150,000 per unit in construction help | 2-6 flats and townhomes on designated city lots; owner-occupant buyers | City-owned land dataset and program rounds | 2026 round: 30 lots in South Chicago and West Englewood [source](https://chicago.gov/city/en/sites/missing-middle/home.html) |
| TIF Small Business Improvement Fund | Grants for permanent building improvements | Property inside a TIF district | TIF boundary layer (eejr-xtfb) | Rolling by district; 13 districts expire end of 2026 [source](https://www.civicfed.org/understanding-chicagos-2026-record-tif-surplus) |
| TIF Neighborhood Improvement Program | $16,850-30,050 by unit count for 1-4 unit homes | Owners up to 140% of area median income | TIF layer | Not accepting applications now [source](https://www.chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/tif-nip.html) |
| Federal historic credit | 20% of qualified rehab cost, over 5 years | Income-producing certified historic buildings | Landmark and National Register layers | Unchanged [source](https://www.novoco.com/notes-from-novogradac/historic-tax-credit-advocates-push-htc-go-modernization-after-obbba-omission) |
| Illinois historic credit | 25% of qualified rehab, up to $3M per project | Same, with spending above the building's adjusted basis; competitive rounds | Same layers | Through Dec 31, 2028 [source](https://dnrhistoric.illinois.gov/preserve/statecredit.html) |
| Cook County Class L | Assessment at 10% instead of 25% for 10 years, renewable to 22 | Landmark or contributing buildings, commercial or multifamily | Landmark layer | Renewals allowed since Nov 2025 [source](https://www.dlapiper.com/insights/publications/2025/11/cook-county-modifies-class-l-property-tax-incentive-program-to-allow-renewals) |
| Cook County Class 7a/7b/8 | Commercial assessment at 10% instead of 25% for 10 years | Commercial space (the retail floor of a mixed-use building); city resolution required; $1,000 application | Use type + area | Ordinance sunsets Dec 31, 2027 unless renewed [source](https://cmap.illinois.gov/wp-content/uploads/CMAP-UIC_Incentives-Report_December-2025.pdf) |
| Affordable housing special assessment | Assessed value cut 25-35% for 10 years, renewable to 30 | 7+ units with 15-35% affordable at 60% of area median income | Unit count + affordability setting | Active [source](https://www.cookcountyassessoril.gov/frequently-asked-questions-ahsap) |
| Enterprise Zone | Sales tax exemption on building materials | Projects in Chicago's 6 zones (about 30% of the city); certificate needed before buying | Enterprise Zone layer (64xf-pyvh) | Active; residential eligibility to confirm [source](https://www.chicago.gov/city/en/depts/dcd/supp_info/enterprise_zone_program.html) |
| Neighborhood Opportunity Fund | Grants up to $250,000 | Commercial and cultural space in eligible areas | Area layer | Annual round [source](https://www.chicago.gov/DPDgrants) |
| Utility new-construction programs | Free energy modeling plus incentives | Commercial, multifamily, and affordable projects that beat code; engage early in design | Applies to new construction | Amounts not published [source](https://nicorgas.com/business/build-with-natural-gas/offers-and-incentives.html) |

**Ended or at risk (the software must not count these by default)**

- **45L new energy-efficient home credit** (up to $5,000 per unit): ended for homes acquired after June 30, 2026.
- **179D commercial energy deduction:** ended for construction starting after June 30, 2026. [source](https://www.bradymartz.com/the-june-30-2026-tax-incentive-deadline-what-builders-and-developers-need-to-know/)
- **Illinois Affordable Housing (donation) Tax Credit:** statutory sunset Dec 31, 2026; an extension was reported but not confirmed. [source](https://www.nprillinois.org/government-politics/2026-06-12/despite-builds-failure-housing-advocates-celebrate-legislative-wins)
- **LIHTC and New Markets Tax Credits:** expanded and permanent, but rarely practical for 2-6 flats. Show the census-tract flag as context. [source](https://www.huduser.gov/PORTAL/node/10476) [source](https://www.cdfifund.gov/news/537)

**Census data the investor network can show.** Each parcel gets its census tract from the Census Geocoder, then median income, poverty rate, and qualified-tract status from HUD and Census data. That gives investors context on the neighborhood and on which programs apply.

**Display rule.** Numbers first: each incentive shows its estimated dollar value for this project wherever it can be calculated, with the math visible. Values default to the maximum, and the user toggles what applies to them (for example, whether they have capital gains for an Opportunity Zone, or will meet an affordability set-aside) to see their own number. Each incentive also shows the eligibility conditions still to confirm, the deadline or sunset, and a link to the program.

## Stage 3: Zoning and entitlements

On a standard 25 x 125 Chicago lot, the zoning district decides whether you can build 1 unit or 7. Most of the city no longer requires parking near transit. A rezoning runs roughly 4-9 months and needs the alderperson's support. Small projects stall longest at this stage.

**What a 25 x 125 lot (3,125 sq ft) allows** [source](https://www.zoneomics.com/code/chicago-IL/chapter_2) [source](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-49197)

| District | Lot area per unit | FAR | Max height | Units on the lot |
| --- | --- | --- | --- | --- |
| RS-3 | 2,500 sq ft | 0.9 | 30 ft | 1 (2 only if 60%+ of the block is already multi-unit) |
| RT-4 | 1,000 sq ft | 1.2 | 38 ft | 3 |
| RM-4.5 | 700 sq ft | 1.7 | 45 ft | 4 |
| RM-5 | 400 sq ft | 2.0 | 45 ft | 7 |
| B/C -2 (e.g. B2-2) | 1,000 sq ft | 2.2 | 45-47 ft | about 3 |
| B/C -3 (e.g. B2-3) | 400 sq ft | 3.0 | 50 ft (55 with on-site affordable units) | about 7 |

Lot area per unit in all B and C districts, confirmed against the code: -1 is 2,500 sq ft, -1.5 is 1,350, -2 is 1,000, -3 is 400, -5 is 200. Ground-floor residential is allowed as of right only in B2 (and DR) districts; other B and C districts need a special use or administrative adjustment for it. [source](https://codelibrary.amlegal.com/codes/chicago/latest/chicagozoning_il/0-0-0-49197) [source](https://help.chicagocityscape.com/groundfloorresidential)

**Approval paths**

| Path | When you need it | Fee | Typical time |
| --- | --- | --- | --- |
| Administrative adjustment | Small changes: setbacks cut up to 50% to match the block, height up 10%, lot area down to 90% of minimum | $500 | Weeks; abutting owners and alderperson get 10 days notice |
| Variation (Zoning Board of Appeals) | Larger changes to bulk rules | $500 | Roughly 2-4 months (unverified) |
| Special use (ZBA) | Uses allowed only with approval | $1,000 | Roughly 2-4 months (unverified) |
| Type 1 rezoning | More units than the district allows | $1,025 | Roughly 4-9 months; $10k-30k+ in attorney and architect fees (practitioner estimate) |
| Planned development | Large sites only; 2-6 flats almost never trigger it | $1,500 | Longer |

Sources: [DPD rezoning steps](https://chicago.gov/city/en/depts/dcd/supp_info/map_and_text_amendment.html), [fee table](https://www.zoneomics.com/code/chicago-IL/chapter_13), [administrative adjustments](https://chicago.gov/city/en/depts/dcd/supp_info/administrative_adjustments.html)

**Type 1 rezoning steps**

1. Mail notice to owners within 250 ft, no more than 30 days before filing.
2. File with the Department of Planning and Development with the owner's authorization and plans.
3. DPD reviews and sends a recommendation to the Committee on Zoning.
4. Committee hearing, then a full City Council vote.
5. The approved plans become binding: unit count must match exactly; setbacks, height, FAR, and parking must substantially match.

Since December 2023, variations and administrative adjustments can be bundled into the Type 1 application, saving a separate ZBA trip. [source](https://www.thompsoncoburn.com/insights/update-to-chicago-zoning-rules-streamlines-approval-timeline/)

**The alderperson.** By custom the Zoning Committee follows the local alderperson's position, and most wards expect a community meeting. Some wards run formal community review. [source](https://40thward.org/city-services/community-driven-zoning/) The software should track each ward's process, contacts, meeting dates, and past decisions.

**Rules that change the math**

- **Parking:** since September 25, 2025, zero parking is required by right within 1/2 mile of CTA rail or 1/4 mile of eligible bus corridors, about 74% of the city. One bike space per unit is still required. [source](https://www.thompsoncoburn.com/insights/chicago-eliminates-parking-requirements-unlocks-certain-density-bonuses-with-new-ordinance/) Illinois' People Over Parking Act, effective June 1, 2026, bars parking minimums near transit statewide. [source](https://www.lplegal.com/content/people-over-parking-illinois-parking/)
- **Affordable Requirements Ordinance:** applies at 10+ units when you get a rezoning that adds density, city land, or city money. Set-aside is 10-20% depending on area. 2025 in-lieu fees ran from $64,512 per required unit in low-moderate income areas to $451,581 downtown, adjusted each January. A 2-6 flat project stays under the trigger. [source](https://chicago.gov/content/dam/city/sites/affordable-requirements-ordinance/2021-ARO-In-lieu-Fee-Table.pdf)
- **Transit density bonus:** in -3 districts near transit, projects with on-site affordable units can go to 300-350 sq ft per unit and FAR 3.5-4.0 without a rezoning. [source](https://www.chicago.gov/content/dam/city/sites/etod/Pdfs/CCO-Full-Explainer.pdf)
- **ADUs:** since April 1, 2026, coach houses and basement or attic units are allowed by right in RT-4 and higher and in B/C districts, and in RS areas only where the alderperson opted in. Buildings of 1-4 units can add one. Coach houses need a contractor in an approved apprenticeship program. [source](https://www.thedailyline.com/chicago-city-additional-accessory-dwelling-unit-legalization-ordinance-effective-april-application-process-housing-department)
- **Demolition delay:** buildings rated red or orange in the Historic Resources Survey get a 90-day hold on demolition permits. [source](https://chicago.gov/city/en/depts/dcd/supp_info/demolition_delay.html)
- **606 and Pilsen districts:** demolition surcharge of $20,000 per unit or $60,000 per building (whichever is greater) through 2029, and limits on converting multi-unit buildings to single-family. [source](https://www.chicago.gov/NWSPreservation)
- **New construction code:** mandatory for permits filed on or after December 1, 2026. Most small residential exceptions now reach 5 stories, and combustible rear porches are allowed up to 5 stories. [source](https://map-strategies.com/ideas/2026-chicago-construction-code-updates)

**Still not legal:** by-right 2-4 flats in RS districts (over 40% of the city is still RS or two-flat-only) and single-stair buildings above 3 stories. A single-stair proposal had a hearing in June 2026 with no vote. [source](https://www.thedailyline.com/chicago-city-council-zoning-committee-hearing-recap-single-stair-apartment-proposal-alderman-matt-martin-fire-buildings-department)

**What the software tracks:** zoning district and overlays per parcel, buildable units and floor area, required approvals, filing and hearing dates, notices sent, alderperson and community meeting status, conditions attached to approval.

## Stage 4: Design and permitting

A standard Chicago building permit averages 88 days, and about two-thirds of that time is the applicant fixing and resubmitting drawings. Self-certification by a trained architect cuts it to about 10 business days. Self-certification expands to new buildings up to 16 units in early 2027. [source](https://chicagocitywire.com/chicago-buildings-department-reports-88-day-average-permit-time-down-slightly-in-volume)

**Permit paths**

| Path | Covers | Typical time |
| --- | --- | --- |
| Express Permit | Minor work: interior remodels up to 2,000 sq ft per unit, reroofing, masonry, HVAC swaps, small garages | Fast, no plans |
| Self-Certification | Architect or engineer certifies code compliance; residential up to 8 units now, 16 units (4-story cap) planned for early 2027 | About 10 business days after zoning approval |
| Standard Plan Review | Default for work needing drawings | 88 days average in 2026 (29 city, 59 applicant) |
| Developer Services | Moderate and complex projects; third-party review option | Intake meeting first |

Sources: [self-certification](https://chicago.gov/city/en/depts/bldgs/provdrs/permits/svcs/self-cert-permits.html), [express permits](https://chicago.gov/city/en/sites/guide-to-building-permits/home/help/faq/DOB/EPP-eligible.html), [developer services](https://chicago.gov/city/en/depts/bldgs/supp_info/dynamicportalinstructions/DDS-NC.html)

The city also plans a "Ready Set Build" program for 4-50 unit buildings in 2027 and is piloting AI pre-screening of drawings. Permit fees are based on project value and use type, with a $302 minimum. [fee calculator](https://chicago.gov/city/en/depts/bldgs/provdrs/permits/svcs/permit_fee_calculator.html)

**Code changes.** The 2026 construction code update becomes mandatory for permits submitted on or after December 1, 2026. It moves the energy code to the 2024 IECC, requires ducted make-up air in dwelling units, extends most small-residential exceptions to 5 stories, and keeps Chicago's electrification-ready rules (40A circuits at gas ranges, 30A at gas dryers and water heaters). [source](https://map-strategies.com/ideas/2026-chicago-construction-code-updates) [source](https://www.bomachicago.org/2026/07/30/city-advances-2024-construction-code-updates/)

**Demolition before you build** [source](https://www.chicago.gov/city/en/depts/bldgs/provdrs/permits/svcs/demo-permits.html)

1. Asbestos survey by a certified inspector; notice due 10 working days before disturbing asbestos.
2. Health department demolition notice and dust mitigation plan.
3. Sewer cut-and-seal permit and water disconnect permit.
4. Rodent baiting with affidavit and Streets and Sanitation inspection.
5. Department of Housing sign-off if the building had apartments.
6. Check for the 90-day historic hold and the 606/Pilsen surcharge.
7. Demolition by a licensed GC (Class D or higher). Permit must start within 6 months of payment.

**Utilities and the public way** (2025 fee schedules; 2026 versions not yet found)

| Item | Cost |
| --- | --- |
| Water tap, 1" | $2,000 |
| Water tap, 2" | $2,760 |
| Water meter, 1" | $431 |
| Cut and seal old service | $2,350 |
| Sidewalk, street, or alley opening (CDOT) | $741.47 each |
| Residential driveway, 4 units or fewer | $10 one-time |
| Dumpster permit, residential street | $22.05 application + $50-100 use |

Sources: [water fees](https://chicago.gov/content/dam/city/depts/water/supp_info/2025_WaterServiceFeeSchedule.pdf), [CDOT fees](https://chicago.gov/content/dam/city/depts/cdot/permit/2025/CDOT%202025%20Permit%20Fee%20Schedule.pdf)

Peoples Gas and ComEd service requests go through their own portals with no published lead times; start them early. [Peoples Gas](https://www.peoplesgasdelivery.com/services/new-service-requirements)

**Where it goes wrong.** Incomplete drawings bounce back for repeated review rounds. Utility service is requested too late and holds up occupancy. Demolition steps are missed and stall the start.

**What the software tracks:** permit path chosen, submission and comment rounds, each reviewer comment and response, utility applications, demolition checklist, fees paid.

## Stage 5: Financing and closing

Small Chicago projects usually run on a bank construction loan covering 60-65% of cost, with the developer's equity going in first and every draw paid through a title company escrow. Small developers lose the most time on the paperwork behind each draw.

**Typical structure** (rates are from one secondary source; get quotes from local community banks)

| Lender type | Rate (mid-2026) | Loan-to-cost | Notes |
| --- | --- | --- | --- |
| Bank | About 7-8.75% (SOFR + 2.75-4%) | 60-65% | Recourse; personal guarantee standard |
| Debt fund | About 8.75-10.25% (SOFR + 4-6.5%) | 65-85% | Faster, more expensive |

[source](https://www.coradvisors.net/2026/05/construction-loan-rates-2026.html)

Loans are usually interest-only with an interest reserve, drawn monthly as work is completed and checked by a third-party inspector.

**How a Chicago draw works** (title escrow is standard practice)

1. GC submits a pay application for work completed.
2. Owner and GC sign sworn statements listing every sub and supplier and what each is owed.
3. Lien waivers collected from each listed sub and supplier.
4. Lender's inspector confirms percent complete.
5. Title company checks for new liens (date-down) and releases funds.

Chicago Title quotes construction escrow fees on request. [source](<https://www.cmetro.ctic.com/CTRSCMetro/media/publications/2026-RATE-CARD-(METRO)-FINAL.pdf>)

**Illinois Mechanics Lien Act rules the software must track** [source](https://www.alfainternational.com/compendium/construction/illinois/)

- The owner must get a sworn statement from the contractor before paying. Paying without sworn statements and waivers risks paying twice.
- A GC must record a lien within 4 months of completion to keep it good against lenders and buyers (2 years against the owner).
- Subcontractors and suppliers must serve notice within 90 days of their last work.
- Liens take priority over the value the improvements add to the property.
- Retainage caps under the state prompt payment law (10%, dropping to 5% at half complete) do not apply to buildings of 12 or fewer units, so 2-6 flats are exempt; small commercial is covered. [source](https://ogletree.com/insights/construction-one-minute-read-illinois-restricts-retainage-on-private-construction-projects)

**Where it goes wrong.** A missing waiver from one supplier holds up the whole draw. Change orders aren't reflected in the sworn statement. The budget and the lender's draw schedule drift apart.

**What the software tracks:** loan terms, budget by line item, draw schedule, sworn statements, lien waivers by sub and supplier (conditional and final), inspector reports, retainage held, lien deadlines.

## Stage 6: Construction

New-construction inspections in Chicago are currently taking about 25 business days to schedule because of inspector vacancies, so inspection timing needs to be built into the schedule from day one. [source](https://chicagocitywire.com/chicago-buildings-department-reports-88-day-average-permit-time-down-slightly-in-volume)

**Chicago general contractor license classes** [source](https://www.chicago.gov/city/en/depts/bldgs/supp_info/TLdetails/GC.html)

| Class | Project value limit | Insurance | Annual fee | Demolition |
| --- | --- | --- | --- | --- |
| A | Unlimited | $5M | $2,000 | Ordinary or complex |
| B | Up to $10M | $3M | $1,000 | Ordinary or complex |
| C | Up to $5M | $1M/$2M | $750 | Ordinary only |
| D | Up to $2M | $1M/$2M | $500 | Ordinary only |
| E | Up to $500K | $1M | $300 | None |

Project value counts all trades on the site. Plumbing, electrical, and mason work each need their own city license, and roofers need an Illinois roofing license. A 2-6 flat usually needs a Class C or D contractor.

**Inspections by phase**

| Phase | Inspections |
| --- | --- |
| Underground | Plumbing; rebar and steel before concrete pours |
| Rough | Carpentry, electrical, iron, plumbing, ventilation |
| Final | Boilers, carpentry, electrical, iron, plumbing, refrigeration, ventilation; Fire Prevention where required |

Permits suspend automatically if required inspections aren't requested.

**What the software does at this stage**

- Schedule linked to inspections, with the city's current wait time built in.
- Budget vs. actual by line item, tied to the draw schedule from Stage 5.
- Change orders with cost and schedule impact, flowing into sworn statements.
- Daily logs and photos, organized by unit and room so they feed the closeout package.
- Sub and supplier directory with license and insurance expiration alerts.
- Lien waiver collection per draw, flagged before the title company asks.

**Where it goes wrong.** Inspections requested late. A sub's insurance lapses mid-job. Change orders are approved verbally and never reach the budget or the lender. You already see these gaps in your own project management.

## Stage 7: Closeout and occupancy

A new 4-6 flat needs a Certificate of Occupancy before anyone moves in; a new 2-3 flat does not. Converting a storefront to apartments also needs one at any size. [source](https://chicago.gov/city/en/depts/bldgs/supp_info/certificate-of-occupancy.html)

**When a Certificate of Occupancy is required**

- New construction or substantial alteration with 4 or more dwelling units.
- More than 10,000 sq ft of non-residential space.
- Any change of occupancy (for example, retail to residential).
- Assembly spaces over 50 people, any size.

All inspection and reinspection fees must be paid first. Partial or temporary certificates are possible.

**Closeout checklist**

1. Final inspections passed for every trade.
2. Certificate of Occupancy, if required.
3. Punch list completed and signed off unit by unit.
4. Final lien waivers from every sub and supplier; final sworn statement.
5. Retainage released.
6. Warranties collected (roof, windows, HVAC, appliances, water heaters) with start dates.
7. As-built drawings, equipment model and serial numbers, paint colors and finish specs.
8. Utility accounts moved to owner or tenants.
9. New construction reported to the Cook County Assessor.

**The handoff package.** Everything above goes into one record that follows the building to whoever manages or buys it. Information usually gets lost at this handoff. A building that comes with its full history is also a selling point for buyers and investors.

**Property tax during and after construction.** Cook County assesses new buildings in proportion to completion until they're fit for occupancy. For commercial projects, the Assessor phases in value monthly toward the completed value. If the Assessor doesn't know the details, it assesses land only and later sends an omitted assessment bill, so the software should remind owners to file the New Construction Reporting Form. [source](https://www.cookcountyassessoril.gov/commercial-properties-under-construction-valuation-policy)

**What the software tracks:** final inspection results, certificate status, punch items by unit, warranties with expiration dates, equipment list, final waivers, retainage release.

## Stage 8: Exit (sell, lease up, or hold)

Model the exit decision during feasibility, because Chicago transfer taxes, landlord rules, and incentive classes all change the return.

**Selling**

- Chicago transfer tax: $5.25 per $500 of price ($3.75 paid by the buyer, $1.50 by the seller). The 2024 "Bring Chicago Home" increase was rejected by voters. [source](https://chicago.gov/city/en/depts/fin/supp_info/revenue/tax_list/real_property_transfertax.html)
- Cook County adds $0.25 and Illinois $0.50 per $500 (standard rates; not re-verified).
- The handoff package from Stage 7 becomes part of the listing and due diligence.

**Leasing up and holding**

- **Landlord-tenant ordinance (RLTO):** covers most rentals; owner-occupied buildings of 6 or fewer units are exempt. The 2026 security deposit interest rate is 0.01%, and the city's summary must be attached to every lease. [source](https://www.caapts.org/news/2026-illinois-and-chicago-security-deposit-interest-rates)
- **Fair Notice:** 60 days' notice to end a tenancy or raise rent for tenancies of 6 months to 3 years; 120 days beyond 3 years. [source](https://www.chicago.gov/content/dam/city/depts/doh/fair_notice/fair_notice_flyer.pdf)
- **Pending:** two competing renter-protection proposals (the mayor's Protecting Renters Ordinance and the FAIR ordinance) would add a rental registry, cap deposits, and lengthen notice periods. Neither had passed as of the last report found; council deferred them in late September 2026. [source](https://therealdeal.com/chicago/2026/09/29/chicago-city-council-stalls-renters-rights-discussion/)
- **Short-term rentals:** every unit needs a registration number. In 2-4 unit buildings only the host's primary residence can be rented; 5+ unit buildings cap at 25% of units or 6 units, whichever is less. Taxes total 10.5%. [source](https://chicago.gov/sharedhousing)

**Property tax incentives to model at exit**

- **Class L (landmarks):** 10% assessment for 10 years, then 15% and 20%, against a normal 25% commercial level; renewable since November 2025 for up to 22 years total. [source](https://www.dlapiper.com/insights/publications/2025/11/cook-county-modifies-class-l-property-tax-incentive-program-to-allow-renewals)
- **Affordable housing special assessment (state):** for 7+ units with 15-35% of units at 60% of area median income; apply before the building is in service. [source](https://www.cookcountyassessoril.gov/frequently-asked-questions-ahsap)
- **Class 7, 8, 9:** commercial and affordable-rental incentives; details in the incentives section.

**Short-term income.** A vacant commercial building can earn short-term license income from film productions or pop-up shops before or instead of a permanent lease. See the Interim section.

**What the software tracks:** exit plan and its assumptions, listing or lease-up status, rent roll, lease terms and notice dates, deposit interest due, tax incentive renewals.

## Product: modules and data model

Every module reads and writes one record: the **parcel**. A parcel starts as a lead in the site finder and carries everything learned about it through construction, sale, and management. No existing tool keeps one record across all eight stages.

**Core records**

| Record | Key fields | Created at |
| --- | --- | --- |
| Parcel | PIN, address, lot size, zoning, overlays (TIF, transit, historic, Opportunity Zone), census tract, owner of record, distress signals | Stage 1 (imported from Assessor and city data) |
| Deal | Status, offer, contract terms, contingency dates, acquisition cost | Stage 1 |
| Scenario | Program (units, sq ft, use mix), layout, cost estimate, incentives, pro forma, exit plan | Stage 2; several per parcel |
| Approval | Type (adjustment, variation, special use, rezoning, permit), filing date, hearing date, status, conditions | Stages 3-4 |
| Budget line | Category, estimate, committed, paid, change orders | Stage 5 onward |
| Draw | Period, amount, sworn statement, waivers, inspector sign-off | Stages 5-6 |
| Company | GC, subs, suppliers, architects, lenders: licenses, insurance, ratings, history | Any stage |
| Asset | Units, equipment, warranties, leases, rent roll | Stages 7-8 |
| Profile | Boutique company track record, built from completed parcels | Investor network |

**Modules, in build order**

| Phase | Module | What it does |
| --- | --- | --- |
| 1 | Site finder | Map and ranked list of parcels from public data; filters for vacancy, distress, city land, zoning, transit, incentives; owner outreach log |
| 1 | Feasibility screen | What zoning allows on the parcel, incentives that apply, a quick pro forma, go or no-go |
| 2 | Layout and cost planner | Grid-based unit layouts checked against Chicago code and priced (see its section) |
| 2 | Entitlement and permit tracker | Approval paths, deadlines, ward contacts, reviewer comments |
| 3 | Budget and draw manager | Budget, sworn statements, lien waivers, draw packages for the title company |
| 3 | Construction tracker | Schedule, inspections, change orders, photos, sub compliance |
| 4 | Handoff and asset record | Closeout package, warranties, equipment, leases |
| 4 | Sale and lease-up | Listing package, rent roll, lease deadlines |
| 5 | Investor network | Profiles, project listings, search, introductions |
| 5 | Interim (short-term space) | Short-term licensing of vacant or underused space to film productions and pop-up shops (separate brand) |

**Data foundation.** Phase 1 runs almost entirely on free city and county open data (Stage 1 table). Paid feeds (foreclosures, MLS) can be added per customer later. The parcel record is designed so each later module adds fields without changing what came before.

## Layout and cost planner

A grid-based builder, like RimWorld or Prison Architect, where users place rooms on their actual lot and see in real time whether each room meets Chicago code and what the building costs. No existing tool (TestFit, Archistar, Snaptrude, Hypar) encodes Chicago's own code rules. [source](https://www.iccsafe.org/about/periodicals-and-newsroom/international-code-council-collaborates-with-archistar-to-modernize-permitting-and-accelerate-housing-development)

**How it works**

- The lot loads from the parcel record with zoning setbacks, height limit, and buildable envelope drawn on a grid.
- Users drag rooms, stairs, porches, and walls into place, floor by floor.
- Each room checks itself against code as it's placed: green if it passes, red with the reason if not.
- A running cost total updates with every change, broken down by category.
- Users compare options side by side: cost against rent or sale value for each choice (a second bath, in-unit laundry, a coach house, an extra floor). The planner shows the numbers; the user decides.
- Gut rehabs start from the existing floor plan, imported from drawings or entered by hand.
- Import and export at every step, so an architect, contractor, or lender can pick up the file wherever they join.
- The output is a starting design. An Illinois-licensed architect must prepare and stamp the permit drawings for any 3+ unit, mixed-use, or ADU project.

**Code rules the planner checks** (Chicago Building Code; the 2026 update is mandatory for permits from December 1, 2026)

| Rule | Minimum | Source |
| --- | --- | --- |
| Largest room in each unit | 120 sq ft | [14B-12-1207](https://dev-codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2548475) |
| Other habitable rooms | 70 sq ft | Same |
| Combined living/dining/kitchen | 180 sq ft | Same |
| Ceiling height, habitable rooms | 7 ft (6 ft 4 in under basement beams) | Same |
| Ceiling height, baths and laundry | 6 ft 8 in | Same |
| Kitchen aisle | 36 in (30 in for units of 700 sq ft or less, non-accessible) | Same |
| Window glass, existing buildings | 6% of floor area, a third of it openable | [14X-6-602.2](https://codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2676077) |
| Borrowed light | Up to 2 rooms per unit; through an opening of 8% of floor area and 25+ sq ft | [DOB interpretation](https://www.chicago.gov/content/dam/city/depts/bldgs/general/Building%20Code/61314InteriorEnviron.pdf) |
| Single exit | Up to the 2nd story above grade, 4 units per story, 75-125 ft common path | [Table 1006.3.3](https://dev-codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2547444) |
| Stairs | 36 in wide under 50 occupants; 11 in treads, 7 in risers | [DOB training](https://www.chicago.gov/content/dam/city/depts/bldgs/general/Self_Cert_Program/CodesUpdate/SelfCertOneDayAM2.pdf) |
| Doors | 32 in clear (28 in in non-accessible units) | Same |
| Exterior wall rating | 2 hr within 3 ft of lot line, 1 hr at 3-30 ft | [AWC presentation](https://www.woodworks.org/wp-content/uploads/presentation_slides-SMITH-Chicago-Building-Code-Modernization-WDS-200311.pdf) |
| Porches | 60 psf for one unit, 100 psf shared; combustible porches allowed up to 5 stories under the 2026 code | [2026 update](https://map-strategies.com/ideas/2026-chicago-construction-code-updates) |
| Make-up air | Ducted make-up air in every unit (2026 code) | Same |

New-construction window percentages, corridor widths, and travel distances still need confirming against the full 2026 ordinance text; the planner should flag them until verified.

**Design moves the planner can suggest (with their cost effect shown)**

- Stay at 3 units or fewer to avoid sprinklers, or go to 6 and spread the sprinkler cost across more units.
- Stay at 3 stories so one stair can serve the building and stairs can be wood.
- Use a rear porch as the second exit.
- Stack kitchens and baths on every floor to shorten plumbing runs.
- Repeat one unit plan per floor.
- Keep units at 700 sq ft or less where it suits the market, for the narrower kitchen aisle.

**Cost data.** Starts from published Chicago ranges (Stage 2 table). Every number is editable, and your own job costs replace the defaults as you collect them in a consistent format.

## What to build first

The first version answers four questions for any Chicago parcel: what can I build here, what will it cost, what incentives apply, and does it make money? If it answers them faster and more accurately than Chicago Cityscape plus a spreadsheet, brokers will pay for it.

**First release: four screens**

1. **Map and search.** Map and results list side by side, the way MRED shows search results, so clicking a parcel in either highlights it in the other. All Chicago parcels with filters: vacant land, vacant-building complaints, violations, scofflaw owners, city-owned lots for sale, zoning district, distance to transit, TIF, Opportunity Zone, historic rating. Results ranked by a development score.
2. **Parcel page.** Everything known about one parcel: owner, zoning, lot size, assessed value, recent nearby sales, permits and violations history, incentives that apply, historic or demolition flags, 606/Pilsen surcharge flag.
3. **Feasibility screen.** Buildable units and floor area under current zoning (and with an administrative adjustment or rezoning), parking requirement, approval path and estimated time, rough hard and soft costs, incentive value, simple pro forma for sell and hold. Side-by-side scenarios.
4. **Deal list.** Saved parcels with status, notes, owner outreach log, and a one-page PDF export for partners, lenders, or investors.

**Build order**

1. Load Assessor parcel data and city zoning into a database with mapping support (PostgreSQL with PostGIS is the standard choice).
2. Add nightly pulls of permits, violations, 311 vacancy complaints, city land, and demolition notices through the Socrata API.
3. Write the zoning rules engine for the districts small developers use (RS, RT, RM, B, C) and the transit, ADU, and parking rules. Test it against real lots where you already know the answer.
4. Add the incentive layers (TIF, Opportunity Zone, census tracts, Enterprise Zone, historic).
5. Add cost estimates, seeded from your own and your partner contractor's recent job costs.
6. Build the pro forma and PDF export.
7. Put it in front of 5-10 Chicago brokers and developers, starting with your own team.

**Accuracy comes first.** A wrong zoning answer costs the user money. Every result should show its source and date, and anything not yet confirmed against the code should be flagged as unverified.

**Out of scope for version 1:** construction management, draws, the layout planner, investor network, and Interim. Each comes later on the same parcel record.

## Brand architecture

The technology is built once and sold under separate brands, each aimed at one audience, the way Hardee's and Carl's Jr. share a parent company or a restaurant group runs an online-only brand from the same kitchens. Each brand gets its own name, site, pricing, features, and marketing; customers of one never need to know about the others.

&#91;embedded content: brand architecture · 4 brands, 1 engine\]

The brands share the parcel record, data feeds, rules engine, pricing, incentives, and workflow tools; only the brand layer on top changes.

| Brand | Audience | What it emphasizes | How it charges |
| --- | --- | --- | --- |
| 25x125 | Chicago brokers, small developers, owner-builders | Zoning, feasibility, incentives, the full development pipeline | Monthly subscription per user or team |
| Interim | Landlords, brokers, film producers, pop-up businesses | Short-term licensing of vacant or underused space | Brokerage commission or listing subscription |
| Wholesale brand (name to come) | Wholesalers and investors working off-market deals | Distressed lead scoring, owner outreach, quick after-repair values, buyer lists | Subscription plus usage (lists, outreach) |
| Illinois expansion | Developers in the Cook County suburbs, then Lake County, then McHenry County, then the rest of Illinois | The same engine loaded with each municipality's zoning, permits, and data, sold under the 25x125 name | Same model as 25x125 |

**Rules for keeping them separate**

- One shared account system and database behind the scenes, kept invisible to customers.
- Each brand's data stays visible only to that brand's users unless a customer connects them.
- Launch one brand at a time. Every brand needs its own marketing budget and support, so 25x125 proves the engine first.
- Each new Illinois municipality needs its own zoning and permit rules, neighborhood data, and local incentives before it goes live.

**Wholesale brand: a licensing rule to build in.** Under the Illinois real estate license law, dealing in assignable purchase contracts or options on 2 or more occasions in 12 months counts as brokerage and needs a license. [source](https://ilga.gov/legislation/ilcs/documents/022504540K1-10.htm) The wholesale brand should show that rule to Illinois users and track their assignment count.

## Investor network (later phase)

The network lets investors find small boutique developers and their projects, and lets those developers show a verified track record. It is a networking and listing service only. No money moves through the platform, and boutique companies pay a flat subscription for access.

**How it works**

- **Profiles for boutique companies:** projects completed, budgets and schedules hit, entitlements won, current pipeline. Pulled automatically from the pipeline modules, so the track record comes from real data instead of self-reported claims.
- **Project listings:** a deal can be posted with its feasibility summary, incentives that apply, and the capital it needs.
- **Search by anything:** neighborhood, project type (2-6 flat, commercial, mixed use), budget size, stage, incentive programs (TIF, Opportunity Zone, historic credit), census-tract data, developer track record.
- **Incentives shown up front:** each listing shows the tax breaks, credits, and public dollars attached to the parcel, so investors can see how much public money backs each project.
- **Introductions:** investors request a conversation; everything after that happens off-platform between the parties and their lawyers.

**Search layout.** Map and list together, like MRED results, with filters on any field.

**Launch profiles.** Your own projects and your family company's go in first, so investors see a complete example on day one.

**Who pays.** Boutique companies pay a monthly or annual subscription to list. Investors browse free at first. A paid investor tier (saved searches, alerts, deeper data) can come later.

**The legal line to stay behind** (not legal advice; a securities attorney should review the model before launch)

- **No success fees.** A fee tied to whether a deal closes or how much is raised is the main thing that turns a platform into an unregistered broker-dealer under federal law. A flat subscription unrelated to outcomes avoids that. [source](https://angelinvestorsnetwork.com/regulatory-compliance/unregistered-finders-broker-dealer-compliance-sec-2026)
- **No handling of funds, no recommendations.** The federal safe harbor for online platforms in Rule 506 offerings only applies when the platform takes no compensation tied to the sale and never holds investor money. Ranking or "featuring" deals as good investments can also drift into solicitation. [source](https://www.securitieslawyer101.com/2020/09/28/rule-506b-and-rule-506c-online-platforms/)
- **Which deals can advertise.** Developers raising under Rule 506(c) can advertise publicly but may only accept verified accredited investors. Rule 506(b) raises cannot be advertised publicly at all, so they shouldn't appear as open listings. [source](https://www.ropesgray.com/en/insights/alerts/2025/03/sec-issues-no-action-letter-clarifying-rule-506c-accredited-investor-verification)
- **Illinois has no finder exemption.** Treat anyone paid to bring in investors as needing registration in Illinois. [source](https://lig.ilga.gov/legislation/ilcs/documents/081500050K2.7.htm)
- **Keep property deals separate from investment deals.** Connecting buyers and sellers of actual land or buildings for a fee is real estate brokerage and needs an Illinois brokerage license held by the entity. Selling shares of a project LLC is a securities matter, which a real estate license does not cover. [source](https://ilga.gov/legislation/ilcs/documents/022504540K1-10.htm)
- **Small-investor option later.** If you ever want non-accredited Chicago residents to invest, partner with a registered funding portal under Reg CF ($5M per issuer per year), or look at Illinois' intrastate crowdfunding exemption, which allows an exempt portal charging fixed fees. [source](https://www.sec.gov/resources-small-businesses/regulation-crowdfunding-guidance-issuers) [source](https://ilga.gov/legislation/publicacts/99/099-0182.htm)

**Watch:** the SEC listed new rules on finders and exempt offerings for October 2026, but no proposal had been published as of this writing. [source](https://www.thecorporatecounsel.net/blog/?p=59751)

**Closest existing model:** Small Change, a Reg CF funding portal focused on small urban developers. [source](https://www.crowdfundinsider.com/2025/01/235479-small-change-real-estate-crowdfunding-platform-reports-best-year-yet/) Larger platforms such as CrowdStreet, Fundrise, and RealtyMogul serve bigger deals, and several have had investor losses or paused redemptions in 2025-2026.

## Interim: short-term space for productions and pop-ups

The same parcel engine can find vacant buildings for film and TV productions and either license them short-term as one-off sets or convert them into permanent stages. Chicago has large studios and tiny photo studios, but few mid-size (5,000-15,000 sq ft) flexible spaces for independent producers. That gap is inferred from the state's stage directory; no published study confirms it. [source](https://dceo.illinois.gov/whyillinois/film/locations/soundstages.html)

**Two tracks**

|  | One-off remodel (short-term license) | Permanent stage |
| --- | --- | --- |
| Building | Vacant or occupied: storefront, warehouse, restaurant on a closed day, old house | Warehouse or industrial building with clear span and height |
| Agreement | Location or license agreement for weeks or months | Both options modeled side by side: build and lease to a production company or stage operator, or own and operate |
| Zoning | Existing use plus owner approval; no city filming permit for interiors | Usually M or C districts, or a Planned Development; Chicago has no "film studio" use category |
| Building code | Normal occupancy and egress rules; special effects need fire department permits | Likely a change of occupancy (warehouse to production), which can trigger sprinkler and egress upgrades |
| Revenue | Daily or weekly license fee during vacancy; any kept build-outs add value | Stage rent; anchor tenants matter |
| Who pays you | Broker leasing fee or listing subscription | Brokerage, development, and asset management |

**Illinois film tax credit (the second incentive layer)**

- 35% of qualified Illinois spend and resident wages since SB 1911 (signed December 2025, retroactive to July 1, 2025). Non-resident wages get 30%. [source](https://reelchicago.com/article/illinois-strengthens-film-incentives-as-gov-pritzker-signs-sb-1911/)
- Stackable extras: +15% on wages of workers from economically disadvantaged areas, +5% outside the six-county Chicago region, +5% for relocating TV series, +5% for certified green productions. [source](https://www.ep.com/production-incentives/us/illinois)
- Minimum spend: $50,000 for projects under 30 minutes, $100,000 for longer. No annual cap. Credits are transferable and sell for about 90 cents on the dollar. [source](https://dceo.illinois.gov/whyillinois/film/filmtaxcredit/rulesandrequirements.html)
- Runs through 2038 or 2039 (sources disagree).
- Set construction and stage rental from Illinois vendors probably count as production spend; a building owner's permanent improvements do not. Confirm with the Illinois Film Office's qualified expenditures list.
- Film and TV production spending in Illinois hit a record $703 million in 2025. [source](https://reelchicago.com/article/production-spending-hits-record-high-as-chicago-stays-busy/)

**Stage-building money.** The state's Soundstage Capital Grant gave $1-5M matching grants for stages of 10,000+ sq ft, but no funding round is open now. [source](https://omb.illinois.gov/public/gata/csfa/Program.aspx?csfa=3134) The Fields Studios in Avondale, a converted Marshall Field's warehouse, received $5M state and $5M city grants. [source](https://www.preservationchicago.org/win-the-fields-studios-received-10m-in-city-and-state-grants/) A pending city ordinance (O2026-0027135) would change the lease tax on film equipment rentals. [source](https://chicago.councilmatic.org/legislation/o2026-0027135/)

**City filming permits.** Only needed when equipment or vehicles use the street, sidewalk, or alley: $250 per location per day, $25 for student and independent projects, 4-10 business days lead time, and $1M liability insurance naming the city. Private interiors need only the owner's approval. [source](https://chicago.gov/city/en/depts/dca/supp_info/chicago_film_office5.html)

**Competing marketplaces**

| Platform | Model | Covers conversion or buildout? |
| --- | --- | --- |
| Giggster | 19% host commission plus renter fee [source](https://help.giggster.com/en/articles/2832062-how-much-commission-does-giggster-take) | No |
| Peerspace | Host and guest fees [source](https://www.peerspace.com/legal/terms/fees-overview) | No |
| LocationsHub | Owner listing subscription, no commission [source](https://locationshub.com/faqs) | No |
| Reel-Scout | Software sold to film offices; runs the Illinois Film Office location library [source](https://reelchicago.com/article/ifo-put-its-locations-library-online-brreelscout-exclusive-services-film-offices) | No |

None of them find a building to convert, check zoning and code, or manage the buildout and restoration, which leaves that work open for Interim.

**How listings work.** Brokers list space on the owner's behalf. The landlord decides what build-outs stay after filming; the software records that decision in the agreement and documents condition with before-and-after photos. Finding space as an independent producer today is slow and fragmented, and Interim is built to fix that.

**What the software adds for this brand:** a production-space filter on the site finder (clear height, column spacing, power, loading, parking for trucks, vacancy), a license agreement template with restore-or-keep terms, before-and-after condition photos, the production's insurance certificate, and a film-credit estimate next to the real estate incentives.

**Market risk.** Chicago spending is at a record, but anchor shows like The Bear and The Chi are wrapping, and no stage occupancy data is published. [source](https://www.axios.com/local/chicago/2026/04/08/illinois-film-tax-credits-chicago-production-the-bear-chi) Talk to working producers before building this module.

### Pop-up shops

Pop-up retail runs on the same engine: a vacant or underused storefront, a short-term license, a broker listing it for the owner, and condition tracking before and after. Chicago has had dedicated pop-up licenses since 2019, and they are cheap and fast. [source](https://perkinscoie.com/en/news-insights/chicago-city-council-approves-pop-up-shop-licensing.html)

**Chicago pop-up licenses** [source](https://www.chicago.gov/city/en/depts/bacp/supp_info/popupusefaq.html)

| License | Who applies | Terms and fees |
| --- | --- | --- |
| Pop-up user, retail (Tier I): general goods and packaged shelf-stable food | The pop-up business | 5 days $25, 30 days $50, 90 days $75, 180 days $100, 1 year $150 |
| Pop-up user, food (Tier II shared-kitchen food, Tier III cooked onsite) | The pop-up business | 5 days $50-150 up to 90 days; max 90 days a year at one location |
| Food host (Tier II) | Property owner or host | 1 year, $150; hand sink and temperature control required |
| Food host (Tier III) | Property owner or host | 1 year, $330; restaurant equipment and inspection required |

- The user license moves with the business, so one license covers different sites during its term (one location at a time).
- Retail-only hosts need no license but must confirm their users are licensed and keep records.
- **Zoning:** pop-ups are not allowed in R or M districts, so this works on B, C, and D corridors.
- **Signs:** window signs under 25% of each pane, or vinyl signs up to 60 days, need no sign permit.

**City support.** Chicago's Storefront Activation Program funds community organizations to fill vacant corridor storefronts with pop-ups; in early 2024 the city awarded about $2 million to 15 groups. [source](https://chicago.gov/city/en/sites/bacp-recovery-plan/home/news-updates/2-million-grants.html) [source](https://blockclubchicago.org/2024/01/04/15-neighborhood-groups-get-city-grants-to-launch-pop-ups-in-empty-storefronts/) Those organizations are natural partners and early users: they already negotiate short-term leases with landlords.

**What the software adds for pop-ups:** a storefront filter on the site finder (B/C/D zoning, ground-floor commercial, vacancy signals, foot traffic and transit nearby), a short-term license agreement template, a check that the user holds the right pop-up license tier, and a path from pop-up to permanent lease when a tenant does well.

## Validation, pricing, and go-to-market

Price the first release between Chicago Cityscape and the national design tools, and prove it on your own deals before selling it.

**What comparable tools charge**

| Tool | Price | What it does |
| --- | --- | --- |
| Chicago Cityscape | $1,375/year | Chicago property data, permits, zoning, land sales |
| Zoneomics | $92-279/month | Zoning lookups, national |
| PropStream | $99-699/month | Distressed lead lists, skip tracing |
| DealMachine | About $99-279/month | Driving-for-dollars app, owner outreach |
| TestFit | $1,250+/month | Automated building layouts and yield |

Sources: [Cityscape](https://www.chicagocityscape.com/vs/siteselection), [Zoneomics](https://www.zoneomics.com/pricing/zoning-search), [PropStream](https://www.propstream.com/news/how-much-does-propstream-cost), [DealMachine](https://resimpli.com/blog/dealmachine-pricing/), [TestFit](https://pricingsaas.com/companies/testfit)

**Proposed pricing** (to test, not final)

| Plan | Price | Includes |
| --- | --- | --- |
| Broker | $149/month or $1,490/year | Site finder, feasibility, deal list, PDF exports |
| Team | $399/month | Up to 5 users, shared deals, phase 2 modules as they ship |
| Project modules | Per active project per month | Entitlement, budget, draw, construction tracking |
| Network listing | Monthly subscription for boutique companies | Profile, project listings, investor introductions; flat fee only |

**Validation steps**

1. Run 10 real Chicago parcels through the feasibility screen by hand with your team and your partner contractor. Note every question you had to answer outside the tool.
2. Build version 1 and use it on your own deals for a month.
3. Show it to 10 Chicago brokers and small developers from your network. Ask what they'd pay and what's missing.
4. Sign 3-5 paying users before building phase 2.

**Where to find users:** your sponsoring brokerage and its agents, Chicago Association of Realtors events, small developer groups, community banks that lend on 2-6 flats (they want better feasibility from borrowers), and architects who do self-certification.

**Trust builders for a new company:** show the source and date on every number, publish case studies from your own projects, and let users report errors and see them fixed.

## Decisions (recommended)

These are recommended answers to the open product questions from the planning conversation. Each can be changed. Market scope is Illinois only for now, starting in Chicago.

| Question | Recommendation | Why |
| --- | --- | --- |
| Who buys, owner or operations person? | The owner or principal pays; the operations person or broker uses it daily | Owners control the budget; daily users decide whether it sticks |
| Build it yourself or bring in a partner? | Build the first version yourself with Claude; bring in a technical partner or contract developer before selling to outside customers | Fast and cheap to prove the idea; outside customers need security, uptime, and data licensing done properly |
| Which handoff to fix first? | Finding a site to feasibility, then construction to management | The first is where money is committed; the second is where information is lost |
| Other tools to connect | QuickBooks for accounting; export to AppFolio or Buildium for property management; MRED for listings | These are the common small-company tools |
| MRED data access | Ask your brokerage whether it has an IDX or RESO Web API feed; plan for a vendor license before selling | Each outside brokerage can also connect its own MRED account |
| Site-finder signals to rank first | City-owned lots, vacant land, vacant-building complaints and violations, tax delinquency, then MLS listings | Ordered from free and reliable to paid or licensed |
| Zoning districts to support first | RT-4, RM-4.5, RM-5, B2-2, B2-3, B3-2, C1-2 | These cover most 2-6 flat and small mixed-use sites |
| Investors: local or national? | Chicago-first, open to anyone | Local investors know the neighborhoods; national ones add capital later |
| Investor listings | Both company profiles and project listings | Already in the investor network section |
| Product names | 25x125 for the main product; Interim for the short-term space brand (film and pop-ups) | 25x125 is the standard Chicago lot; Interim fits both productions and pop-ups better than the earlier working name, Backlot. A web search found no obvious product conflict, but a formal trademark and domain search is still needed |
| One brand or two for short-term space? | One brand (Interim) with film and pop-up tracks, kept separate from 25x125 | Same engine, different audience; kept apart from 25x125 under the brand rules |
| Pop-up to permanent lease | Yes, with a one-click path to a standard lease and the broker earning the commission | Turns short-term income into long-term tenants and fees |
| Permanent stages | Model both build-and-lease and own-and-operate | Already in the film section |
| File formats for the planner | Import PDF, DWG/DXF, and IFC; export PDF, DXF, IFC, and CSV | Covers architects (AutoCAD, Revit via IFC), contractors (PDF), and lenders (CSV) |
| Existing floor plans for rehabs | Phone room scan (iPhone LiDAR) first, tracing over old PDF drawings second, manual entry last | Fastest to most accurate |
| Cost tracking | Log every job's hard costs by the standard construction division codes (CSI MasterFormat) | Makes your costs comparable job to job and usable in the planner |
| Partner contractor conversation | Yes, within two weeks | Ground-up pain points shape phase 2 |
| One-page concept for your dad | Yes, after the screen mockups | A picture of the product gets better feedback than a description |
| Next step | Mock up the four first-release screens, then take the Chicago Cityscape trial and compare | Shows the product and tests it against the main competitor |

**Chicago Cityscape trial: what to test**

1. Look up 10 parcels you know well, including one in a 606/Pilsen district and one historic building.
2. Check whether it says how many units zoning allows on each.
3. Check whether it shows parking requirements under the 2025 transit rules.
4. See how it finds vacant land and city-owned lots.
5. Check tax-sale and foreclosure coverage.
6. Look for any cost or pro forma estimate.
7. Look for incentive values in dollars.
8. Test map and list search together.
9. Try exporting a parcel report.
10. Note everything you still had to do in a spreadsheet.

## Open questions to verify

Sources are linked next to each fact above. These items were uncertain in the research and should be confirmed before the software relies on them.

**Zoning and code**

- [x] Lot area per unit in B and C districts by suffix (-1 through -5)
- [ ] New-construction window glazing percentage, corridor widths, and travel distances in the 2026 code (ordinance SO2026-0024930)
- [ ] 2026 Affordable Requirements Ordinance in-lieu fee table
- [ ] Status of the state parking law overlay ordinance proposed in June 2026
- [ ] Coach house size limits under the permanent ADU ordinance
- [ ] How sound stages are classified under Chicago's building code amendments

**Costs and fees**

- [ ] 2026 Water Management and CDOT fee schedules (2025 versions used)
- [ ] Residential construction factors in the permit fee table
- [ ] Chicago-specific soft cost percentages
- [ ] Construction loan rates from local community banks

**Incentives**

- [ ] Treasury certification of Illinois' 2027 Opportunity Zone tracts
- [ ] Which 13 TIF districts expire at the end of 2026
- [ ] Whether the Illinois Affordable Housing donation credit was extended past 2026
- [ ] Whether residential projects qualify for the Enterprise Zone materials exemption
- [ ] Whether set construction and stage rental appear on the Illinois Film Office's qualified expenditures list

**Legal and market**

- [ ] Outcome of the Protecting Renters and FAIR ordinances
- [ ] Timing of the delayed Cook County tax sale (deadline December 1, 2026)
- [ ] Any new SEC finder or exempt-offering rules (targeted for October 2026)
- [ ] Securities attorney review of the investor network model
- [ ] Trademark and domain checks for the product names

**From you**

- [ ] Take a Chicago Cityscape free trial and run 10 of your own parcels through it
- [ ] 20-minute conversation with your partner contractor about where ground-up projects slow down
- [ ] Start logging hard costs per job in a consistent format
