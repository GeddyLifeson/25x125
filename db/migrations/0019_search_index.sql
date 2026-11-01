-- Fast address prefix search for the search box.
create index if not exists parcel_address_prefix on parcel_address (address text_pattern_ops);
create index if not exists parcel_address_pin_prefix on parcel_address (pin text_pattern_ops);
