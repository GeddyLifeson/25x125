"""Zoning capacity for one lot: the 10 steps in docs/v1-spec.md (Zoning rules engine).

Pure functions over a Site and Rules. Each path gives units, floor area, height and parking with the rule
it rests on; flags list what can stop or slow a project. The engine presents the math; it does not pick
a path.
"""

import math
from dataclasses import asdict, dataclass, field

from core import region
from engine.rules import District, Rules, family


@dataclass
class Site:
    pin: str
    zone_class: str | None
    lot_sqft: float | None
    frontage_ft: float | None = None
    lot_source: str | None = None
    zone_share: float | None = None
    zone_class_2: str | None = None
    zone_share_2: float | None = None
    transit_served: str | None = None
    adu_zone: str | None = None
    adu_limits: str | None = None
    special_district: str | None = None
    historic_rating: str | None = None
    landmark_name: str | None = None
    fire_limits: bool | None = None
    overlays: list | None = None  # outside Chicago: [{"kind": "flood", "name": "AE"}, ...]
    use_now: str | None = None
    units_now: int | None = None
    block_lots: int | None = None
    block_multi_lots: int | None = None
    block_single_lots: int | None = None
    block_two_flat_lots: int | None = None
    block_vacant_lots: int | None = None


@dataclass
class Path:
    id: str
    name: str
    approval: str
    district: str
    units: int
    floor_area_sqft: float
    max_height_ft: float | None
    parking_spaces: int
    bike_spaces: int
    notes: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


@dataclass
class Flag:
    id: str
    text: str
    citation: str | None = None
    dollars: float | None = None


@dataclass
class Result:
    pin: str
    zone_class: str | None
    covered: bool
    lot_sqft: float | None
    frontage_ft: float | None
    paths: list[Path] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)

    def max_units(self) -> tuple[int, str | None]:
        if not self.paths:
            return 0, None
        best = max(self.paths, key=lambda p: (p.units, -len(p.approval)))
        return best.units, best.id

    def to_dict(self) -> dict:
        return asdict(self)


def _parking(rules: Rules, district: str, units: int, site: "Site") -> tuple[int, int, str]:
    """Car and bike spaces for a building of `units` on this lot (17-10-0207, 17-10-0102-B)."""
    p = rules.steps.get("parking", {}).get("params") or {"spaces_per_unit": {"default": 1}}
    spu = p["spaces_per_unit"]
    per_unit = spu.get(district, spu.get("default", 1))
    if units == 2 and district in p.get("two_flat_spaces_per_unit", {}):
        per_unit = p["two_flat_spaces_per_unit"][district]
    big = p.get("large_building")
    if big and district == big["district"] and units > big["after_units"]:
        cars = big["after_units"] * per_unit + (units - big["after_units"]) * big["spaces_per_unit"]
    else:
        cars = units * per_unit
    cars = math.ceil(cars - 1e-9)
    narrow_ft = p.get("narrow_lot_exemption_ft")
    narrow = bool(narrow_ft) and units <= 2 and site.frontage_ft is not None and site.frontage_ft <= narrow_ft
    if site.transit_served and "bike_spaces_per_unit" in p:
        bikes = units * p["bike_spaces_per_unit"]
        if site.transit_served == "Metra station":
            share = p["metra_only_share_by_right"]
            return (
                math.ceil(cars * share - 1e-9),
                bikes,
                (
                    f"transit-served by a Metra station only: {cars} spaces cut {share:.0%} by right"
                    f" to {math.ceil(cars * share - 1e-9)}; to 0 with an administrative adjustment"
                ),
            )
        return 0, bikes, f"transit-served ({site.transit_served}): no car parking required"
    note = f"{per_unit:g} space(s) per unit" + (
        " outside transit-served areas" if "bike_spaces_per_unit" in p else ""
    )
    if narrow:
        note += f"; 0 if the lot of record has no improved alley ({site.frontage_ft:.0f} ft wide)"
    return cars, 0, note


def _cap(d: District, units: int) -> int:
    return min(units, d.max_units) if d.max_units else units


def _units(lot: float, lapu: float) -> int:
    return max(math.floor(lot / lapu + 1e-9), 0)


