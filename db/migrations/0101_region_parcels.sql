-- Regions outside Cook County. Source use codes differ by state, so each loader also writes a plain use group
-- that the shared builders read. Florida's tax roll says whether a parcel was vacant when it sold.
alter table parcel add column if not exists use_group text;  -- vacant, single, multi, condo, other
alter table sale add column if not exists vacant_at_sale boolean;
alter table sale add column if not exists date_precision text not null default 'day';  -- 'month' for Florida
alter table comp add column if not exists source text;
alter table land_sale add column if not exists basis text not null default 'sale';
