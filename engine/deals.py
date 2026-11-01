"""Deals: saved parcels, their stage, the feasibility edits saved with them, and the owner outreach log.

Endpoints are mounted on the engine app (engine/app.py). Every list exports as CSV; deals import from CSV.
Every route needs a signed-in member on a plan with deals (engine/auth.py). Queries run under row-level
security for the caller's organization, so a deal of another organization reads as not found. Changes and
exports go to the audit log.
"""

import csv
import io
import json
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.db import connect
from engine.accounts import export_gate
from engine.auth import Caller, audit, needs, scoped
from engine.parcel_feasibility import feasibility

router = APIRouter()

STAGES = {"lead": "Lead", "contacted": "Contacted", "feasibility": "Feasibility",
          "under_contract": "Under contract", "passed": "Passed"}  # fmt: skip
EVENT_KINDS = {"letter": "Letter mailed", "call": "Call", "text": "Text message", "email": "Email",
               "visit": "Site visit", "meeting": "Meeting", "note": "Note", "reminder": "Reminder"}  # fmt: skip
OUTREACH_NOTE = "Calls and texts follow TCPA rules; email follows CAN-SPAM."
LABEL = "Estimates, not tax, legal, zoning or appraisal advice."

DEAL_FIELDS = ["id", "org_id", "pin", "pin10", "address", "stage", "next_step", "next_step_on", "exit", "target",
               "scenario", "scenario_name", "overrides", "result", "notes", "created_at", "updated_at"]  # fmt: skip
NIGHTLY_FIELDS = [
    "score",
    "by_right_units",
    "profit_central",
    "max_land_price",
    "return_on_cost_p25",
    "computed_on",
]
CSV_COLUMNS = ["id", "pin", "pin10", "address", "community_area", "zone_class", "stage", "next_step", "next_step_on",
               "scenario_name", "exit", "profit", "max_land_price", "numbers_from", "numbers_on", "notes",
               "created_at", "updated_at", "overrides"]  # fmt: skip
EVENT_COLUMNS = ["id", "deal_id", "address", "kind", "event_on", "note", "created_at"]


class DealIn(BaseModel):
    pin: str
    stage: str = "lead"
    next_step: str | None = None
    next_step_on: date | None = None
    exit: str | None = Field(
        None, description="sell or hold; when set, the engine runs feasibility and saves the numbers"
    )
    target: str | None = None
    scenario: int | None = Field(None, ge=0, le=2)
    overrides: dict = Field(default_factory=dict)
    notes: str | None = None


class DealPatch(BaseModel):
    stage: str | None = None
    next_step: str | None = None
    next_step_on: date | None = None
    notes: str | None = None
    address: str | None = None
    exit: str | None = None
    target: str | None = None
    scenario: int | None = Field(None, ge=0, le=2)
    overrides: dict | None = None


class EventIn(BaseModel):
    kind: str
    event_on: date | None = None
    note: str = ""


def _clean_pin(pin: str) -> str:
    pin = pin.replace("-", "").strip()
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    return pin


def _stage(value: str) -> str:
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    if v not in STAGES:
        raise HTTPException(400, f"stage must be one of {', '.join(STAGES)}")
    return v


def _jsonable(v):
    if isinstance(v, datetime | date):
        return v.isoformat()
    if type(v).__name__ == "Decimal":
        return float(v)
    return v


