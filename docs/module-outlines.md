# 25x125 Module Outlines

2026-10-28 · Marlon

One outline per module of the Illinois development pipeline plan, in build order.

## How to read these outlines

Every module follows the same outline so they can be compared and built in order. All modules read and write one shared parcel record; the last section covers the platform pieces they share.

**Fields in every outline**

- **Job:** the one question or task the module handles.

- **Users:** who uses it daily and who pays.

- **Inputs:** data it reads, from public feeds, other modules, or imports.

- **Version 1 features** and **later features.**

- **Screens.**

- **Illinois rules it must encode,** with Chicago first.

- **Outputs:** what it hands to the next module or exports.

- **Success measure:** how we know it works.

- **Open questions.**

**Build phases**

| Phase           | Modules                                                 |
|-----------------|---------------------------------------------------------|
| 1               | Site finder, Feasibility screen                         |
| 2               | Layout and cost planner, Entitlement and permit tracker |
| 3               | Budget and draw manager, Construction tracker           |
| 4               | Handoff and asset record, Sale and lease-up             |
| 5               | Investor network                                        |
| Separate brands | Interim (film and pop-up space), Wholesale tools        |

Geography for every module: Chicago first, then the Cook County suburbs, then Lake County, then McHenry County, then the rest of Illinois.

## Module 1 · Site finder (phase 1)

**Job:** show every parcel in the market worth a closer look, ranked by what could be built there and whether it pays.

**Users:** brokers and small developers search daily; the owner or principal pays.

**Inputs**

- Cook County Assessor: parcel universe (class codes for vacant land), sales, assessed values, neighborhood codes.

- Chicago Data Portal: zoning, permits, building violations, 311 vacancy complaints, scofflaw list, demolition notices, city-owned land, TIF and Enterprise Zone boundaries, historic ratings.

- Transit: CTA and Metra stations for transit-served areas.

- Paid or licensed, added per customer: MLS (MRED) listings, foreclosures and tax delinquency (ATTOM or PropStream).

- Imports: lists from BatchLeads, PropStream, DealMachine, or any CSV.

**Version 1 features**

- Map and results list side by side, like MRED search.

- Filters: area, zoning district, lot size, project type, distress signals, city-owned, transit-served, TIF, Opportunity Zone, listed on MLS.

- Development score per parcel, with the reasons behind the score shown.

- Saved searches with alerts when a new parcel matches.

- Save a parcel to the deal list.

- Owner of record and tax-bill mailing address.

**Later features**

- Mobile drive-and-tap: tap a building on the street and get its parcel page.

- Built-in skip tracing and mail, or deeper links to outside tools.

- Filters for production space (clear height, loading) and pop-up storefronts, shared with Interim.

**Screens:** search (map and list), saved searches, parcel quick view.

**Illinois rules:** outreach follows TCPA (calls and texts) and CAN-SPAM (email); broker advertising follows the Illinois license law; MLS data follows MRED license terms, with no scraping.

**Outputs:** a saved parcel, sent to the feasibility screen and the deal list.

**Success measure:** users find at least one parcel a month worth running feasibility on that they would not have found otherwise.

**Open questions**

- How to weight the development score: zoning upside, distress, price gap, or user-set.

- Whether the brokerage's MRED feed can be used for the first version.

## Module 2 · Feasibility screen (phase 1)

**Job:** for any parcel, answer four questions: what can I build, what will it cost, what incentives apply, and does it make money.

**Users:** brokers, developers, and lenders reviewing a borrower's deal; the owner or principal pays.

**Inputs**

- The parcel record from the site finder.

- Zoning rules engine: units, floor area, height, parking, and approval paths per district.

- Neighborhood comparables: land sales, building sales, and rents from the parcel's Assessor neighborhood, widened to the community area when sales are thin.

- Cost base: published Chicago ranges, then the user's own job costs.

- Incentive layers: TIF, Opportunity Zone tracts, Enterprise Zones, census tracts, historic status, Cook County tax classes.

**Version 1 features**

- Scenarios side by side: by right, with an ADU, with an administrative adjustment, with a rezoning.

- Cost breakdown: land, hard, sprinklers, soft, permit fee, financing and carry.

- Code thresholds each scenario crosses (sprinklers at 4+ units, second stair above 3 stories, Certificate of Occupancy at 4+ units, accessibility at 4+ units).

- Exit switch: build and sell (profit, return on cost, max land price) or build and hold (net operating income, yield on cost, value).

- Incentives shown at maximum value with toggles for what applies to the user, math visible.

