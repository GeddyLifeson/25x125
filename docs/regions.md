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
