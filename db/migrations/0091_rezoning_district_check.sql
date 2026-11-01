-- Hand-check status of the districts read from the ordinance scans (data/reference/rezoning_districts_checked.csv).
-- model: the model's reading passed every free cross-check; confirmed / corrected: read by hand against the scan;
-- not_a_rezoning: the ordinance changes no district (e.g. a Pedestrian Street designation);
-- unresolved: flagged and not resolved by hand. Screens show districts only when this is model, confirmed or corrected;
-- for the other two the district columns stay empty.
alter table rezoning add column district_check text;
