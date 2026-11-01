-- Latest foreclosure auction on the lot (parcel_signal kind 'foreclosure_auction') and public land for sale.
alter table parcel_site
  add column foreclosure_auction_date date,       -- latest sale date, past or scheduled
  add column foreclosure_auction_status text,     -- upcoming, completed or cancelled
  add column public_sale_source text,             -- 'city' or 'land_bank' when the lot is offered now
  add column public_sale_price numeric;           -- land bank asking price or minimum bid, else city land value
