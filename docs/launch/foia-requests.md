# Public records requests

Drafted 2026-10-30 from the channel audit (https://claude.ai/artifact/KDGRZ9tKEgCwC2cUYq5Ydg). Ready for Marlon to send in his own name.

## Status (2026-10-30)

| # | Office | How | Status |
| --- | --- | --- | --- |
| 1 | Chicago Department of Buildings | Email DOBfoia@cityofchicago.org (listed on the department's FOIA page) | Sent 2026-10-30. Follow-up sent: cancel if any fee applies |
| 2 | Chicago Department of Planning and Development | Email DPDfoia@cityofchicago.org (listed on DPD's FOIA page) | Sent 2026-10-30. Follow-up sent: cancel if any fee applies |
| 3 | Cook County Treasurer | Online portal https://foia.cookcountytreasurer.com/ (Marlon's account), category Tax Sale | Sent 2026-10-30 11:49, reference lHcL1CI0hwZwA10. No email channel; fees apply only to paper past 50 pages and are collected before copying, so nothing is charged without approval |
| 4 | Cook County Clerk | Email FOIA.ccclerk@cookcountyil.gov (listed on the Clerk's FOIA portal) | Withdrawn 2026-10-30 after a fee notice (FOIA 369D53A, $0.10 per index line). Use the Clerk's free online search instead |
| 5 | Cook County Land Bank Authority | Email Info@CookCountyLandBank.org (the only address on its site), asking them to forward if FOIA goes elsewhere | Sent 2026-10-30. Follow-up sent: cancel if any fee applies |

Commercial requests get 21 business days, so answers are due by about December 1, 2026.

## Before sending

- Check each office's fee schedule before sending. Marlon approves any fee first.

- Illinois FOIA (5 ILCS 140) gives a public body 5 business days to answer, with one 5-day extension.
- 25x125 will use the records in a paid product, so each request is a commercial request. Section 3.1 requires saying so. A commercial request gets 21 business days, and the body may charge for staff time. Each draft below says so.
- Send each request to the named department's FOIA officer. The City of Chicago takes requests through its online FOIA portal, one department per request. Cook County offices each list a FOIA officer on their own site.
- Ask for electronic files (CSV or Excel). Electronic copies are usually free or cheap; paper is not.
- Keep the response letters. Each dataset we load from them gets a row in `data/sources/datasets.csv` with the request date.

## 1. Chicago Department of Buildings: permit applications

**Why:** the portal lists issued permits only. Applications in review, and how long each review step took, give a real permit timeline per review path.

> Under the Illinois Freedom of Information Act, I request an electronic copy (CSV or Excel) of the following records of the Department of Buildings:
>
> For every building permit application for new construction, renovation or wrecking submitted from January 1, 2022 to the date of this request, including applications not yet issued, withdrawn or denied: application number, address, PIN if recorded, permit type, review type (for example standard plan review, self-certification, express), date submitted, date of each review cycle or correction letter, current status, and issue date if issued.
>
> If the system cannot produce review-cycle dates, please send the remaining fields. If an existing report or export covers most of these fields, that report is acceptable.
>
> This request is for a commercial purpose: the records will inform a property development analysis service that my company sells.
>
> Marlon Lee
> imarlonlee@gmail.com

## 2. Chicago Department of Planning and Development: zoning changes and ZBA cases

**Why:** the portal has today's zoning map only. Map amendments and ZBA results let the parcel page show what was approved nearby and how long it took. Asad Khan (University of Illinois, 2019) obtained map changes for 2002-2016 this way.

> Under the Illinois Freedom of Information Act, I request electronic copies (CSV or Excel) of the following records:
>
> 1. A list of zoning map amendments approved from January 1, 2002 to the date of this request: ordinance or application number, address or boundary description, prior district, new district, date introduced, date passed, and whether it was a Type 1 rezoning or a Planned Development.
> 2. The Zoning Board of Appeals case log from January 1, 2015 to the date of this request: case number, address, relief requested (variation or special use, with the section of the Zoning Ordinance), hearing date, decision, and vote.
> 3. Administrative adjustment applications from January 1, 2015 to the date of this request: application number, address, adjustment requested, decision and decision date.
>
> If any item exists only as scanned documents, please send the other items first and tell me the format of the rest.
>
> This request is for a commercial purpose: the records will inform a property development analysis service that my company sells.
>
> Marlon Lee
> imarlonlee@gmail.com

## 3. Cook County Treasurer: tax sale and delinquency lists

**Why:** the tax-delinquent score points (6) wait for a source. The portal's tax sale datasets were last updated in 2016.

> Under the Illinois Freedom of Information Act, I request electronic copies (CSV or Excel) of:
>
> 1. The list of PINs offered at the most recent Annual Tax Sale, with the tax year, amount offered and whether each PIN sold or was forfeited.
> 2. The list of PINs offered at the most recent Scavenger Sale, with the tax years delinquent and whether each PIN received a bid.
> 3. If it exists as a report, a current list of PINs in the City of Chicago with one or more unpaid tax years, with the tax years and amounts.
>
> This request is for a commercial purpose: the records will inform a property development analysis service that my company sells.
>
> Marlon Lee
> imarlonlee@gmail.com

## 4. Cook County Clerk, Recordings: bulk index

**Why:** mortgages, liens and lis pendens show debt and foreclosure starts. The free Recorder extracts on the county portal stop in March 2015. If the Clerk sells a bulk subscription instead, this request gets its terms and price.

> Under the Illinois Freedom of Information Act, I request an electronic copy (CSV or Excel) of the index of documents recorded from January 1, 2024 to the date of this request for property in the City of Chicago: document number, document type, recording date, PINs, and grantor and grantee names. I am not requesting document images.
>
> If the Clerk provides this index through a bulk data subscription or another program instead of FOIA, please send the program's terms and fees.
>
> This request is for a commercial purpose: the records will inform a property development analysis service that my company sells.
>
> Marlon Lee
> imarlonlee@gmail.com

## 5. Cook County Land Bank Authority: inventory

**Why:** land bank lots are a direct acquisition channel for small builders and are not on either data portal.

> Under the Illinois Freedom of Information Act, I request an electronic copy (CSV or Excel) of the Cook County Land Bank Authority's current property inventory in the City of Chicago: PIN, address, property type (vacant land or building), status (available, under contract, sold), and list price if set.
>
> This request is for a commercial purpose: the records will inform a property development analysis service that my company sells.
>
> Marlon Lee
> imarlonlee@gmail.com
