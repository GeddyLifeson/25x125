# Regions (markets outside Chicago)

One install serves one region: one database, one `REGION` setting (`core/region.py`). Chicago is the default
and keeps its rules in `data/rules/`. Every other region has a folder:

```
data/regions/<id>/
  region.json                 settings and data sources (below)
  rules/zoning_districts.csv  one row per zoning district the product covers
  rules/zoning_heights.csv    height limits
  rules/zoning_steps.json     ADU, parking, rezoning targets, flags
  notes.md                    what was read, what is uncertain, what is not covered
```

A rules file a region does not provide falls back to the shared copy in `data/rules/`.
Every rule row carries the code section, a source URL and the date it was checked (CLAUDE.md rules 1 and 2).

## region.json

```json
{
  "id": "tampa",
  "name": "Tampa",
  "state": "FL",
  "counties": [{"id": "hillsborough", "name": "Hillsborough", "fips": "12057", "dor_county_no": 39}],
  "city_filter": {"field": "PHY_CITY", "values": ["TAMPA"]},
  "center": {"lat": 27.95, "lon": -82.46, "zoom": 11},
  "fhfa_metro": "45294",
  "parcel_id_label": "Folio",
  "price_basis": "recorded sales",
  "zoning_layer": {
    "url": "https://.../FeatureServer/0",
    "zone_field": "ZONECLASS",
    "tested_on": "2026-11-17",
    "note": "what the layer is, who publishes it"
  },
  "overlay_layers": [{"kind": "historic", "url": "...", "name_field": "..."}],
  "permit_source": {"kind": "socrata|arcgis|ckan|none", "url": "...", "note": "..."},
  "disclaimer": "Estimates, not tax, legal, zoning or appraisal advice.",
  "sources": [{"what": "zoning code", "url": "...", "checked_on": "2026-11-17"}]
}
```

`price_basis` is `recorded sales` (Florida, Georgia) or `appraisal district values` (Texas, where sale prices
are not public). Screens label Texas prices as values, not sales, and use a wider range.

## zoning_districts.csv

```
district,match,lot_area_per_unit_sqft,min_lot_area_sqft,far,max_units,min_lot_width_ft,max_lot_coverage,section,source_url,verified_on
```

- `district`: the name shown on screen. `match`: space-separated codes exactly as they appear in the city's
  zoning GIS layer (`zone_field`).
- `lot_area_per_unit_sqft`: lot area needed per dwelling unit. For a single-family district use the minimum
  lot area. Where the code gives units per acre, convert: 43,560 / units per acre.
- `min_lot_area_sqft`: the smallest lot that may be built on (blank if none).
- `far`: floor area ratio. Where the code has no FAR, derive a ceiling from lot coverage x stories allowed
  and say so in `section` (for example "no FAR; 0.40 coverage x 2.5 stories").
- `max_units`: cap on dwelling units per lot regardless of lot area (1 for single-family districts, 2 for
  duplex districts; blank where density alone governs).
- `min_lot_width_ft`, `max_lot_coverage` (0-1): blank if none.

Cover the districts where 1 to 6 unit residential buildings can be built: single-family, duplex/two-family,
townhouse, low- and mid-density multifamily, and the mixed-use or commercial districts that allow housing.
Leave out industrial, planned developments and special districts; the engine reports those as "not covered".

## zoning_heights.csv

```
district,frontage_from_ft,frontage_to_ft,ground_floor_commercial,max_height_ft,section,source_url,verified_on
```
One row per district (`frontage_from_ft` 0, `frontage_to_ft` blank, `ground_floor_commercial` any) unless
the height depends on lot width. Height in feet; where the code counts stories, use 12 ft per story and say so.

## zoning_steps.json

```json
{
  "verified_on": "2026-11-17",
  "steps": [
    {"id": "adu", "rule": "plain-English rule",
     "params": {"units": 1, "by_district": ["RS-50", "RS-60"], "max_sqft": 950,
                "owner_occupancy": false, "approval": "permit only"},
     "section": "Sec. 27-...", "source_url": "..."},
    {"id": "parking", "rule": "...",
     "params": {"spaces_per_unit": {"default": 2, "RM-24": 1.5}}, "section": "...", "source_url": "..."},
    {"id": "rezoning", "rule": "...", "approval": "rezoning (City Council)",
     "targets": {"RS-50": ["RM-16"], "RS-60": ["RS-50", "RM-16"]}},
    {"id": "state_overrides", "rule": "state laws that change what the city code allows on this lot",
     "items": [{"id": "tx_sb840", "applies_to": ["CG", "CI"], "text": "...", "source_url": "..."}]},
    {"id": "flags", "rule": "local conditions to flag",
     "items": [{"id": "flood", "text": "..."}, {"id": "historic", "text": "..."}]}
  ]
}
```
Leave a step out when the city has no such rule. Rezoning targets are the next districts up that a small
developer would plausibly ask for; every target must be a row in zoning_districts.csv.

## Rules for whoever fills these in

