-- Indexes for the list screen's sorts (engine/parcels.py LOT_SORTS). Without them every page of the list sorted all
-- 600,000 scored lots: 0.6 to 4 seconds for the return, extra-units and lot-size sorts. With them a page takes
-- under 20 ms. The nightly jobs truncate and refill these tables, so the indexes stay.
create index if not exists parcel_score_return on parcel_score (return_on_cost_p25 desc nulls last, pin10);
create index if not exists parcel_score_upside on parcel_score ((by_right_units - coalesce(units_now, 0)) desc, pin10);
create index if not exists parcel_score_score_pin10 on parcel_score (score desc, pin10);
create index if not exists parcel_score_pin on parcel_score (pin);
create index if not exists parcel_site_lot_sqft on parcel_site (lot_sqft desc nulls last, pin);
drop index if exists parcel_score_score;
