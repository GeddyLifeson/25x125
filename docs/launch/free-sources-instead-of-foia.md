# Free sources instead of FOIA

Checked 2026-10-30, after Marlon decided to stop filing records requests. Each section covers one of the five requests: the best free route, what it has, how complete it is compared with the FOIA version, and what is still missing. Nothing here costs money. The one paid option found (the Treasurer's $250 tax sale list) is noted and not used.

## Summary

| FOIA request | Free route | Compared with the FOIA version |
| --- | --- | --- |
| 1. DOB permit applications | City building permits dataset (ydr8-5enu), already loaded | About 90%. Has review type, application date, issue date and days in review for every issued permit since 2006. Missing: applications still in review, withdrawn or denied, and dates of each correction cycle. |
| 2a. Zoning map amendments | City Clerk eLMS public API | Better than the FOIA version from 2010 on. 6,845 zoning ordinances with address, map number, dates and status, plus the ordinance, application and plans as PDFs. Missing: 2002-2009. |
| 2b. ZBA case log | Monthly ZBA agendas, minutes, decisions and signed resolutions (PDFs on chicago.gov) | About 95%. Case number, district, ward, applicant, address, relief and decision every month; votes are in the signed resolutions. Needs PDF parsing. |
| 2c. Administrative adjustments | None found | Gap. The city publishes no list. |
| 3. Treasurer tax sale lists | Delinquent list the Treasurer posts free before each Annual Tax Sale (next sale December 2026), plus the free per-PIN lookup | Full for the list, once it posts. Past results are online only for 2015-2017; 2009-2016 are on the county portal. |
| 4. Clerk recordings index | Assessor parcel sales (deeds), Sheriff and Judicial Sales Corporation foreclosure auctions, Assessor foreclosure counts | About 40%. Deeds and late-stage foreclosures are covered. Mortgages, liens and lis pendens filings are a gap. |
| 5. Land Bank inventory | Land Bank's public property viewer JSON feed | 100%, and better than FOIA: refreshed daily, with prices and bid deadlines. |

## 1. Permit applications (DOB)

**Source:** Chicago Data Portal, Building Permits, `ydr8-5enu`. We already load it (`jobs/load_permits.py`).

**What it has:** `review_type`, `application_start_date`, `issue_date` and `processing_time` (days) for every issued permit. Average days in review for permits issued since 2023 (pulled 2026-10-30):

| Review path | Permits | Average days |
| --- | --- | --- |
| Standard plan review | 15,530 | 106 |
| Self-certification | 11,249 | 44 |
| Express permit program | 71,725 | 11 |
| Direct developer services | 1,114 | 144 |
| Demolition | 2,470 | 20 |

**Missing compared with FOIA:**
- Applications that never issued (still in review, withdrawn, denied). Every row in the dataset has an issue date.
- The date of each correction letter or review cycle.

**Partial fill:** the ADU preapproval applications dataset (`j4h8-ug9m`) lists ADU applications before they issue. The city's per-permit status lookup shows one application at a time, which works for a parcel page and not for bulk.

**Verdict:** good enough for V1 permit timelines by review path and neighborhood. The FOIA would have added the slow and failed cases, which matter for risk but not for the median.

## 2a. Zoning map amendments (City Council)

**Source:** Office of the City Clerk eLMS public API, `https://api.chicityclerkelms.chicago.gov`. Free, no key, JSON.
- Search: `/search?search=Zoning Reclassification&size=100&skip=0` returns 6,990 matters (70 pages of 100), 6,845 of them ordinances.
- Detail: `/matter/<matterId>` returns actions (referred, passed, with dates and votes) and attachments.

**What it has, per matter:** record number (e.g. O2026-0029356), title with map number, address and application number (e.g. "Map No. 93-B at 1828 W Race Ave - App No. 23178T1"; the T1 suffix marks a Type 1 rezoning), introduction date, final action date, status (5,981 final, 671 introduced, 333 in committee), committee, sponsor and the action history.

**Attachments:** application, narrative and plans, the ordinance and the economic disclosure statement as PDFs. The ordinance states the old and new district (e.g. "RS-3 ... to those of an RT-3.5"). The PDFs are scans, so getting the districts out needs OCR. Tesseract is free.

**Coverage:** a few matters from 2007-2009, then complete from 2010. The FOIA asked for 2002 on.

**Older years:** DataMade's `chicago-council-scrapers` publishes a nightly SQLite of council matters from 2011, which is a backup copy of the same data. For 2002-2009 there is no free bulk source; the Council Journal of Proceedings PDFs have them, page by page.

**Verdict:** better than the FOIA version for 2010 on, because it includes the plans and the timeline of every step.

## 2b. Zoning Board of Appeals cases

**Source:** chicago.gov publishes four PDFs per monthly meeting under predictable names:
- `.../zlup/Administrative_Reviews_and_Approvals/Agendas/ZBA_<Mon>_<YYYY>_Agenda.pdf`
- `..._Minutes.pdf`, `..._Decisions.pdf`, `..._Map.pdf`
- Signed resolutions: `.../Publications/ZBAsignedresolutions/Resolutions_<DD><MON><YYYY>.pdf` (e.g. `Resolutions_18JUL2025.pdf`)

**What it has:** the July 2025 decisions PDF lists 67 cases. Each has case number (suffix S = special use, Z = variation, A = appeal), zoning district, ward, applicant, owner, address, relief requested and decision (approved, denied, continued). The text is selectable. Votes and findings are in the signed resolutions.

**Coverage:** minutes from mid-2014, resolutions back to 1982 per the ZBA page, and decisions for 2012-2014 and 2024-2025. The decisions PDFs alone don't cover every year, but the minutes do.

**Catch:** chicago.gov blocks scripted downloads from cloud servers. A browser downloads the files fine. A nightly job would need to run from a normal connection, or someone downloads the month's four files by hand (about 2 minutes a month).

**Verdict:** about as complete as the FOIA case log, with more detail. It needs a PDF parser.

## 2c. Administrative adjustments

No free source found. The city's administrative adjustments page has the application form and code sections only. Applicants mail notice to neighbors, but the city publishes no log. This is the one item with no free substitute. It matters least of the three: adjustments are small changes to setbacks and parking, mostly on single lots.

## 3. Tax sale and delinquency (Treasurer)

**The next Annual Tax Sale is set for December 2026** (delayed from August 2025 under Public Act 104-0460). Before each sale:
- The Treasurer posts the list of properties in the sale on its website, free, and runs it in community newspapers by township. In 2024 it covered 51,811 properties owing $207 million.
- The same list is sold as a download at cooktaxsale.com for $250 (plus $250 for special assessments and $100 for weekly removals). **That costs money; not used.**

**Free routes:**
1. Capture the posted list when it goes up before the December sale. The Treasurer's results page shows past lists by ward with PIN, taxpayer, address, taxes sold and class.
2. The Treasurer's per-PIN search (`yourpropertytaxoverviewsearch.aspx`) shows whether a PIN's taxes are delinquent or sold. That works on a parcel page lookup, not in bulk.
3. Old sales on the county portal: Annual Tax Sale `55ju-2fs9` and Scavenger `ydgz-vkrp` (last updated 2016), plus 2009-2011 sold, forfeited and no-bid PIN lists.
4. The Land Bank's 2022 scavenger bids layer is in its public viewer.

**Scavenger sale:** since a 2023 law it is held only when the County Board orders it. None is scheduled.

**Verdict:** the free list covers what the FOIA asked for, once the Treasurer posts it. Set a reminder to capture it in November or December 2026.

## 4. Recordings index (Clerk)

**The Clerk's recordings search** (`crs.cookcountyclerkil.gov`) is free to use one search at a time in a browser. It sits behind Cloudflare bot protection and blocks scripts, so it is not a bulk source, and we should not try to get around that.

**What covers part of it:**
- **Deeds:** Assessor Parcel Sales (`wvhk-k5uv`), already loaded. Every recorded sale has the document number, deed type (warranty, trustee, quit claim, deed in trust), buyer and seller names and price. This is the deed half of the index.
- **Foreclosure auctions:** the Judicial Sales Corporation (`tjsc.com/Sales/UpcomingSales`, plus completed and cancelled lists) posts every sale it runs free: sale date, case number, law firm, address, opening bid, sale amount and buyer. It runs most Cook County foreclosure auctions. The Sheriff's site (`foreclosure.ccsheriff.org` and `/previoussale`) lists the rest, with the same fields.
- **Foreclosure density:** the Assessor proximity data we loaded today has foreclosures within half a mile over 5 years for every parcel.
- **Area-level mortgages:** HMDA (free, from the CFPB) gives loan-level mortgage originations by census tract, not by parcel.

**Gap:** mortgages, liens, releases and lis pendens on a given PIN. Lis pendens is the early foreclosure signal; the auction lists catch the same properties 12-24 months later. No free bulk source exists. The county portal's Recorder extracts stop in March 2015.

**Verdict:** about 40% of the FOIA version. Deeds and auctions are covered; debt and early foreclosure are not.

## 5. Land Bank inventory

**Source:** the Land Bank's public property viewer runs on ePropertyPlus, with a public JSON feed:
`https://public-cclba.epropertyplus.com/landmgmtpub/remote/public/property/getPublishedProperties?json={"criterias":[]}&start=0&limit=2000&page=1`

**What it has (pulled 2026-10-30):** 938 properties, 828 in Chicago. Of the Chicago properties, 698 are vacant land, 82 homes, 41 commercial and 5 industrial. Each has PIN, address, lat/lon, status, lot square feet, asking price (74), minimum bid (824), neighborhood and comments with offer deadlines.

**Also free:** monthly acquisitions and sales reports (PDF, January 2022 to March 2026, with gaps), quarterly board reports, and a 2015 list of tax-delinquent and scavenger PINs.

**Verdict:** complete, current, and free. Nothing a FOIA would add.

## What this means for the build

- Free and ready to load when loaders are approved: Land Bank feed, eLMS rezonings, judicial sale lists.
- Free but needs PDF work: ZBA decisions and resolutions (text), rezoning ordinances (OCR).
- Free once posted: the December 2026 tax sale list.
- No free source: in-review permit applications, administrative adjustments, mortgages, liens and lis pendens.