- Read the code itself (Municode, American Legal, eCode360, the city's site), not a summary. Give the section.
- If a number cannot be confirmed from the code text, leave the row out and list it in notes.md.
- Test the zoning GIS layer with a real request and record the exact field that holds the district code and
  20 or so distinct values, so `match` lines up.
- Free sources only. No sign-ups, no paid data, no records requests.

## Loading a region (added 2026-11-17)

One install serves one region. Set `REGION` and point `DATABASE_URL` at that region's database, then:

```
python -m db.migrate
python -m jobs.nightly
python -m jobs.check_region --write
```

`jobs.nightly` runs the region's parcel loader (`parcel_loader` in region.json), the zoning layer loader
(`jobs/load_zoning_layer.py`, from `zoning_layer`), the FHFA index for the region's state, then the shared
builders: parcel sites, `jobs/build_region.py` (what stands on each lot, comps, land values), rules and the
score. `jobs.check_region --write` fits the region's own size elasticity and 80% sale range, measures the
appraiser's land value against vacant-lot sales, and draws a 35-sale test set into
`data/regions/<id>/reference/test_parcels.csv`. Chicago's fitted range is never borrowed.

### Parcel loaders

| `parcel_loader` | Covers | Source |
|---|---|---|
| `fl_dor` | every Florida county | Department of Revenue NAL tax roll file and parcel map (`jobs/load_fl_dor.py`) |
| `arcgis_parcels` | Houston, San Antonio, Atlanta | a public parcel map layer named in `parcel_layer` (`jobs/load_arcgis_parcels.py`) |
| `dcad` | Dallas | Dallas Central Appraisal District yearly CSV export plus its parcel map layer (`jobs/load_dcad.py --dir`) |
| `tcad` | Austin | Travis Central Appraisal District fixed-width export plus its parcel map layer (`jobs/load_tcad.py --zip`) |

Florida county entries carry `dor_name`, `dor_county_no`, `shape_name`, `shape_epsg` (the State Plane zone of
the county's parcel map) and `tax_auth_codes` or `tax_auth_prefixes` (the city's taxing authority codes, read
from the NAL file). The roll holds each parcel's two latest sales, from January of the year before the roll, so
the comp pool starts at about 20 months of sales and grows as each year's roll is added. Sale dates are known
to the month.

`parcel_layer` holds the layer `url`, an optional `where` filter, the `fields` map (id, address, zip, use_code,
market_value, land_value, year_built, living_sqft, units, land_sqft or land_acres, nbhd) and `use_groups`, which
maps the layer's use codes (longest prefix wins) to vacant, single, condo, multi or other.

A region whose parcel layer has no year built can date buildings from finished new-construction permits:
`permits_year_built` in region.json (url, types, done_statuses, fields) and `jobs/load_permits_year_built.py`,
which `jobs.nightly` runs after the parcel loader. Atlanta uses it.

A Florida county can set `comps_countywide` to load newer 1-6 unit homes outside the city as comps only. When a
region has such comps, `jobs.check_region` also measures error on in-city sales and fits the range on those.

### Texas and Georgia: appraised values, not sale prices

Texas does not publish sale prices (Government Code 552.148). A region with `"price_basis"` set to appraisal
values builds its comp pool from the appraisal district's market value of 1 to 6 unit buildings built 2019 or
later, dated January 1 of the roll year and stored with `comp.basis = 'appraisal'`. Screens label these as
appraised values. `jobs.check_region` widens the fitted range by 10 points on each side
(`appraisal_basis.extra_range` in the shared defaults; an assumption until sale prices can be checked).
No MLS data is used.

### What the site reads

`GET /region` returns the region's name, state, parcel number label, price basis, sources and map bounds. The
web app uses it for the city name in the header, the search help text, the parcel page header and the map's
starting view. Chicago is unchanged.

### Rules shared by the new regions

`data/regions/_shared/rules/` holds files every region outside Chicago uses unless it has its own:
`feasibility_defaults.json` and `building_patterns.json`. A JSON file marked `"extends": true` holds only what
differs and is laid over the next copy down: region, then `_shared`, then `data/rules` (`region.rules_json`).
`"chicago_rules": false` switches off the Chicago-only lines (Open Space Impact Fee, Illinois Enterprise Zone,
Cook County classes, Missing Middle, the 2019 Chicago code flags).

Cost base outside Chicago: $162 per sq ft, from the NAHB 2024 construction cost survey. Tampa's own new-house
sales imply a median of $162 per sq ft after land and the builder's other costs (1,218 sales; 25th to 75th
percentile $128 to $200), so the national figure holds there. The feasibility-stage margin is wider
(-25% / +45%) until local job costs replace it.

### Engine rules added for the new regions

- A district row with FAR and no lot area per unit (Atlanta RG, MR, MRC) gives units = lot x FAR / 1,100 sq ft.
  The 1,100 is an assumed unit size, shown in the path's notes; a `far_only` step can change it.
- A zoning code stored with overlay suffixes (`R-2A/T/HP`) falls back to the text before the first `/`.
- A pattern with `paths` is used only on those zoning paths. `sold_as_one` values a house plus accessory unit
  as one home of the combined size.
- Where no vacant-lot sales are nearby, land is the appraiser's land value for the parcel divided by the
  measured ratio of appraiser land value to sale price (Tampa: 0.55 on 426 vacant-lot sales).

### Not built yet

Steps the city files describe that the engine does not compute: Tampa ADU eligible areas (map layer), Orlando
duplex-lot, multiplex and townhome steps, Jacksonville cottages, Miami cottage housing, Houston's Chapter 42
lot steps, Austin's small-lot rule. Each city's `notes.md` lists what could not be confirmed against the
official code text. Flood, historic and overlay layers are recorded in each region.json and not loaded yet.