- Every number shows its source, date, and comp count, and every cost shows as a dollar figure with dollar margins, such as \$1,375,000 (-\$275,000 / +\$413,000). Margins are set at -20% / +30% at feasibility and narrow to about 5% either way with sub bids. Every number is editable.

- One-page PDF export.

**Later features**

- Sensitivity sliders (cost, price, rate).

- Lender-ready packages.

- Scenario sync with the layout planner.

**Screens:** feasibility (scenarios, cost, result, incentives), comps drawer, assumptions editor.

**Illinois rules:** Chicago zoning (RS, RT, RM, B, C districts first), the 2025 parking ordinance and state parking law, ADU rules, ARO trigger at 10+ units, Cook County assessment and tax classes, Chicago and Illinois transfer taxes, building permit fee formula. Suburban and county rules load per municipality as each market opens.

**Outputs:** a chosen scenario on the deal, sent to the layout planner, entitlement tracker, and budget.

**Success measure:** feasibility results land within 10% of the real outcome on users' completed projects.

**Open questions**

- Default return target for max land price (15% return on cost used in the mockups).

- Which B and C district lot-area figures still need checking against the code.

## Module 3 · Layout and cost planner (phase 2)

**Job:** let users lay out units on the real lot, grid by grid like RimWorld or Prison Architect, and see live whether each room meets code and what the building costs.

**Users:** developers and brokers testing options; architects and contractors who pick up the file.

**Inputs**

- Buildable envelope from the zoning engine (setbacks, height, floor area).

- Code rules engine: room sizes, ceiling heights, kitchen aisles, light and ventilation, exits and stairs, fire ratings by distance to the lot line, porches, make-up air.

- Cost data from the feasibility screen, editable.

- Existing floor plans for rehabs: phone room scan, traced PDF drawings, or manual entry.

- Imports: PDF, DWG/DXF, IFC.

**Version 1 features**

- Grid canvas over the lot, floor by floor.

- Drag rooms, stairs, porches, and walls; each turns green or red against code with the reason.

- Running cost total by category.

- Side-by-side options with cost against rent or sale value (second bath, in-unit laundry, coach house, extra floor). The planner shows numbers and makes no recommendation.

- Suggested cost moves: stay at 3 units to skip sprinklers, stay at 3 stories for one wood stair, rear porch as second exit, stacked kitchens and baths, one repeated unit plan.

- Export: PDF, DXF, IFC, CSV.

**Later features**

- Gut rehab mode starting from an existing plan.

- 3D massing view.

- Construction-division cost breakdown feeding the budget module.

**Screens:** lot canvas, room palette, code check panel, cost panel, options compare.

**Illinois rules:** Chicago Building Code with the 2026 update (mandatory for permits from December 1, 2026). An Illinois-licensed architect must prepare and stamp permit drawings for any 3+ unit, mixed-use, or ADU project, so the planner produces a starting design only. Suburbs use their own adopted codes, loaded per town.

**Outputs:** unit mix, floor area, and cost estimate back to feasibility; a starting file for the architect.

**Success measure:** an architect accepts the exported layout as a starting point without redrawing it from scratch.

**Open questions**

- Confirm new-construction window percentages, corridor widths, and travel distances in the 2026 code text.

- Which file format architects you work with prefer.

## Module 4 · Entitlement and permit tracker (phase 2)

**Job:** get a project from "zoning allows it" to "permit in hand" with every filing, hearing, comment, and deadline in one place.

**Users:** the project manager or developer; the architect and expediter as collaborators.

**Inputs**

- Approval path from the feasibility scenario (adjustment, variation, special use, rezoning, permit only).

- Ward, alderperson office, and community process for the parcel.

- Permit path choice: Express, Self-Certification, Standard Plan Review, Developer Services.

- Live status from the city's permit data where available.

**Version 1 features**

- Checklist per approval path, generated from the rules (rezoning: notice to owners within 250 ft no more than 30 days before filing, DPD filing, committee hearing, Council vote).

- Deadlines and reminders for notices, hearings, and permit expirations.

- Reviewer comment log with responses and resubmission rounds.

- Demolition checklist (asbestos survey, health department notice, sewer and water disconnects, rodent baiting, Department of Housing sign-off, historic hold, 606/Pilsen surcharge).

- Utility applications: water tap, ComEd, Peoples Gas, CDOT public-way permits.

- Fees paid, by item.

**Later features**

- Ward-by-ward history of past zoning decisions.

- Document templates for notices and narratives.

- Suburban permit portals, one town at a time.

