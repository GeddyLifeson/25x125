-- Split-zoned lots: the second district and its share of the lot (slivers under 2% ignored).
alter table parcel_site
  add column zone_class_2 text,
  add column zone_share_2 numeric;
