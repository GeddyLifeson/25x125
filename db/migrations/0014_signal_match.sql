-- How each signal record was tied to a lot: 'source pin', 'address', 'point in lot', 'nearest lot within 15 m'.
alter table parcel_signal add column match_method text;