**Screens:** approvals timeline, checklist, comments, fees.

**Illinois rules:** Chicago zoning approval steps and fees, Department of Buildings permit paths, demolition requirements, the 2026 construction code date. Suburban towns and Lake and McHenry counties each add their own process.

**Outputs:** permit issued, conditions of approval, and final drawings set, sent to the construction tracker.

**Success measure:** fewer resubmission rounds and no missed notice or hearing deadlines.

**Open questions**

- Whether the city's newer permit system exposes status data the tracker can read.

- How expediters on your projects want to share updates.

## Module 5 · Budget and draw manager (phase 3)

**Job:** keep the budget, lender, and title company in sync so every draw goes out complete and on time.

**Users:** the owner or developer and their project manager; the GC submits pay applications; lenders and title companies receive packages.

**Inputs**

- Budget from the chosen feasibility scenario, by line item and construction division.

- Loan terms: amount, rate, loan-to-cost, interest reserve, retainage.

- GC pay applications, sworn statements, and lien waivers from subs and suppliers.

- Change orders from the construction tracker.

**Version 1 features**

- Budget vs. committed vs. paid, by line.

- Draw builder: pay application, owner's and GC's sworn statements, waiver checklist per listed sub and supplier, inspector sign-off.

- Missing-waiver alerts before the package goes to the title company.

- Retainage held and released.

- Lien deadline calendar.

- Draw package export (PDF bundle).

**Later features**

- Lender and title company portal access.

- Electronic waiver collection from subs.

- QuickBooks sync.

**Screens:** budget, draw builder, waiver tracker, loan summary.

**Illinois rules:** Mechanics Lien Act (sworn statement before payment, GC lien within 4 months of completion against lenders and buyers, sub notice within 90 days); state retainage caps don't apply to buildings of 12 or fewer units but do apply to small commercial; Chicago title-escrow draw practice.

**Outputs:** funded draws, paid amounts, and final waivers, sent to the handoff record.

**Success measure:** no draw is held up by a missing document.

**Open questions**

- Which title companies and lenders you work with, to match their package formats.

- Whether subs will sign waivers electronically.

## Module 6 · Construction tracker (phase 3)

**Job:** run the build day to day so schedule, inspections, changes, and money stay tied together.

**Users:** the project manager and site super daily; the GC and subs as collaborators; the owner reviews.

**Inputs**

- Permit, conditions, and drawings from the entitlement tracker.

- Budget lines from the budget module.

- Company directory: GC, subs, suppliers, with licenses and insurance.

- City inspection wait times.

**Version 1 features**

- Schedule with inspections built in (underground, rough, final by trade), using the city's current wait time.

- Inspection requests and results; alert before a permit suspends for a missed inspection.

- Change orders with cost and schedule impact, flowing to the budget and sworn statements.

- Daily logs and photos, tagged by unit and room.

- License and insurance expiration alerts for every sub.

- Punch list started early, by unit.

**Later features**

- Sub and supplier ratings from past jobs.

- Phone app for field crews.

- Weather and delivery scheduling.

**Screens:** schedule, inspections, change orders, daily log, directory.

**Illinois rules:** Chicago GC license classes (A-E by project value; most 2-6 flats need C or D); separate city licenses for plumbing, electrical, and masonry; Illinois roofing license; inspection sequence and permit suspension rules.

**Outputs:** completed inspections, approved change orders, photos, and punch items, sent to the handoff record.

**Success measure:** no change order reaches the lender without being in the budget, and no inspection is requested late.

**Open questions**

- Which features from Contractor Foreman your team would miss, and which you'd drop.

- Whether field crews will use a phone app or need a simpler text-based check-in.

## Module 7 · Handoff and asset record (phase 4)

**Job:** turn a finished build into one complete record that follows the building to whoever manages, finances, or buys it.

**Users:** the owner and property manager; buyers, lenders, and investors receive the package.

**Inputs**

- Final inspections, Certificate of Occupancy status, and as-built drawings.

- Final waivers, sworn statement, and retainage release from the budget module.

- Photos, punch list, and change orders from the construction tracker.

- Warranties and equipment details entered at closeout.

**Version 1 features**

- Closeout checklist: finals by trade, Certificate of Occupancy when required, punch sign-off by unit, final waivers, retainage release, warranties, as-builts, equipment list, utility transfers, Assessor new-construction report.

- Warranty and equipment register with expiration alerts.

- Building history: every permit, inspection, change, and photo from the project.

- Handoff package export for buyers or a property manager.

- Export to AppFolio or Buildium.

