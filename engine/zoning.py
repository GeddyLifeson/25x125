"""Zoning capacity for one lot: the 10 steps in docs/v1-spec.md (Zoning rules engine).

Pure functions over a Site and Rules. Each path gives units, floor area, height and parking with the rule
it rests on; flags list what can stop or slow a project. The engine presents the math; it does not pick
a path.
"""

import math
from dataclasses import asdict, dataclass, field

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
    p = rules.step("parking")["params"]
    per_unit = p["spaces_per_unit"].get(district, p["spaces_per_unit"]["default"])
    if units == 2 and district in p["two_flat_spaces_per_unit"]:
        per_unit = p["two_flat_spaces_per_unit"][district]
    big = p["large_building"]
    if district == big["district"] and units > big["after_units"]:
        cars = big["after_units"] * per_unit + (units - big["after_units"]) * big["spaces_per_unit"]
    else:
        cars = units * per_unit
    cars = math.ceil(cars - 1e-9)
    narrow = units <= 2 and site.frontage_ft is not None and site.frontage_ft <= p["narrow_lot_exemption_ft"]
    if site.transit_served:
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
    note = f"{per_unit:g} space(s) per unit outside transit-served areas"
    if narrow:
        note += f"; 0 if the lot of record has no improved alley ({site.frontage_ft:.0f} ft wide)"
    return cars, 0, note


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
    floor_area = (site.lot_sqft or 0) * (far if far is not None else d.far)
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


def evaluate(site: Site, rules: Rules, rezoning_target: str | None = None) -> Result:
    d = rules.district_for(site.zone_class)
    res = Result(site.pin, site.zone_class, d is not None, site.lot_sqft, site.frontage_ft)
    res.flags.extend(_flags(site, rules))
    if d is None or not site.lot_sqft:
        if d is None:
            res.flags.append(
                Flag("not_covered", f"District {site.zone_class or 'unknown'} is not covered in version 1.")
            )
        else:
            res.flags.append(Flag("no_lot_size", "No lot size on file; capacity cannot be computed."))
        return res
    lot = site.lot_sqft

    # 1-2. By right.
    units = _units(lot, d.lot_area_per_unit_sqft)
    notes = []
    if d.min_lot_area_sqft and lot < d.min_lot_area_sqft:
        units = min(units, 1)
        notes.append(
            f"lot is under the {d.min_lot_area_sqft:,.0f} sq ft district minimum; one house on a lot of record"
        )
    res.paths.append(_path(rules, site, d, "by_right", "By right", "none (permit only)", units, notes=notes))

    # 3. RS-3 two-flat.
    rs3 = rules.step("rs3_two_flat_exception")["params"]
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
    aa = rules.step("administrative_adjustment")
    adj_units = _units(lot, aa["params"]["lot_area_factor"] * d.lot_area_per_unit_sqft)
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
    adu = rules.step("adu")["params"]
    adu_ok = d.name in adu["by_district"] or (d.name in adu["by_map"] and site.adu_zone)
    if adu_ok:
        base = max(p.units for p in res.paths if p.approval == "none (permit only)")
        note = (
            f"ADU zone {site.adu_zone}: {site.adu_limits}"
            if d.name in adu["by_map"]
            else "ADU allowed in this district"
        )
        by_map = d.name in adu["by_map"]
        if by_map:
            cap = adu["annual_cap_per_block_face"].get(d.name)
            note += f"; yearly cap of {cap} per block face and opposite face" if cap else ""
            note += "; owner must live on site if the main building is a house"
        approval = adu["by_map_approval"] if by_map else "ADU permit (as of right)"
        p = _path(rules, site, d, "adu", "By right plus ADU", approval, base + adu["units"], notes=[note])
        p.citations.append(rules.step("adu")["section"])
        res.paths.append(p)
    elif d.name in adu["by_map"]:
        res.flags.append(Flag("no_adu", "Outside the city's ADU zones: no coach house or conversion unit in this district.",
                              rules.step("adu")["section"]))  # fmt: skip

    # 6. Rezoning.
    targets = rules.step("rezoning")["targets"].get(d.name, [])
    target = rezoning_target if rezoning_target in targets else (targets[0] if targets else None)
    if target:
        t = rules.districts[target]
        t_units = _units(lot, t.lot_area_per_unit_sqft)
        if t.min_lot_area_sqft and lot < t.min_lot_area_sqft:
            t_units = min(t_units, 1)
        fam = family(site.zone_class or "")
        label = f"{fam}{target[3:]}" if fam and target.startswith("B/C") else target
        p = _path(rules, site, t, "rezoning", f"Rezone to {label}", rules.step("rezoning")["approval"], t_units,
                  notes=[f"other targets: {', '.join(x for x in targets if x != target)}" if len(targets) > 1 else "only target listed"])  # fmt: skip
        if t_units >= rules.step("aro_flag")["params"]["units"]:
            p.notes.append("Affordable Requirements Ordinance applies at 10+ units with a zoning change")
        res.paths.append(p)

    # 7. Transit-served density bonus (B3-3 and C3-3).
    tb = rules.step("transit_density_bonus")
    if site.zone_class in tb["params"]["districts"] and site.transit_served:
        for tier in tb["params"]["tiers"]:
            p = _path(rules, site, d, f"tsl_bonus_{int(tier['aro_on_site_share'] * 100)}",
                      f"Transit-served bonus, {tier['aro_on_site_share']:.0%} of ARO units on site", tb["approval"],
                      _units(lot, tier["lot_area_per_unit_sqft"]), far=tier["far"])  # fmt: skip
            p.citations.append(tb["section"])
            res.paths.append(p)

    # 8. Ground floor residential in B/C.
    fam = family(site.zone_class or "")
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


def _flags(site: Site, rules: Rules) -> list[Flag]:
    out = []
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
