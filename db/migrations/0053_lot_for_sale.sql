-- Public land offered for sale: City of Chicago lots (City-Owned Land Inventory aksk-kvfp, the data behind
-- ChiBlockBuilder) and Cook County Land Bank Authority properties (its public ePropertyPlus feed).
create table lot_for_sale (
  source text not null,              -- 'city' or 'land_bank'
  source_id text not null,
  pin text,                          -- 14 digits, no dashes
  pin10 text,
  address text,
  status text,                       -- city: sales_status (Apply, Offered, Application(s) Received, ...); land bank: currentStatus
  for_sale boolean not null,         -- open to applications or offers now
  asking_price numeric,              -- land bank asking price
  minimum_bid numeric,               -- land bank minimum bid
  city_land_value numeric,           -- city's appraised land value (its sale price for most lots)
  lot_sqft numeric,
  property_type text,                -- land bank inventoryType; city application_use
  zoning text,
  deadline date,                     -- city application deadline
  offer_round text,
  apply_url text,
  comments text,
  listed_on date,
  lon double precision,
  lat double precision,
  geom geometry(Point, 4326),
  source_pull_id bigint references source_pull (id),
  primary key (source, source_id)
);
create index on lot_for_sale (pin10);
create index on lot_for_sale using gist (geom);
