"""Load parcel signals from the City of Chicago portal into parcel_signal.

Each kind is replaced on every run. Windows keep the large sources small: violations since 2021, 311
vacant building and lot requests since 2021, demolition notices since 2021.
Run: python -m jobs.load_signals [--kind violation]
"""

import argparse
import json
from dataclasses import dataclass

from core.db import connect
from core.socrata import CHICAGO, Socrata
from core.sources import finish_pull, start_pull
from jobs.common import num, text, upsert

SINCE = "2021-01-01"


@dataclass(frozen=True)
class Signal:
    dataset: str
    id_field: str
    date_field: str
    status_field: str | None
    detail_field: str | None
    address_field: str
    where: str | None = None
    keep: tuple[str, ...] = ()


SIGNALS = {
    "violation": Signal(
        "22u3-xenr", "id", "violation_date", "violation_status", "violation_description", "address",
        f"violation_date >= '{SINCE}'", ("violation_code", "inspection_category", "department_bureau"),
    ),
    "vacant_building_311": Signal(
        "v6vf-nfxy", "sr_number", "created_date", "status", "sr_type", "street_address",
        f"sr_type = 'Vacant/Abandoned Building Complaint' and created_date >= '{SINCE}'", ("duplicate",),
    ),
    "vacant_lot_311": Signal(
        "v6vf-nfxy", "sr_number", "created_date", "status", "sr_type", "street_address",
        f"sr_type = 'Clean Vacant Lot Request' and created_date >= '{SINCE}'", ("duplicate",),
    ),
    "scofflaw": Signal(
        "rz4d-qp2m", "record_id", "building_list_date", None, "defendant_owner", "address",
        None, ("circuit_court_case_number", "secondary_address", "tertiary_address"),
    ),
    "city_owned": Signal(
        "aksk-kvfp", "id", "date_of_acquisition", "property_status", "sales_status", "address",
        None, ("managing_organization", "zoning_classification", "square_footage_city_estimate",
               "land_value", "application_use", "last_listed"),
    ),
    "demolition_notice": Signal(
        "qhb4-qx8k", "application_id", "start_date", None, "notification_type", "address",
        f"notification_type in ('Demolition Notice of Intent', 'Both Asbestos Abatement and Demo Notification')"
        f" and start_date >= '{SINCE}'", ("owner_applicant", "comment"),
    ),
    "environmental_hold": Signal(
        "6gqn-e2ij", "application_id", "date", None, "moratorium_type", "address",
        None, ("comment", "data_source"),
    ),
    "hearing_fine": Signal(
        "6br9-quuz", "id", "violation_date", "case_disposition", "violation_description", "address",
        f"violation_date >= '{SINCE}'", ("docket_number", "violation_code", "imposed_fine", "admin_costs",
                                         "hearing_date", "respondents"),
    ),
    "vacant_building_fine": Signal(
        "kc9i-wq85", "violation_number", "issued_date", "disposition_description", "violation_type",
        "property_address", None, ("docket_number", "issuing_department", "entity_or_person_s_", "total_fines",
                                   "total_paid", "current_amount_due", "last_hearing_date"),
    ),
    "foreclosed_rental": Signal(
        "yhcw-iu53", "id", "owner_date", None, "owner_name", "property_address",
        None, ("submission_date", "owner_management_agent_name", "owner_notices_agent_name"),
    ),
}  # fmt: skip

COLUMNS = ["kind", "source_id", "signal_date", "status", "detail", "address", "pin", "attrs", "lon", "lat",
           "source_pull_id"]  # fmt: skip
GEOM = {"geom": "st_setsrid(st_makepoint(lon::float8, lat::float8), 4326)"}


def to_row(kind: str, r: dict, pull_id: int) -> tuple | None:
    s = SIGNALS[kind]
    sid = text(r.get(s.id_field))
    if not sid:
        return None
    lon, lat = num(r.get("longitude")), num(r.get("latitude"))
    if lon is None and isinstance(r.get("location"), str) and r["location"].startswith("POINT ("):
        lon, lat = (float(v) for v in r["location"][7:-1].split())  # foreclosed rentals give WKT only
    if lon is None or lat is None or not (-88.0 < lon < -87.4 and 41.6 < lat < 42.1):
        lon = lat = None
    pin = text(r.get("pin"))
    return (
        kind,
        sid,
        (text(r.get(s.date_field)) or "")[:10] or None,
        text(r.get(s.status_field)) if s.status_field else None,
        text(r.get(s.detail_field)) if s.detail_field else None,
        text(r.get(s.address_field)),
        pin.replace("-", "") if pin else None,
        json.dumps({k: r[k] for k in s.keep if r.get(k) not in (None, "")}),
        lon,
        lat,
        pull_id,
    )


def run_kind(kind: str, client: Socrata | None = None, url: str | None = None) -> int:
    client = client or Socrata(CHICAGO)
    s = SIGNALS[kind]
    total = 0
    with connect(url) as conn:
        pull_id = start_pull(conn, CHICAGO, s.dataset, s.where or "")
        conn.commit()
        try:
            conn.execute("delete from parcel_signal where kind = %s", (kind,))
            for page in client.pages(s.dataset, order=":id", where=s.where):
                rows = (row for r in page if (row := to_row(kind, r, pull_id)))
                total += upsert(conn, "parcel_signal", COLUMNS, "kind, source_id", rows, GEOM)
            finish_pull(conn, pull_id, total)
        except Exception as e:
            conn.rollback()
            finish_pull(conn, pull_id, total, "failed", str(e)[:500])
            conn.commit()
            raise
    return total


def run(url: str | None = None) -> dict[str, int]:
    return {kind: run_kind(kind, url=url) for kind in SIGNALS}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=list(SIGNALS))
    a = ap.parse_args()
    for kind in [a.kind] if a.kind else SIGNALS:
        print(f"{kind}: {run_kind(kind):,}", flush=True)
