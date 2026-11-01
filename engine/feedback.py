"""Feedback on the app's numbers, for the contractor trial (2026-11): a rating, the person's own cost and sale
figures, and what was wrong or missing, stored next to a snapshot of the app's figures on screen at the time.

Anyone signed in may send it; signed-out people send it with an email address. It is product-owner data, not
organization data: the engine writes it as the database owner, and only product admins (ADMIN_EMAILS) read it.
Sends are rate limited (data/rules/rate_limits.json, bucket "feedback") and logged in the audit log when signed in.
"""

import csv
import io
from statistics import median
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from core.db import connect
from engine.accounts import clean_email
from engine.auth import Caller, admin, audit, check_rate, signed, user_email

router = APIRouter()

TEXT_MAX = 4000
SNAPSHOT_NUMBERS = ["total_cost", "cost_per_unit", "hard_cost_per_sqft", "total_cost_per_sqft", "sale_per_unit",
                    "profit", "max_land_price", "cost_index", "area_adjustment", "units", "gross_sqft",
                    "edits"]  # fmt: skip
SNAPSHOT_TEXT = ["preset", "exit", "scenario_name", "stage", "address"]
# Each comparison: the person's figure, the app's figure in the snapshot, and what to call it.
COMPARISONS = [
    ("cost_per_sqft", "cost_per_sqft_own", "hard_cost_per_sqft", "Hard cost per sq ft"),
    ("cost_total", "cost_total_own", "total_cost", "Total cost"),
    ("sale_per_unit", "sale_per_unit_own", "sale_per_unit", "Sale price per unit"),
]
COLUMNS = ["id", "created_at", "email", "user_id", "org_id", "page_path", "pin", "scenario", "screen", "rating",
           "cost_per_sqft_own", "cost_total_own", "sale_per_unit_own", "numbers_wrong", "outside_questions",
           "missing", "minutes_spent", "would_use", "notes", "app_snapshot"]  # fmt: skip


class Snapshot(BaseModel):
    """The app's figures on screen when the form was opened. Dollars unless named otherwise."""

    total_cost: float | None = None
    cost_per_unit: float | None = None
    hard_cost_per_sqft: float | None = None
    total_cost_per_sqft: float | None = None
    sale_per_unit: float | None = None
    profit: float | None = None
    max_land_price: float | None = None
    cost_index: float | None = None
    area_adjustment: float | None = None
    units: float | None = None
    gross_sqft: float | None = None
    edits: float | None = None
    preset: str | None = Field(None, max_length=40)
    exit: str | None = Field(None, max_length=10)
    scenario_name: str | None = Field(None, max_length=200)
    stage: str | None = Field(None, max_length=40)
    address: str | None = Field(None, max_length=200)

    @field_validator(*SNAPSHOT_NUMBERS)
    @classmethod
    def finite(cls, v):
        if v is not None and not (-1e10 < v < 1e10):
            raise ValueError("out of range")
        return v


Money = Annotated[float | None, Field(None, ge=0, le=1e9)]
Text = Annotated[str | None, Field(None, max_length=TEXT_MAX)]


class FeedbackIn(BaseModel):
    email: str | None = Field(None, max_length=254)
    page_path: str | None = Field(None, max_length=300)
    pin: str | None = Field(None, max_length=20)
    scenario: Literal["A", "B", "C"] | None = None
    screen: str | None = Field(None, max_length=40, pattern=r"^[a-z_]+$")
    rating: int | None = Field(
        None, ge=1, le=5, description="How close were the numbers to what you would expect?"
    )
    cost_per_sqft_own: Annotated[float | None, Field(None, ge=0, le=10_000)] = None
    cost_total_own: Money = None
    sale_per_unit_own: Money = None
    numbers_wrong: Text = None
    outside_questions: Text = None
    missing: Text = None
    minutes_spent: int | None = Field(None, ge=0, le=1440)
    would_use: Literal["yes", "maybe", "no"] | None = None
    notes: Text = None
    app_snapshot: Snapshot = Field(default_factory=Snapshot)

    @field_validator("pin")
    @classmethod
    def digits(cls, v):
        if v is None or v == "":
            return None
        d = v.replace("-", "")
        if not d.isdigit() or len(d) not in (10, 14):
            raise ValueError("PIN must be 10 or 14 digits")
        return d

    @field_validator("numbers_wrong", "outside_questions", "missing", "notes", "page_path", "email")
    @classmethod
    def strip(cls, v):
        v = v.strip() if isinstance(v, str) else v
        return v or None