def _snapshot(f: dict, scenario: int) -> dict | None:
    """The saved scenario's headline numbers, with the run date, so the deal table can show them later."""
    if not f.get("scenarios"):
        return None
    i = min(scenario, len(f["scenarios"]) - 1)
    s = f["scenarios"][i]
    snap = {"scenario": i, "name": s["name"], "units": s["units"], "exit": s["exit"],
            "total_cost": s["cost_range"]["central"], "total_cost_low": s["cost_range"]["low"],
            "total_cost_high": s["cost_range"]["high"], "run_on": date.today().isoformat(),
            "source": "25x125 feasibility engine, run when the deal was saved", "label": LABEL}  # fmt: skip
    if s.get("sell"):
        sell = s["sell"]
        snap.update(profit=sell["profit"], return_on_cost=sell["return_on_cost"], max_land_price=sell["max_land_price"],
                    profit_p10=(sell.get("range") or {}).get("p10"), profit_p90=(sell.get("range") or {}).get("p90"))  # fmt: skip
    if s.get("hold"):
        snap.update(noi=s["hold"]["noi"], yield_on_cost=s["hold"]["yield_on_cost"])
    return snap


def _parcel_for(conn, pin: str) -> tuple[str, str, str | None] | None:
    """(14-digit PIN, pin10, address) for a PIN or a 10-digit lot number."""
    return conn.execute(
        """select p.pin, p.pin10, a.address from parcel p left join parcel_address a on a.pin = p.pin
           where p.pin = %s or p.pin10 = %s order by (p.pin = %s) desc, p.tax_year desc, p.pin limit 1""",
        (pin, pin[:10], pin),
    ).fetchone()


SELECT = f"""
select {", ".join("d." + c for c in DEAL_FIELDS)}, {", ".join("s." + c for c in NIGHTLY_FIELDS)},
       p.community_area_name, ps.zone_class, ps.lot_sqft
from deal d
left join parcel_score s on s.pin10 = d.pin10
left join parcel p on p.pin = d.pin
left join parcel_site ps on ps.pin = d.pin
"""


def _row(r) -> dict:
    out = {k: _jsonable(v) for k, v in zip(DEAL_FIELDS, r[: len(DEAL_FIELDS)], strict=True)}
    n = dict(
        zip(NIGHTLY_FIELDS, (_jsonable(v) for v in r[len(DEAL_FIELDS) : len(DEAL_FIELDS) + 6]), strict=True)
    )
    out["stage_label"] = STAGES[out["stage"]]
    out["community_area"], out["zone_class"], lot = r[-3], r[-2], r[-1]
    out["lot_sqft"] = float(lot) if lot is not None else None
    out["nightly"] = None if n["score"] is None else {
        **n, "source": "25x125 nightly score, by-right program", "label": LABEL}  # fmt: skip
    return out


def _get(conn, deal_id: int) -> dict:
    r = conn.execute(SELECT + " where d.id = %s", (deal_id,)).fetchone()
    if r is None:
        raise HTTPException(404, f"deal {deal_id} not found")
    return _row(r)


def _list(conn, stage: str | None) -> list[dict]:
    where, args = "", []
    if stage:
        where, args = " where d.stage = %s", [_stage(stage)]
    return [_row(r) for r in conn.execute(SELECT + where + " order by d.updated_at desc, d.id desc", args)]


def _headline(d: dict) -> tuple:
    """(profit, max land, where the numbers came from, their date) for the table and CSV."""
    res, n = d.get("result"), d.get("nightly")
    if res:
        return res.get("profit"), res.get("max_land_price"), "saved feasibility run", res.get("run_on")
    if n:
        return n["profit_central"], n["max_land_price"], "nightly score (by right)", n["computed_on"]
    return None, None, "", ""


def _csv_response(rows: list[list], header: list[str], name: str) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={name}"})  # fmt: skip


DealsCaller = Annotated[Caller, Depends(needs("deals"))]


@router.get("/deals")
def list_deals(
    c: DealsCaller, stage: str | None = None, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json"
):
    """Saved deals, newest change first. format=csv returns one row per deal (import it back with POST /deals/import)."""
    if format == "csv":
        export_gate(c, "export.deals_csv")
    with scoped(connect(), c) as conn:
        deals = _list(conn, stage)
    if format == "json":
        return deals
    rows = []
    for d in deals:
        profit, max_land, src, on = _headline(d)
        rows.append([d["id"], d["pin"], d["pin10"], d["address"], d["community_area"], d["zone_class"], d["stage_label"],
                     d["next_step"], d["next_step_on"], d["scenario_name"], d["exit"],
                     round(profit) if profit is not None else "", round(max_land) if max_land is not None else "",
                     src, on, d["notes"], d["created_at"], d["updated_at"], json.dumps(d["overrides"])])  # fmt: skip
    return _csv_response(rows, CSV_COLUMNS, "25x125-deals.csv")