**Later features**

- Maintenance schedules from equipment data.

- Tenant-facing manuals per unit.

**Screens:** closeout checklist, asset register, building history.

**Illinois rules:** Certificate of Occupancy required in Chicago for 4+ new units, over 10,000 sq ft non-residential, or a change of occupancy; Cook County assesses new buildings in proportion to completion and can bill omitted assessments, so the Assessor's new-construction form is on the checklist. Lake and McHenry assess differently and load later.

**Outputs:** a complete asset record, sent to sale and lease-up and to investor profiles.

**Success measure:** a buyer's or lender's due diligence can be answered from the package alone.

**Open questions**

- Which property management software your family company and partners use.

## Module 8 · Sale and lease-up (phase 4)

**Job:** get the finished building sold or leased on the terms the feasibility screen assumed, and track the gap if it isn't.

**Users:** the listing broker and owner; leasing agents; buyers' brokers receive packages.

**Inputs**

- Exit plan and assumptions from the feasibility scenario.

- Asset record and handoff package.

- MLS data for pricing and listing (through the user's MRED access).

- Lease terms and rent roll.

**Version 1 features**

- Exit tracker: assumed vs. actual sale price, rents, days on market.

- Listing package built from the handoff record.

- Rent roll with lease dates, notice deadlines, and deposit interest due.

- Lease checklist with required Chicago disclosures.

- Transfer tax and closing cost estimates on a sale.

**Later features**

- Tenant screening and applications through partners.

- Feedback loop: actual results improve the next feasibility estimate for that neighborhood.

**Screens:** exit tracker, listing package, rent roll.

**Illinois rules:** Chicago Residential Landlord and Tenant Ordinance (owner-occupied buildings of 6 or fewer units exempt), 2026 deposit interest rate and required summary attachment, Fair Notice periods (60 and 120 days), short-term rental registration and caps, Chicago, Cook County, and Illinois transfer taxes. Watch the pending Protecting Renters and FAIR ordinances.

**Outputs:** closed sale or stabilized rent roll; actual results returned to feasibility; track record to investor profiles.

**Success measure:** users can compare projected and actual returns on every finished project.

**Open questions**

- Whether listing should integrate with MRED directly or export a listing file.

## Module 9 · Investor network (phase 5)

**Job:** let investors find small boutique developers and their projects, with track records built from real project data. Networking and listing only; no money moves through the platform.

**Users:** boutique companies pay a flat subscription to list; investors browse free at first.

**Inputs**

- Completed and active projects from the pipeline modules (budgets hit, schedules, entitlements won, exits).

- Feasibility summaries and incentive values for listed projects.

- Census-tract data (income, poverty rate, qualified-tract status) for neighborhood context.

**Version 1 features**

- Company profiles with a verified track record pulled from the pipeline.

- Project listings with feasibility summary, incentives, and capital sought.

- Search by any field, with map and list together like MRED.

- Introduction requests; everything after happens off-platform.

- Your own projects as the launch profiles.

**Later features**

- Paid investor tier: saved searches, alerts, deeper data.

- Partnership with a registered funding portal for small-investor raises.

**Screens:** investor search, company profile, project listing, introduction inbox.

**Illinois and federal rules:** no success fees or pay tied to whether a deal closes or how much is raised; no handling of funds; no ranking deals as good investments. Rule 506(b) raises can't be listed publicly; 506(c) raises can advertise but accept only verified accredited investors. Illinois has no finder exemption. Property sales (real estate license) stay separate from selling project shares (securities). A securities attorney reviews the model before launch.

**Outputs:** introductions between investors and boutique companies.

**Success measure:** listed companies get introductions that turn into funded projects, reported by the companies.

**Open questions**

- Watch for SEC finder and exempt-offering rules (targeted for October 2026).

- Subscription price for boutique companies.

## Module 10 · Interim: short-term space (separate brand)

**Job:** turn vacant or underused space into short-term income by licensing it to film productions and pop-up shops, and help convert buildings into permanent stages.

**Users:** brokers list space on owners' behalf; producers, location managers, and pop-up businesses search; landlords approve terms.

**Inputs**

- Site finder data filtered for vacancy, storefronts, and production-ready buildings (clear height, column spacing, power, loading, truck parking).

- Zoning: pop-ups only in B, C, and D districts; production uses mostly in M and C districts.

- Owner terms: dates, allowed uses, restore-or-keep rules, price.

**Version 1 features**

- Listings with photos, specs, availability, and price, searchable by map and list.

- Two tracks: film (one-off sets and permanent stage projects) and pop-ups.

- License agreement template with restore-or-keep terms the landlord sets.

- Before-and-after condition photos.

- Required documents: production's insurance certificate (Chicago Film Office requires \$1M liability naming the city for street use); pop-up user's license tier.

- Film credit estimate shown next to real estate incentives.

- One-click path from a successful pop-up to a permanent lease.

**Later features**

- Permanent stage feasibility (build and lease vs. own and operate).

- Partnerships with community groups running city storefront-activation grants.

**Screens:** space search, listing page, booking and agreement, condition report.

**Illinois rules:** Illinois film credit (35% base since SB 1911, stackable extras, \$50,000 or \$100,000 minimum spend); Chicago filming permits only for street, sidewalk, or alley use; Chicago pop-up licenses (\$25 for 5 days up to \$150 a year for retail; food tiers limited to 90 days a year per location); broker commission rules for placements.

**Outputs:** license income for owners, commission for brokers, and leads for permanent tenants.

**Success measure:** listed spaces earn license income during vacancy, and some placements convert to permanent leases.

**Open questions**

- Confirm whether set construction and stage rental count toward the film credit.

- Which producers and pop-up operators will test it first.

## Module 11 · Wholesale tools (separate brand)

**Job:** help wholesalers and investors find off-market distressed properties, reach owners, price deals fast, and pass contracts to buyers, while staying inside Illinois license law.

**Users:** wholesalers and small investors; they pay a subscription plus usage for lists and outreach.

**Inputs**

- Distress signals from the site finder: vacancy complaints, violations, scofflaw list, tax delinquency, foreclosure and probate data (paid feeds).

- Neighborhood comps for after-repair value.

- Rehab cost ranges from the cost base.

- Imported lists from BatchLeads, PropStream, or CSV.

**Version 1 features**

- Distressed lead scoring by neighborhood.

- Quick after-repair value and rehab estimate from local comps.

- Owner outreach log, with mail and skip tracing through partners.

- Buyer list and deal sharing.

- Assignment counter with an Illinois license warning.

**Later features**

- Built-in dialer and mail.

- "Development upside" flag that sends a lead to 25x125 feasibility, kept invisible to wholesale users unless they also subscribe to 25x125.

**Screens:** lead search, deal analyzer, outreach log, buyer list.

**Illinois rules:** dealing in assignable purchase contracts or options 2 or more times in 12 months counts as brokerage and needs a license; TCPA and CAN-SPAM for outreach; MLS terms for any listing data.

**Outputs:** assigned contracts or deals passed to buyers.

**Success measure:** users close assignments with fewer dead leads than with national list tools.

**Open questions**

- Brand name.

- Whether to build skip tracing or partner for it.

## Shared platform pieces

These are built once in phase 1 and used by every module and brand. The brand architecture diagram is in the [main plan](https://claude.ai/artifact/P5vJ5Cgu14bcMuijpGP1y5).

| Piece                 | What it does                                                                                                                                                           | First needed by         |
|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|
| Parcel record         | One record per property (PIN, zoning, overlays, owner, history) that every module adds to                                                                              | Site finder             |
| Data feeds            | Nightly pulls from the Chicago Data Portal and Cook County Assessor; licensed feeds (MLS, foreclosures) per customer; suburban and county sources as each market opens | Site finder             |
| Rules engine          | Zoning, building code, and incentive rules stored per municipality and county, each with a source and effective date                                                   | Feasibility screen      |
| Cost and comps base   | Published cost ranges, neighborhood comparables, and each user's own job costs (logged by construction division)                                                       | Feasibility screen      |
| Accounts and brands   | One account system behind every brand; each brand has its own name, site, pricing, and data visibility                                                                 | All                     |
| Teams and permissions | Owners, staff, architects, contractors, lenders, and investors see only what they're given                                                                             | Construction tracker    |
| Imports and exports   | CSV, PDF, DWG/DXF, IFC in and out at every step; QuickBooks, AppFolio, and Buildium connections later                                                                  | All                     |
| Documents             | Generated PDFs (one-pagers, draw packages, handoff packages, agreements)                                                                                               | Feasibility screen      |
| Audit trail           | Who changed what number and when, so lenders and investors can trust the history                                                                                       | Budget and draw manager |
| Alerts                | Deadlines, expirations, new matching parcels, missing documents                                                                                                        | Site finder             |

**Build order for the platform:** parcel record and data feeds, then the Chicago rules engine, then costs and comps, then documents and exports. Everything else arrives with the module that first needs it.
