-- Old and new districts read from the scanned ordinance PDFs by jobs/extract_rezoning_districts.py.
-- AI output is data to check: each row keeps the model, the PDF it read and the date.
alter table rezoning
  add column district_changes jsonb,          -- every old -> new change in the ordinance, in order
  add column district_confidence text,        -- high, medium or low, as the model reported it
  add column district_model text,
  add column district_source_url text,
  add column district_extracted_on date;