def _audit_signed_in(conn: psycopg.Connection, c: Caller, action: str, target: str | None, **detail) -> None:
    """Audit log row for a signed-in caller with an organization (the audit log is organization-scoped)."""
    if not c.user_id or not c.org_id:
        return
    conn.execute("select set_config('app.org_id', %s, true)", (c.org_id,))
    audit(conn, c, action, target, **detail)


@router.post("/feedback", status_code=201)
def send_feedback(body: FeedbackIn, c: Annotated[Caller, Depends(signed)]) -> dict:
    """Save one feedback entry. Signed in: the account's email is used. Signed out: an email is required."""
    check_rate("feedback", c.key)
    if not any([body.rating, body.cost_per_sqft_own, body.cost_total_own, body.sale_per_unit_own,
                body.numbers_wrong, body.outside_questions, body.missing, body.would_use, body.notes]):  # fmt: skip
        raise HTTPException(400, "Fill in at least one answer before sending.")
    with connect() as conn:
        email = user_email(conn, c.user_id)
        uid = c.user_id if email else None
        if email is None:
            if not body.email:
                raise HTTPException(400, "Enter your email address so we can follow up, or sign in.")
            email = clean_email(body.email)
        org_id = c.org_id if uid else None
        if org_id and not conn.execute("select 1 from org where id = %s", (org_id,)).fetchone():
            org_id = None
        snap = body.app_snapshot.model_dump(exclude_none=True)
        row = conn.execute(
            """insert into feedback (user_id, email, org_id, page_path, pin, scenario, screen, rating,
                 cost_per_sqft_own, cost_total_own, sale_per_unit_own, numbers_wrong, outside_questions, missing,
                 minutes_spent, would_use, notes, app_snapshot)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               returning id, created_at""",
            (uid, email, org_id, body.page_path, body.pin, body.scenario,
             body.screen or ("feasibility" if body.pin else "general"), body.rating, body.cost_per_sqft_own,
             body.cost_total_own, body.sale_per_unit_own, body.numbers_wrong, body.outside_questions, body.missing,
             body.minutes_spent, body.would_use, body.notes, psycopg.types.json.Jsonb(snap)),
        ).fetchone()  # fmt: skip
        if org_id:
            _audit_signed_in(
                conn, c, "feedback.create", f"feedback {row[0]}", pin=body.pin, scenario=body.scenario
            )
    return {"id": row[0], "created_at": row[1].isoformat()}


def _cell(v):
    """CSV cell: whole-dollar floats without a trailing .0."""
    return int(v) if isinstance(v, float) and v.is_integer() else v


def _num(v):
    return None if v is None else float(v)


