"""Rules as data: read from data/rules (for seeding and tests) or from the rule table (for the app).

Both paths build the same Rules object, so the nightly scorer and the live screens use the same numbers.
"""

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from core import region

RULES_DIR = Path(__file__).resolve().parents[1] / "data" / "rules"


@dataclass(frozen=True)
class Citation:
    section: str | None
    source_url: str | None
    verified_on: str | None

    def text(self) -> str:
        return "; ".join(
            x
            for x in (self.section, self.source_url, self.verified_on and f"verified {self.verified_on}")
            if x
        )


@dataclass(frozen=True)
class District:
    name: str  # e.g. 'RT-4' or 'B/C-2'
    match: tuple[str, ...]
    lot_area_per_unit_sqft: float
    min_lot_area_sqft: float | None
    far: float
    cite: Citation
    max_units: int | None = None  # cap per lot whatever the lot area (1 = single-family district)
    min_lot_width_ft: float | None = None
    max_lot_coverage: float | None = None


@dataclass(frozen=True)
class Height:
    district: str
    frontage_from_ft: float
    frontage_to_ft: float | None
    ground_floor_commercial: str  # 'any', 'yes', 'no'
    max_height_ft: float
    cite: Citation


@dataclass
class Rules:
    districts: dict[str, District] = field(default_factory=dict)
    heights: list[Height] = field(default_factory=list)
    steps: dict[str, dict] = field(default_factory=dict)
    special: dict[str, dict] = field(default_factory=dict)

    def district_for(self, zone_class: str | None) -> District | None:
        """'B3-2' -> the B/C-2 row, 'RT-4' -> RT-4. None when version 1 doesn't cover the district."""
        if not zone_class:
            return None
        for d in self.districts.values():
            if zone_class in d.match:
                return d
        return None

    def height(
        self, district: str, frontage_ft: float | None, ground_floor_commercial: bool
    ) -> Height | None:
        f = frontage_ft or 0
        want = "yes" if ground_floor_commercial else "no"
        for h in self.heights:
            if h.district != district or h.ground_floor_commercial not in ("any", want):
                continue
            if h.frontage_from_ft <= f and (h.frontage_to_ft is None or f < h.frontage_to_ft):
                return h
        return None

    def step(self, step_id: str) -> dict:
        return self.steps[step_id]

    @classmethod
    def from_rows(cls, rows) -> "Rules":
        r = cls()
        for rule_set, key, value, section, source_url, _file, _start, _end, verified_on in rows:
            cite = Citation(section, source_url, str(verified_on) if verified_on else None)
            if rule_set == "zoning_district":
                r.districts[key] = District(key, tuple(value["match"]), value["lot_area_per_unit_sqft"],
                                            value["min_lot_area_sqft"], value["far"], cite, value.get("max_units"),
                                            value.get("min_lot_width_ft"), value.get("max_lot_coverage"))  # fmt: skip
            elif rule_set == "zoning_height":
                r.heights.append(Height(value["district"], value["frontage_from_ft"], value["frontage_to_ft"],
                                        value["ground_floor_commercial"], value["max_height_ft"], cite))  # fmt: skip
            elif rule_set == "zoning_step":
                r.steps[key] = value
            elif rule_set == "special_district":
                r.special[key] = value
        return r

    @classmethod
    def from_files(cls, directory: Path | None = None) -> "Rules":
        return cls.from_rows(rows_from_files(directory))

    @classmethod
    def from_db(cls, conn) -> "Rules":
        return cls.from_rows(
            conn.execute(
                "select rule_set, rule_key, value, section, source_url, source_file, effective_from,"
                " effective_to, verified_on from rule where municipality_id = %s"
                " and (effective_to is null or effective_to >= current_date)",
                (region.region_id(),),
            ).fetchall()
        )


def _f(v) -> float | None:
    return float(v) if v not in (None, "") else None


def rows_from_files(directory: Path | None = None) -> list[tuple]:
    """(rule_set, rule_key, value, section, source_url, source_file, effective_from, effective_to, verified_on)

    With no directory, each file is the region's own copy when it has one, else the shared copy
    (core/region.py). Regions outside Chicago have no special_districts.json of their own and get none."""

    def path(name: str) -> Path:
        return directory / name if directory else region.rules_file(name)

    out = []
    for r in csv.DictReader(path("zoning_districts.csv").open(encoding="utf-8")):
        if not r.get("district") or not r.get("lot_area_per_unit_sqft"):
            continue
        value = {
            "match": r["match"].split(),
            "lot_area_per_unit_sqft": float(r["lot_area_per_unit_sqft"]),
            "min_lot_area_sqft": _f(r.get("min_lot_area_sqft")),
            "far": _f(r.get("far")) or 0.0,
            "max_units": int(float(r["max_units"])) if r.get("max_units") else None,
            "min_lot_width_ft": _f(r.get("min_lot_width_ft")),
            "max_lot_coverage": _f(r.get("max_lot_coverage")),
        }
        out.append(("zoning_district", r["district"], value, r["section"], r["source_url"],
                    "zoning_districts.csv", None, None, r["verified_on"]))  # fmt: skip
    for i, r in enumerate(csv.DictReader(path("zoning_heights.csv").open(encoding="utf-8"))):
        if not r.get("district") or not r.get("max_height_ft"):
            continue
        value = {
            "district": r["district"],
            "frontage_from_ft": _f(r.get("frontage_from_ft")) or 0.0,
            "frontage_to_ft": _f(r.get("frontage_to_ft")),
            "ground_floor_commercial": r.get("ground_floor_commercial") or "any",
            "max_height_ft": float(r["max_height_ft"]),
        }
        out.append(("zoning_height", f"{r['district']}#{i}", value, r["section"], r["source_url"],
                    "zoning_heights.csv", None, None, r["verified_on"]))  # fmt: skip
    steps = json.loads(path("zoning_steps.json").read_text(encoding="utf-8"))
    for s in steps["steps"]:
        out.append(("zoning_step", s["id"], s, s.get("section"), s.get("source_url"), "zoning_steps.json", None,
                    None, steps["verified_on"]))  # fmt: skip
    special_file = path("special_districts.json")
    if (
        not directory
        and not region.is_chicago()
        and not (region.rules_dir() / "special_districts.json").exists()
    ):
        return out
    special = json.loads(special_file.read_text(encoding="utf-8"))
    for s in special["rules"]:
        ends = (s.get("dollars") or {}).get("ends")
        out.append(("special_district", s["id"], s, s.get("code"), (s.get("sources") or [None])[0],
                    "special_districts.json", None, ends, s.get("verified_on")))  # fmt: skip
    return out


def family(zone_class: str) -> str | None:
    """Letter family of a B/C district: 'B3-2' -> 'B3'."""
    m = re.match(r"^([BC][123])-", zone_class or "")
    return m.group(1) if m else None
