-- Depth channels rolled up per lot (jobs.build_parcel_site): Assessor proximity, city footprints, tax-exempt
-- owners, and the newer signal kinds.

alter table parcel_site
  add column foreclosures_half_mile_5y integer,   -- Assessor proximity: foreclosure filings within half a mile
  add column nearest_new_construction_ft numeric, -- Assessor proximity: feet to the nearest new construction
  add column stories integer,                     -- tallest footprint on the lot (city file, last updated 2015)
  add column footprint_units integer,             -- units summed over the lot's footprints
  add column hearing_fines_3y numeric,            -- Buildings hearing fines imposed, last 3 years
  add column vacant_building_fine_due numeric,    -- vacant-building fines still owed
  add column environmental_hold text,             -- latest city environmental permit hold or LUST letter type
  add column foreclosed_rental_date date,         -- latest date a lender took title to a registered rental
  add column exempt_owner text;                   -- owner name when the PIN is tax-exempt