def _rows(conn: psycopg.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        f"select {', '.join(COLUMNS)} from feedback order by created_at desc, id desc limit %s", (limit,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(zip(COLUMNS, r, strict=True))
        d["created_at"] = d["created_at"].isoformat()
        for k in ("cost_per_sqft_own", "cost_total_own", "sale_per_unit_own"):
            d[k] = _num(d[k])
        d["comparisons"] = _compare(d)
        out.append(d)
    return out


def _compare(d: dict) -> dict:
    """Per entry: the person's figure minus the app's, in dollars, and their ratio."""
    snap = d.get("app_snapshot") or {}
    out = {}
    for key, own_f, app_f, _ in COMPARISONS:
        own, app_v = d.get(own_f), snap.get(app_f)
        if own is None or app_v is None or app_v <= 0:
            continue
        out[key] = {"own": own, "app": app_v, "difference": own - app_v, "ratio": round(own / app_v, 4)}
    return out


def _spread(values: list[float]) -> dict | None:
    if not values:
        return None
    return {"median": round(median(values), 4), "low": round(min(values), 4), "high": round(max(values), 4)}


def summary_of(rows: list[dict]) -> dict:
    ratings = [r["rating"] for r in rows if r["rating"] is not None]
    comps = {}
    for key, _, _, label in COMPARISONS:
        pairs = [r["comparisons"][key] for r in rows if key in r["comparisons"]]
        comps[key] = {
            "label": f"Your {label.lower()} / the app's",
            "n": len(pairs),
            "ratio": _spread([p["ratio"] for p in pairs]),
            "difference": _spread([p["difference"] for p in pairs]),
            "own_median": round(median([p["own"] for p in pairs]), 2) if pairs else None,
            "app_median": round(median([p["app"] for p in pairs]), 2) if pairs else None,
        }
    uses = [r["would_use"] for r in rows if r["would_use"]]
    return {
        "count": len(rows),
        "rating": {"n": len(ratings), "median": median(ratings) if ratings else None},
        "comparisons": comps,
        "would_use": {k: uses.count(k) for k in ("yes", "maybe", "no")},
        "minutes_spent": {
            "n": sum(1 for r in rows if r["minutes_spent"] is not None),
            "total": sum(r["minutes_spent"] or 0 for r in rows),
        },
        "note": "Ratio above 1: your figure is higher than the app's. Difference is your figure minus the app's, in dollars.",
    }


@router.get("/feedback")
def list_feedback(
    c: Annotated[Caller, Depends(admin)], limit: Annotated[int, Query(ge=1, le=5000)] = 500
) -> list:
    """Feedback entries, newest first, each with its comparison to the app's figures (product admins only)."""
    with connect() as conn:
        return _rows(conn, limit)


@router.get("/feedback/summary")
def feedback_summary(c: Annotated[Caller, Depends(admin)]) -> dict:
    """Count, median rating, and how far the app's figures are from the people's own: ratio and dollars."""
    with connect() as conn:
        return summary_of(_rows(conn, 100_000))


@router.get("/feedback.csv")
def feedback_csv(c: Annotated[Caller, Depends(admin)]) -> Response:
    """Every entry as CSV, with the app's figures and the comparisons in their own columns (logged)."""
    with connect() as conn:
        rows = _rows(conn, 100_000)
        _audit_signed_in(conn, c, "export.feedback_csv", None, rows=len(rows))
    snap_cols = SNAPSHOT_NUMBERS + SNAPSHOT_TEXT
    comp_cols = [f"{k}_{m}" for k, *_ in COMPARISONS for m in ("difference", "ratio")]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([c for c in COLUMNS if c != "app_snapshot"] + [f"app_{k}" for k in snap_cols] + comp_cols)
    for r in rows:
        snap = r["app_snapshot"] or {}
        cells = (
            [r[k] for k in COLUMNS if k != "app_snapshot"]
            + [snap.get(k) for k in snap_cols]
            + [r["comparisons"].get(k, {}).get(m) for k, *_ in COMPARISONS for m in ("difference", "ratio")]
        )
        w.writerow([_cell(v) for v in cells])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=25x125-feedback.csv"})  # fmt: skip


@router.delete("/feedback/{feedback_id}", status_code=204)
def delete_feedback(feedback_id: int, c: Annotated[Caller, Depends(admin)]) -> Response:
    """Remove one entry (a test entry, or on request)."""
    with connect() as conn:
        gone = conn.execute("delete from feedback where id = %s returning id", (feedback_id,)).fetchone()
        if gone is None:
            raise HTTPException(404, "No such feedback entry.")
        _audit_signed_in(conn, c, "feedback.delete", f"feedback {feedback_id}")
    return Response(status_code=204)