def _block_share(site: Site, vacant_counts_as_multi: bool = False) -> float | None:
    if not site.block_lots:
        return None
    multi = (site.block_multi_lots or 0) + (site.block_vacant_lots or 0 if vacant_counts_as_multi else 0)
    return multi / site.block_lots


def _path(rules, site, d: District, path_id, name, approval, units, far=None, height_factor=1.0, notes=()):
    h = rules.height(d.name, site.frontage_ft, ground_floor_commercial=False)
    with_shop = rules.height(d.name, site.frontage_ft, ground_floor_commercial=True)
    if h and with_shop and with_shop.max_height_ft > h.max_height_ft:
        notes = [
            *notes,
            f"{with_shop.max_height_ft * height_factor:.0f} ft with ground-floor commercial space",
        ]
    ratio = far if far is not None else d.far
    if not ratio and d.max_lot_coverage and h:
        # No floor area ratio in the code: lot coverage times the stories the height limit allows (11 ft each).
        ratio = d.max_lot_coverage * max(int(h.max_height_ft // 11), 1)
        notes = [
            *notes,
            f"no floor area ratio in the code; floor area from {d.max_lot_coverage:.0%} lot coverage",
        ]
    floor_area = (site.lot_sqft or 0) * ratio
    cars, bikes, park_note = _parking(rules, d.name, units, site)
    cites = [f"{d.name}: {d.cite.text()}"]
    if h:
        cites.append(f"height: {h.cite.text()}")
    return Path(
        id=path_id,
        name=name,
        approval=approval,
        district=d.name,
        units=units,
        floor_area_sqft=round(floor_area),
        max_height_ft=round(h.max_height_ft * height_factor, 1) if h else None,
        parking_spaces=cars,
        bike_spaces=bikes,
        notes=[*notes, park_note]
        + ([] if h else ["no height limit in the table; tall buildings need a Planned Development"]),
        citations=cites,
    )


def _far_unit_sqft(rules: Rules) -> float:
    return float((rules.steps.get("far_only") or {}).get("params", {}).get("unit_sqft", 1100))


def _district_units(lot: float, d, rules: Rules) -> int:
    """Units from lot area per unit; in a district that limits floor area only, floor area / an assumed unit size."""
    stepped = _stepped_density(lot, d, rules)
    if stepped is not None:
        return stepped
    if d.lot_area_per_unit_sqft:
        return _units(lot, d.lot_area_per_unit_sqft)
    return int(lot * (d.far or 0) // _far_unit_sqft(rules))


def _stepped_density(lot: float, d, rules: Rules) -> int | None:
    """Districts that ask a set area for the first two units and less for each added one (Jacksonville RMD-B to
    RMD-D, CRO, RO: 6,000 sq ft for two, then 2,900 / 2,100 / 1,340), capped at units per acre. Read from any city
    step whose params hold first_two_units_sqft and added_unit_sqft. None when no such step covers the district."""
    for step in rules.steps.values():
        prm = step.get("params") or {}
        added = (prm.get("added_unit_sqft") or {}).get(d.name) if prm.get("first_two_units_sqft") else None
        if not added:
            continue
        first = prm["first_two_units_sqft"]
        n = 1 if lot < first else 2 + int((lot - first) // added)
        cap = (prm.get("max_units_per_acre") or {}).get(d.name)
        return max(1, min(n, int(lot * cap // 43560))) if cap else n
    return None


def _by_district(value, district: str):
    """A step parameter given once for all districts, or as {district: value}."""
    return value.get(district) if isinstance(value, dict) else value


def _step_paths(site: Site, rules: Rules, d: District, lot: float) -> list[Path]:
    """City steps that add a housing type on certain districts (Orlando duplex lots and multiplexes, for
    example). A step takes part when its params carry `engine_path`:
    {"units": 2} for a fixed count, or {"units": "density"} for lot area / the district's lot area per unit,
    with optional "min_units", "max_units", "max_units_by_district" and "round_up_from" (0.5 rounds halves up).
    "lot_area_per_unit_sqft" replaces the district's figure for this path, and "units_per_lot" multiplies the
    count (Houston: two units on each 3,500 sq ft lot). Eligibility: the district is in `by_district`,
    `districts` or `applies_to` (or a key of `min_lot_sqft`), the lot meets `min_lot_sqft` and, when the
    frontage is known, `min_lot_width_ft`. "districts" inside engine_path narrows the path to those districts.
    "min_lot_sqft" and "min_lot_width_ft" inside engine_path take
    precedence over the step's own."""
    out = []
    for sid, step in rules.steps.items():
        prm = (step or {}).get("params") or {}
        ep = prm.get("engine_path")
        if not ep:
            continue
        lot_rule = ep.get("min_lot_sqft", prm.get("min_lot_sqft", prm.get("min_lot_area_sqft")))
        districts = (
            ep.get("districts")
            or prm.get("by_district")
            or prm.get("districts")
            or prm.get("applies_to")
            or (list(lot_rule) if isinstance(lot_rule, dict) else [])
        )
        if d.name not in districts:
            continue
        min_lot = _by_district(lot_rule, d.name)
        min_w = _by_district(ep.get("min_lot_width_ft", prm.get("min_lot_width_ft")), d.name)
        if min_lot and lot < min_lot:
            continue
        if min_w and site.frontage_ft and site.frontage_ft < min_w - 0.5:
            continue
        if ep.get("units") == "density":
            lapu = ep.get("lot_area_per_unit_sqft") or d.lot_area_per_unit_sqft
            if not lapu:
                continue
            raw = lot / lapu
            n = int(raw + (1 - ep["round_up_from"])) if ep.get("round_up_from") else int(raw)
        else:
            n = int(ep["units"])
        n *= int(ep.get("units_per_lot", 1))
        cap = (ep.get("max_units_by_district") or {}).get(d.name, ep.get("max_units"))
        n = min(n, cap) if cap else n
        if n < ep.get("min_units", 1):
            continue
        notes = [step.get("rule", "")[:300]] if step.get("rule") else []
        p = _path(rules, site, d, sid, ep.get("name", sid.replace("_", " ").capitalize()),
                  step.get("approval") or ep.get("approval", "none (permit only)"), n, notes=notes)  # fmt: skip
        if step.get("section"):
            p.citations.append(step["section"])
        out.append(p)
    return out


def evaluate(site: Site, rules: Rules, rezoning_target: str | None = None) -> Result:
    d = rules.district_for(site.zone_class)
    res = Result(site.pin, site.zone_class, d is not None, site.lot_sqft, site.frontage_ft)
    res.flags.extend(_flags(site, rules))
    if d is None or not site.lot_sqft:
        if d is None:
            res.flags.append(
                Flag("not_covered", f"District {site.zone_class or 'unknown'} is not covered in version 1.")
                if region.is_chicago() or site.zone_class
                else Flag("not_covered", "No zoning district on file for this lot.")
            )
        else:
            res.flags.append(Flag("no_lot_size", "No lot size on file; capacity cannot be computed."))
        return res
    lot = site.lot_sqft

    # 1-2. By right.
    units = _cap(d, _district_units(lot, d, rules))
    notes = []
    if not d.lot_area_per_unit_sqft:
        notes.append(
            f"the district limits floor area, not units: units = lot x FAR {d.far:g} /"
            f" {_far_unit_sqft(rules):,.0f} sq ft per unit (an assumed size)"
        )
    if d.max_units and units == d.max_units:
        notes.append(f"district allows at most {d.max_units} unit(s) per lot")
    if d.min_lot_area_sqft and lot < d.min_lot_area_sqft:
        units = min(units, 1)
        notes.append(
            f"lot is under the {d.min_lot_area_sqft:,.0f} sq ft district minimum; one house on a lot of record"
        )
    if d.min_lot_width_ft and site.frontage_ft and site.frontage_ft < d.min_lot_width_ft - 0.5:
        res.flags.append(Flag("narrow_lot", f"Lot is about {site.frontage_ft:.0f} ft wide; the district asks for"
                              f" {d.min_lot_width_ft:g} ft. A lot of record may still be buildable; check with the city.",
                              d.cite.section))  # fmt: skip
    res.paths.append(_path(rules, site, d, "by_right", "By right", "none (permit only)", units, notes=notes))
    res.paths.extend(_step_paths(site, rules, d, lot))

    # 3. RS-3 two-flat.
    rs3 = rules.steps.get("rs3_two_flat_exception", {}).get("params") or {"district": None}
    if d.name == rs3["district"]:
        in_606 = rs3["special_district"] in (site.special_district or "")
        share = _block_share(site)
        if in_606 or (share is not None and share >= rs3["block_face_share"]):
            two = min(_units(lot, rs3["lot_area_per_unit_sqft"]), rs3["max_units"])
            if two > units:
                why = (
                    "lot is in the 606 district"
                    if in_606
                    else (
                        f"{share:.0%} of lots on the block face have 2+ units ({site.block_multi_lots} of {site.block_lots})"
                    )
                )
                p = _path(
                    rules, site, d, "rs3_two_flat", "RS-3 two-flat", "none (permit only)", two, notes=[why]
                )
                p.citations.append("17-2-0303-B.1 (1,500 sq ft per unit, two units only)")
                res.paths.append(p)

    # 4. Administrative adjustment.
    aa = rules.steps.get("administrative_adjustment")
    adj_units = _cap(d, _units(lot, aa["params"]["lot_area_factor"] * d.lot_area_per_unit_sqft)) if aa else 0
    if adj_units > units and not (
        d.min_lot_area_sqft and lot < d.min_lot_area_sqft * aa["params"]["lot_area_factor"]
    ):
        p = _path(rules, site, d, "admin_adjustment", "Administrative adjustment", aa["approval"], adj_units,
                  height_factor=aa["params"]["height_factor"],
                  notes=["lot area per unit reduced 10%",
                         "height +10% only if not taller than buildings on abutting lots (17-13-1003-L-3)",
                         "reading disputed: " + aa["dispute"]])  # fmt: skip
        p.citations.append(aa["section"])
        res.paths.append(p)

    # 5. ADU.
    adu_step = rules.steps.get("adu") or {}
    adu = adu_step.get("params") or {}
    by_map_list = adu.get("by_map", [])
    adu_ok = d.name in adu.get("by_district", []) or (d.name in by_map_list and site.adu_zone)
    base = max((p.units for p in res.paths if p.approval == "none (permit only)"), default=0)
    under = adu.get("multi_family_total_units_under")
    if adu_ok and under and base >= under:
        adu_ok = False  # San Antonio: an ADU only where the lot has fewer than 5 units
    if adu_ok:
        by_map = d.name in by_map_list
        note = (
            f"ADU zone {site.adu_zone}" + (f": {site.adu_limits}" if site.adu_limits else "")
            if by_map
            else "ADU allowed in this district"
        )
        if by_map and region.is_chicago():
            cap = adu["annual_cap_per_block_face"].get(d.name)
            note += f"; yearly cap of {cap} per block face and opposite face" if cap else ""
            note += "; owner must live on site if the main building is a house"
        else:
            if adu.get("max_sqft"):
                note += f", up to {adu['max_sqft']:,.0f} sq ft"
            if adu.get("owner_occupancy"):
                note += "; owner must live on site"
        approval = (
            adu.get("by_map_approval", adu.get("approval")) if by_map else adu.get("approval")
        ) or "ADU permit (as of right)"
        p = _path(
            rules, site, d, "adu", "By right plus ADU", approval, base + adu.get("units", 1), notes=[note]
        )
        if adu_step.get("section"):
            p.citations.append(adu_step["section"])
        res.paths.append(p)
    elif d.name in by_map_list:
        res.flags.append(Flag("no_adu", "Outside the city's ADU zones: no coach house or conversion unit in this district.",
                              adu_step.get("section")))  # fmt: skip

    # State laws that override the city code on this lot (for example Texas SB 840 on commercial land).
    for item in (rules.steps.get("state_overrides") or {}).get("items", []):
        applies = item.get("applies_to")
        if applies and d.name not in applies and (site.zone_class or "") not in applies:
            continue
        if not applies and not item.get("always"):
            continue
        upa = (item.get("path") or {}).get("units_per_acre")
        if upa:
            so_units = _units(lot, 43560 / upa)
            if so_units > units and so_units >= (item["path"].get("min_units") or 0):
                p = _path(rules, site, d, "state_override", item.get("name", "State law"),
                          item["path"].get("approval", "none (permit only, by state law)"), so_units,
                          notes=[item["text"]])  # fmt: skip
                if (
                    item["path"].get("min_height_ft")
                    and (p.max_height_ft or 0) < item["path"]["min_height_ft"]
                ):
                    p.max_height_ft = item["path"]["min_height_ft"]
                if item["path"].get("parking_per_unit") is not None:
                    p.parking_spaces = min(
                        p.parking_spaces, math.ceil(so_units * item["path"]["parking_per_unit"])
                    )
                p.citations.append(item.get("source_url") or item["id"])
                res.paths.append(p)
                continue
        res.flags.append(Flag(item["id"], item["text"], item.get("source_url")))

    # 6. Rezoning.
    rz = rules.steps.get("rezoning") or {"targets": {}}
    targets = [t for t in rz["targets"].get(d.name, []) if t in rules.districts]
    target = rezoning_target if rezoning_target in targets else (targets[0] if targets else None)
    if target:
        t = rules.districts[target]
        t_units = _cap(t, _district_units(lot, t, rules))
        if t.min_lot_area_sqft and lot < t.min_lot_area_sqft:
            t_units = min(t_units, 1)
        fam = family(site.zone_class or "")
        label = f"{fam}{target[3:]}" if fam and target.startswith("B/C") else target
        p = _path(rules, site, t, "rezoning", f"Rezone to {label}", rz.get("approval", "rezoning"), t_units,
                  notes=[f"other targets: {', '.join(x for x in targets if x != target)}" if len(targets) > 1 else "only target listed"])  # fmt: skip
        if "aro_flag" in rules.steps and t_units >= rules.step("aro_flag")["params"]["units"]:
            p.notes.append("Affordable Requirements Ordinance applies at 10+ units with a zoning change")
        res.paths.append(p)

    # 7. Transit-served density bonus (B3-3 and C3-3).
    tb = rules.steps.get("transit_density_bonus") or {"params": {"districts": []}}
    if site.zone_class in tb["params"]["districts"] and site.transit_served:
        for tier in tb["params"]["tiers"]:
            p = _path(rules, site, d, f"tsl_bonus_{int(tier['aro_on_site_share'] * 100)}",
                      f"Transit-served bonus, {tier['aro_on_site_share']:.0%} of ARO units on site", tb["approval"],
                      _units(lot, tier["lot_area_per_unit_sqft"]), far=tier["far"])  # fmt: skip
            p.citations.append(tb["section"])
            res.paths.append(p)

    # 8. Ground floor residential in B/C.
    fam = family(site.zone_class or "") if "ground_floor_residential" in rules.steps else None
    if fam:
        status = rules.step("ground_floor_residential")["params"][fam]
        if status != "by right":
            res.flags.append(Flag("ground_floor", f"All-residential building: ground-floor units are {status} in {fam}.",
                                  rules.step("ground_floor_residential")["section"]))  # fmt: skip

    # Pilsen two-flat limit.
    pil = rules.special.get("pilsen-multi-unit-preservation")
    if pil and pil["match"][0] in (site.special_district or ""):
        small = (site.block_single_lots or 0) + (site.block_two_flat_lots or 0)
        if site.block_lots and small / site.block_lots <= 0.5:
            res.flags.append(
                Flag(
                    "pilsen_3_plus",
                    "Pilsen district: houses and two-flats are under half the block face, so a new building needs 3+ units.",
                    pil["code"],
                )
            )
    return res


# FEMA zones inside the special flood hazard area (the 1% annual chance flood): flood insurance is required
# with a federally backed mortgage, and the lowest floor must sit at or above the base flood elevation.
SFHA_ZONES = ("A", "AE", "AH", "AO", "AR", "A99", "V", "VE")


def _overlay_flags(site: Site) -> list[Flag]:
    """Flags for the region overlays that limit building or add cost. Other overlays are listed on the
    parcel page but raise no flag."""
    out = []
    for o in site.overlays or []:
        kind, name = o.get("kind") or "", (o.get("name") or "").strip()
        # Jacksonville's parcel layer lists every zone touching the lot, comma separated ("AE, X").
        zones = [z.strip().upper() for z in name.split(",")]
        sfha = [z for z in zones if z in SFHA_ZONES]
        if kind.startswith("flood") and ("FLOODWAY" in name.upper() or kind == "flood_floodway"):
            out.append(Flag("floodway", "In the regulatory floodway: new buildings are usually not allowed.",
                            "FEMA flood map"))  # fmt: skip
        elif kind.startswith("flood") and sfha:
            out.append(Flag("flood", f"FEMA flood zone {', '.join(sfha)}: flood insurance is required with most"
                            " mortgages, and the lowest floor must be at or above the base flood elevation.",
                            "FEMA flood map"))  # fmt: skip
        elif kind.startswith("flood") and ("100-YEAR" in name.upper() or "25-YEAR" in name.upper()):
            out.append(Flag("flood", f"{name}: the city limits building in its own floodplain, which can be wider"
                            " than FEMA's.", "city floodplain map"))  # fmt: skip
        elif kind.startswith("historic") or kind == "landmark":
            out.append(Flag("historic", f"Historic district or landmark: {name}. Demolition and exterior changes"
                            " need review by the city's historic commission.", kind.replace("_", " ")))  # fmt: skip
        elif kind.startswith("conservation") or kind in ("nccd", "nso"):
            out.append(Flag("conservation", f"Conservation or neighborhood overlay: {name}. It can change lot size,"
                            " height and design rules; check the overlay text.", kind.replace("_", " ")))  # fmt: skip
        elif kind in ("special_minimum_lot_size", "special_minimum_building_line", "deed_restrictions"):
            out.append(Flag(kind, f"{kind.replace('_', ' ').capitalize()} area ({name}): smaller lots or added"
                            " units may not be allowed here.", kind.replace("_", " ")))  # fmt: skip
        elif kind in ("restricted_driveway_access", "walkable_places_tod"):
            out.append(Flag("driveway", f"Next to a street with restricted lot driveway access ({name}; corner lots included): new lots may need"
                            " access from another street or a shared drive.", kind.replace("_", " ")))  # fmt: skip
        elif kind in ("airport_military", "airport", "military"):
            out.append(Flag("airport", f"Airport or military zone ({name}): housing density and building height can"
                            " be limited; check the zone's rules.", kind.replace("_", " ")))  # fmt: skip
        elif kind == "coastal_high_hazard":
            out.append(Flag(kind, "Coastal high hazard area: added building and density limits apply.",
                            kind.replace("_", " ")))  # fmt: skip
    seen, uniq = set(), []
    for f in out:
        if (f.id, f.text) not in seen:
            seen.add((f.id, f.text))
            uniq.append(f)
    return uniq


def _flags(site: Site, rules: Rules) -> list[Flag]:
    out = _overlay_flags(site)
    if site.historic_rating in ("Red", "Orange"):
        out.append(Flag("historic", f"Historic survey rating {site.historic_rating}: 90-day hold on a demolition permit.",
                        "Demolition Delay Ordinance (Chicago Historic Resources Survey)"))  # fmt: skip
    if site.landmark_name:
        out.append(
            Flag(
                "landmark",
                f"Chicago Landmark: {site.landmark_name}. Exterior changes need Landmarks Commission review.",
            )
        )
    sur = rules.special.get("demolition-surcharge-606-pilsen")
    if sur and any(m in (site.special_district or "") for m in sur["match"]):
        dollars = None
        if site.units_now:
            dollars = max(sur["dollars"]["per_unit"] * site.units_now, sur["dollars"]["per_building"])
        text = "606/Pilsen demolition surcharge: $20,000 per unit or $60,000 per building, whichever is more"
        if dollars:
            text += f"; ${dollars:,.0f} for the {site.units_now} unit(s) on the lot now"
        out.append(Flag("demolition_surcharge", text + ".", sur["code"], dollars))
    if site.fire_limits:
        out.append(
            Flag(
                "fire_limits",
                "Inside the fire limits: wood-frame construction is restricted.",
                "Municipal Code 13-116-010",
            )
        )
    if site.zone_share is not None and site.zone_share < 0.9:
        other = f" and {site.zone_share_2:.0%} in {site.zone_class_2}" if site.zone_class_2 else ""
        out.append(Flag("split_zoned", f"Split-zoned lot: {site.zone_share:.0%} in {site.zone_class}{other}."
                        f" Results use {site.zone_class}, the larger share; each part has its own rules."))  # fmt: skip
    if site.lot_source == "assessor":
        out.append(
            Flag("lot_from_assessor", "Lot size is the Assessor's figure; no lot polygon. Frontage unknown.")
        )
    return out