@router.get("/deals/pipeline")
def pipeline(c: DealsCaller) -> dict:
    """Deal counts by stage, for the pipeline tiles."""
    with scoped(connect(), c) as conn:
        got = dict(conn.execute("select stage, count(*) from deal group by stage").fetchall())
    counts = {k: got.get(k, 0) for k in STAGES}
    return {
        "total": sum(counts.values()),
        "stages": [{"id": k, "label": v, "count": counts[k]} for k, v in STAGES.items()],
    }


@router.get("/deals/events")
def all_events(c: DealsCaller, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json"):
    """Every outreach log entry across deals, oldest first. format=csv for a file."""
    if format == "csv":
        export_gate(c, "export.outreach_csv")
    with scoped(connect(), c) as conn:
        rows = conn.execute(
            """select e.id, e.deal_id, d.address, e.kind, e.event_on, e.note, e.created_at
               from deal_event e join deal d on d.id = e.deal_id order by e.event_on, e.id"""
        ).fetchall()
    if format == "csv":
        return _csv_response(
            [[_jsonable(v) for v in r] for r in rows], EVENT_COLUMNS, "25x125-outreach-log.csv"
        )
    return [dict(zip(EVENT_COLUMNS, (_jsonable(v) for v in r), strict=True)) for r in rows]


@router.post("/deals/import")
def import_deals(c: DealsCaller, text: Annotated[str, Body(media_type="text/csv")]) -> dict:
    """Create or update deals from a CSV file (the same columns the export writes).

    `pin` is required. A row with an `id` that exists updates that deal's stage, next step, date and notes;
    other rows create new deals. `overrides`, when present, is the JSON the feasibility screen saves.
    """
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames or "pin" not in [f.strip().lower() for f in reader.fieldnames]:
        raise HTTPException(400, "the CSV needs a header row with a pin column")
    created, updated, errors = 0, 0, []
    with scoped(connect(), c) as conn:
        for n, raw in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            try:
                stage = _stage(row["stage"]) if row.get("stage") else None
                on = date.fromisoformat(row["next_step_on"]) if row.get("next_step_on") else None
                overrides = json.loads(row["overrides"]) if row.get("overrides") else None
                if overrides is not None and not isinstance(overrides, dict):
                    raise ValueError("overrides must be a JSON object")
                existing = None
                if row.get("id"):
                    existing = conn.execute("select id from deal where id = %s", (int(row["id"]),)).fetchone()
                if existing:
                    conn.execute(
                        """update deal set stage = coalesce(%s, stage), next_step = coalesce(nullif(%s, ''), next_step),
                                  next_step_on = coalesce(%s, next_step_on), notes = coalesce(nullif(%s, ''), notes),
                                  overrides = coalesce(%s, overrides), updated_at = now() where id = %s""",
                        (stage, row.get("next_step", ""), on, row.get("notes", ""),
                         json.dumps(overrides) if overrides is not None else None, existing[0]),
                    )  # fmt: skip
                    updated += 1
                    continue
                pin = _clean_pin(row.get("pin", ""))
                found = _parcel_for(conn, pin)
                if found is None:
                    raise ValueError(f"PIN {pin} is not in the parcel table")
                conn.execute(
                    """insert into deal (pin, pin10, address, stage, next_step, next_step_on, notes, overrides, scenario_name)
                       values (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (found[0], found[1], row.get("address") or found[2], stage or "lead", row.get("next_step") or None,
                     on, row.get("notes") or None, json.dumps(overrides or {}), row.get("scenario_name") or None),
                )  # fmt: skip
                created += 1
            except (ValueError, KeyError, HTTPException) as e:
                errors.append(f"line {n}: {e.detail if isinstance(e, HTTPException) else e}")
        audit(conn, c, "deal.import", None, created=created, updated=updated, errors=len(errors))
    return {"created": created, "updated": updated, "errors": errors}


@router.post("/deals", status_code=201)
def create_deal(body: DealIn, c: DealsCaller) -> dict:
    """Save a parcel as a deal. With `exit` set, the engine runs feasibility with `overrides` and stores the
    chosen scenario's numbers and the run date."""
    pin = _clean_pin(body.pin)
    stage = _stage(body.stage)
    if body.exit not in (None, "sell", "hold"):
        raise HTTPException(400, "exit must be sell or hold")
    with scoped(connect(), c) as conn:
        found = _parcel_for(conn, pin)
        if found is None:
            raise HTTPException(404, f"PIN {pin} is not in the parcel table")
        result, name = None, None
        if body.exit:
            f = feasibility(conn, found[0], body.exit, body.overrides, body.target)
            result = _snapshot(f, body.scenario or 0) if f else None
            name = result["name"] if result else None
        deal_id = conn.execute(
            """insert into deal (org_id, pin, pin10, address, stage, next_step, next_step_on, exit, target, scenario,
                                 scenario_name, overrides, result, notes)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id""",
            (c.org_id, found[0], found[1], found[2], stage, body.next_step, body.next_step_on, body.exit, body.target,
             result["scenario"] if result else body.scenario, name, json.dumps(body.overrides),
             json.dumps(result) if result else None, body.notes),
        ).fetchone()[0]  # fmt: skip
        audit(conn, c, "deal.create", f"deal {deal_id}", pin=found[0], stage=stage, exit=body.exit,
              overrides=body.overrides)  # fmt: skip
        return _get(conn, deal_id)


@router.get("/deals/{deal_id}")
def get_deal(deal_id: int, c: DealsCaller) -> dict:
    """One deal with its outreach log."""
    with scoped(connect(), c) as conn:
        d = _get(conn, deal_id)
        d["events"] = _events(conn, deal_id)
    d["outreach_note"] = OUTREACH_NOTE
    return d


@router.patch("/deals/{deal_id}")
def update_deal(deal_id: int, body: DealPatch, c: DealsCaller) -> dict:
    """Change a deal's stage, next step, its date, notes or address. Fields left out stay as they are.

    Changing exit, target, scenario or overrides runs feasibility again and stores the new numbers.
    """
    changes = body.model_dump(exclude_unset=True)
    if "stage" in changes:
        changes["stage"] = _stage(changes["stage"] or "")
    if changes.get("exit") not in (None, "sell", "hold"):
        raise HTTPException(400, "exit must be sell or hold")
    rerun = any(k in changes for k in ("exit", "target", "scenario", "overrides"))
    logged = dict(changes)
    if "overrides" in changes:
        changes["overrides"] = json.dumps(changes["overrides"] or {})
    with scoped(connect(), c) as conn:
        _get(conn, deal_id)
        if changes:
            sets = ", ".join(f"{k} = %s" for k in changes)
            conn.execute(
                f"update deal set {sets}, updated_at = now() where id = %s", [*changes.values(), deal_id]
            )
        if rerun:
            _store_run(conn, deal_id)
        audit(
            conn, c, "override.save" if "overrides" in changes else "deal.update", f"deal {deal_id}", **logged
        )
        return _get(conn, deal_id)


def _store_run(conn, deal_id: int) -> None:
    d = _get(conn, deal_id)
    f = feasibility(conn, d["pin"], d["exit"] or "sell", d["overrides"] or {}, d["target"])
    result = _snapshot(f, d["scenario"] or 0) if f else None
    conn.execute(
        """update deal set result = %s, exit = coalesce(exit, 'sell'), scenario_name = coalesce(%s, scenario_name),
                  updated_at = now() where id = %s""",
        (json.dumps(result) if result else None, result["name"] if result else None, deal_id),
    )


@router.post("/deals/{deal_id}/rerun")
def rerun_deal(deal_id: int, c: DealsCaller) -> dict:
    """Run feasibility again with the deal's saved edits and store today's numbers."""
    with scoped(connect(), c) as conn:
        _store_run(conn, deal_id)
        audit(conn, c, "deal.rerun", f"deal {deal_id}")
        return _get(conn, deal_id)


@router.delete("/deals/{deal_id}", status_code=204)
def delete_deal(deal_id: int, c: DealsCaller) -> Response:
    """Delete a deal and its outreach log."""
    with scoped(connect(), c) as conn:
        if conn.execute("delete from deal where id = %s returning id", (deal_id,)).fetchone() is None:
            raise HTTPException(404, f"deal {deal_id} not found")
        audit(conn, c, "deal.delete", f"deal {deal_id}")
    return Response(status_code=204)


def _events(conn, deal_id: int) -> list[dict]:
    rows = conn.execute(
        "select id, kind, event_on, note, created_at from deal_event where deal_id = %s order by event_on, id",
        (deal_id,),
    ).fetchall()
    return [{"id": r[0], "kind": r[1], "kind_label": EVENT_KINDS[r[1]], "event_on": r[2].isoformat(), "note": r[3],
             "created_at": r[4].isoformat()} for r in rows]  # fmt: skip


@router.get("/deals/{deal_id}/events")
def list_events(deal_id: int, c: DealsCaller, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json"):
    """One deal's outreach log, oldest first."""
    if format == "csv":
        export_gate(c, "export.outreach_csv", f"deal {deal_id}")
    with scoped(connect(), c) as conn:
        d = _get(conn, deal_id)
        events = _events(conn, deal_id)
    if format == "csv":
        rows = [
            [e["id"], deal_id, d["address"], e["kind"], e["event_on"], e["note"], e["created_at"]]
            for e in events
        ]
        return _csv_response(rows, EVENT_COLUMNS, f"25x125-outreach-deal-{deal_id}.csv")
    return events


@router.post("/deals/{deal_id}/events", status_code=201)
def add_event(deal_id: int, body: EventIn, c: DealsCaller) -> dict:
    """Log an owner contact, a note or a reminder. Calls and texts follow TCPA rules; email follows CAN-SPAM."""
    if body.kind not in EVENT_KINDS:
        raise HTTPException(400, f"kind must be one of {', '.join(EVENT_KINDS)}")
    with scoped(connect(), c) as conn:
        _get(conn, deal_id)
        eid = conn.execute(
            "insert into deal_event (deal_id, kind, event_on, note) values (%s, %s, coalesce(%s, current_date), %s) returning id",
            (deal_id, body.kind, body.event_on, body.note),
        ).fetchone()[0]
        conn.execute("update deal set updated_at = now() where id = %s", (deal_id,))
        audit(conn, c, "deal_event.create", f"deal {deal_id}", kind=body.kind)
        return next(e for e in _events(conn, deal_id) if e["id"] == eid)


@router.delete("/deals/{deal_id}/events/{event_id}", status_code=204)
def delete_event(deal_id: int, event_id: int, c: DealsCaller) -> Response:
    with scoped(connect(), c) as conn:
        gone = conn.execute(
            "delete from deal_event where id = %s and deal_id = %s returning id", (event_id, deal_id)
        ).fetchone()
        if gone is not None:
            audit(conn, c, "deal_event.delete", f"deal {deal_id}", event=event_id)
    if gone is None:
        raise HTTPException(404, f"event {event_id} not found on deal {deal_id}")
    return Response(status_code=204)
