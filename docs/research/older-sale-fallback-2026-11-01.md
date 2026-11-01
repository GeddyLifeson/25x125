# Sale value where no new-construction comps exist (2026-11-01)

## Problem

The comp engine searches rings out to 3 miles, then falls back to every new-construction sale in the city. On 2026-11-01 about 131,000 residential lots (class 2) had no kept comp sold in the last 3 years within 3 miles, mostly on the far South and Southwest Sides: Roseland 12,398, Ashburn 12,334, Auburn Gresham 9,641, West Pullman 9,363, Garfield Ridge 8,994, South Chicago 5,550. The citywide median put a South Chicago 3-flat at $468,000 a unit. The scorer counted 16,052 lots with a by-right 2-6 unit program on that fallback.

## Method

Older 2-6 unit buildings sell everywhere. `older_sale` holds 43,861 arm's-length sales since 2015 of class 211 buildings built before 2014 (`jobs/build_older_sales.py`).

1. Local older price: inverse-distance weighted median price per unit of older sales within 0.75 mi (else 1.5 mi) in the 3 years before the estimate date, moved to the estimate year with the FHFA metro index. At least 10 sales.
2. Curve: ln(new price per unit) = a + b ln(local older price per unit), fit on every kept comp against the older sales around it as of its sale date (`jobs/check_older_sales.py`, written to `data/rules/older_sale_fallback.json`).
3. Range: the 10th and 90th percentile of fit errors. When the local older price is outside the range the curve was fit on, the estimate is marked as an extrapolation and the range is widened 15% each way.

## Fit

| Curve | n | a | b | 80% range | Older price range fit on |
| --- | --- | --- | --- | --- | --- |
| Whole buildings | 191 | 4.8535 | 0.6471 | x0.742 to x1.274 | $93,177 to $518,513 |
| Condo units | 2,043 | 0.4652 | 1.0279 | x0.739 to x1.368 | $111,823 to $556,732 |

For buildings b is 0.65: a new building's price moves about 6.5% for each 10% move in older-building prices. New buildings cost about the same to build everywhere, so their prices spread less than older ones. Condo units track older prices one for one.

## Holdout (fit on comps sold before 2025-07-01, tested on later ones)

| Curve | n | Median error | Within 15% | Median ratio | COD |
| --- | --- | --- | --- | --- | --- |
| Whole buildings | 61 | 15.5% | 49% | 0.966 | 27.1 |
| Condo units | 222 | 16.5% | 45% | 0.922 | 19.3 |
| Comp rings, buildings (step 3 record) | 61 | 10.1% | 59% | 1.036 | 24.8 |

The comp rings stay the first choice wherever comps exist. The curve is the fallback for the citywide ring only; there it replaces a citywide median that has no local information at all.

## Where it lands

Sample of 2,000 lots with no comp within 3 miles, estimate date 2026-11-01:
- 1,866 (93%) get an estimate; 134 have fewer than 10 older sales within 1.5 mi and keep the "enter a sale price" message.
- 298 are extrapolations (older price under $93,177), mostly West Pullman, Roseland and East Side.

| Community area | Lots in sample | Local older price per unit | New-construction estimate per unit |
| --- | --- | --- | --- |
| Roseland | 174 | $91,596 | $208,295 ($131,372 - $281,219) |
| Ashburn | 164 | $156,680 | $294,809 ($218,748 - $375,587) |
| Auburn Gresham | 136 | $144,750 | $280,082 ($207,821 - $356,825) |
| West Pullman | 127 | $85,000 | $198,461 ($125,169 - $283,682) |
| South Chicago | 72 | $106,962 | $230,283 ($170,870 - $299,716) |
| Garfield Ridge | 125 | $222,500 | $369,918 ($274,479 - $471,276) |

## Limits

- Only 24 comps sit where the older price is under $110,000 (Woodlawn, Washington Park, North Lawndale). The curve's low end rests on them; residuals there average +9% (the curve runs slightly low).
- An area with no new construction may have none because new buildings don't sell there for what they cost. The estimate says what a new building would likely sell for, and the feasibility math shows whether that covers cost. It does not say anyone will buy.
