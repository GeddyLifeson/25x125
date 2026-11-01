"""Email sign-in, sessions, organizations, invites, saved searches, saved feasibility edits, export checks
and data deletion.

The /auth routes take signed calls from the web app only (engine/auth.py). The web app keeps the session
token in an http-only cookie; the database keeps only its SHA-256 hash.
"""

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote

import psycopg
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.db import connect
from engine import billing, mail
from engine.auth import (
    Caller,
    admin_emails,
    audit,
    check_rate,
    effective_plan,
    features,
    is_production,
    load_member,
    member,
    needs,
    owner,
    plans,
    scoped,
    signed,
    token_hash,
)

router = APIRouter()

LINK_MINUTES = 30
SESSION_DAYS = 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
EXPORT_KINDS = {"pdf": "export.pdf", "feasibility_csv": "export.feasibility_csv"}


def clean_email(email: str) -> str:
    e = (email or "").strip().lower()
    if len(e) > 254 or not EMAIL_RE.match(e):
        raise HTTPException(400, "Enter a valid email address.")
    return e


def _safe_next(path: str | None) -> str:
    return path if path and path.startswith("/") and not path.startswith("//") else "/"


class LinkIn(BaseModel):
    email: str
    base_url: str
    next: str | None = None


class TokenIn(BaseModel):
    token: str


class SwitchIn(BaseModel):
    session_token: str
    org_id: str


@router.get("/auth/config")
def auth_config() -> dict:
    """What the sign-in page needs to know: whether links go to the console (dev mode) instead of an inbox."""
    return {"email_dev_mode": mail.dev_mode() and not is_production(), "link_minutes": LINK_MINUTES}


@router.post("/auth/email-link")
def email_link(body: LinkIn, c: Annotated[Caller, Depends(signed)]) -> dict:
    """Email a one-use sign-in link (30 minutes). Dev mode (no EMAIL_SERVER): the link goes to the console."""
    email = clean_email(body.email)
    if not body.base_url.startswith(("http://", "https://")):
        raise HTTPException(400, "base_url must be the web app's address")
    if mail.dev_mode() and is_production():
        raise HTTPException(503, "Sign-in email is not set up yet (EMAIL_SERVER).")
    check_rate("sign_in_ip", c.key)
    check_rate("sign_in_email", email)
    token = secrets.token_urlsafe(32)
    nxt = _safe_next(body.next)
    with connect() as conn:
        conn.execute(
            "insert into auth_token (token_hash, email, next_path, expires_at) values (%s, %s, %s, %s)",
            (token_hash(token), email, nxt, datetime.now(UTC) + timedelta(minutes=LINK_MINUTES)),
        )
    link = f"{body.base_url.rstrip('/')}/api/auth/callback?token={quote(token)}"
    sent = mail.send(email, "Your 25x125 sign-in link", mail.sign_in_text(link, LINK_MINUTES))
    return {"sent": sent, "dev_mode": not sent}


def _new_org(conn, user_id: str, name: str, trial: bool) -> str:
    days = plans()["trial_days"]
    org_id = conn.execute(
        """insert into org (name, plan, plan_status, trial_ends_at, plan_updated_at)
           values (%s, %s, %s, %s, now()) returning id""",
        (name, "pro" if trial else "free", "trialing" if trial else "none",
         datetime.now(UTC) + timedelta(days=days) if trial else None),
    ).fetchone()[0]  # fmt: skip
    conn.execute("insert into membership (org_id, user_id, role) values (%s, %s, 'owner')", (org_id, user_id))
    conn.execute("update account_user set trial_used = true where id = %s", (user_id,))
    return org_id


def _accept_invites(conn, user_id: str, email: str) -> list[str]:
    rows = conn.execute(
        """update org_invite set accepted_at = now()
           where email = %s and accepted_at is null and expires_at > now() returning org_id""",
        (email,),
    ).fetchall()
    for (org_id,) in rows:
        conn.execute(
            "insert into membership (org_id, user_id, role) values (%s, %s, 'member') on conflict do nothing",
            (org_id, user_id),
        )
    return [r[0] for r in rows]


def _first_org(conn, user_id: str) -> str | None:
    row = conn.execute(
        "select org_id from membership where user_id = %s order by (role = 'owner') desc, created_at limit 1",
        (user_id,),
    ).fetchone()
    return row[0] if row else None


@router.post("/auth/verify")
def verify(body: TokenIn, c: Annotated[Caller, Depends(signed)]) -> dict:
    """Use a sign-in link: creates the user on first sign-in (with an organization and a 14-day Pro trial,
    unless an invite is waiting), accepts invites for this email, and starts a 30-day session."""
    with connect() as conn:
        row = conn.execute(
            """update auth_token set used_at = now()
               where token_hash = %s and used_at is null and expires_at > now() returning email, next_path""",
            (token_hash(body.token),),
        ).fetchone()
        if row is None:
            raise HTTPException(400, "This sign-in link has expired or was already used. Ask for a new one.")
        email, nxt = row
        user = conn.execute("select id, trial_used from account_user where email = %s", (email,)).fetchone()
        if user is None:
            user = conn.execute(
                "insert into account_user (email) values (%s) returning id, trial_used", (email,)
            ).fetchone()
        user_id, trial_used = user
        joined = _accept_invites(conn, user_id, email)
        org_id = joined[0] if joined else _first_org(conn, user_id)
        if org_id is None:
            org_id = _new_org(conn, user_id, email, trial=not trial_used)
        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(days=SESSION_DAYS)
        conn.execute(
            "insert into auth_session (token_hash, user_id, org_id, expires_at) values (%s, %s, %s, %s)",
            (token_hash(token), user_id, org_id, expires),
        )
        conn.execute("update account_user set last_sign_in_at = now() where id = %s", (user_id,))
        conn.execute("select set_config('app.org_id', %s, true)", (org_id,))
        conn.execute(
            "insert into audit_log (org_id, user_id, action, ip) values (%s, %s, 'auth.sign_in', %s)",
            (org_id, user_id, c.ip),
        )
    return {"session_token": token, "expires_at": expires.isoformat(), "next": _safe_next(nxt)}


def _org_view(conn, org_id: str, user_id: str) -> dict | None:
    row = conn.execute(
        """select o.id, o.name, m.role, o.plan, o.plan_status, o.trial_ends_at, o.founding, o.current_period_end,
                  o.stripe_customer_id is not null
           from org o join membership m on m.org_id = o.id where o.id = %s and m.user_id = %s""",
        (org_id, user_id),
    ).fetchone()
    if row is None:
        return None
    plan = effective_plan(row[3], row[4], row[5])
    return {
        "id": row[0], "name": row[1], "role": row[2], "plan": plan, "plan_label": plans()["plans"][plan]["label"],
        "plan_status": row[4], "trial_ends_at": row[5].isoformat() if row[5] else None, "founding": row[6],
        "current_period_end": row[7].isoformat() if row[7] else None, "has_billing": row[8],
        "features": sorted(features(plan)),
    }  # fmt: skip


@router.post("/auth/session")
def session(body: Annotated[dict, Body()], c: Annotated[Caller, Depends(signed)]) -> dict:
    """The user and organization behind a session token; 401 when it is unknown or expired."""
    th = token_hash(str(body.get("session_token") or ""))
    with connect() as conn:
        row = conn.execute(
            """select s.user_id, s.org_id, u.email, u.name, s.expires_at, s.last_seen_at, u.trial_used
               from auth_session s join account_user u on u.id = s.user_id
               where s.token_hash = %s and s.expires_at > now()""",
            (th,),
        ).fetchone()
        if row is None:
            raise HTTPException(401, "Signed out. Sign in again.")
        user_id, org_id = row[0], row[1]
        org = _org_view(conn, org_id, user_id) if org_id else None
        if org is None:  # removed from that organization, or it was deleted
            org_id = _first_org(conn, user_id) or _new_org(conn, user_id, row[2], trial=not row[6])
            org = _org_view(conn, org_id, user_id)
            conn.execute("update auth_session set org_id = %s where token_hash = %s", (org_id, th))
        if row[5] < datetime.now(UTC) - timedelta(hours=1):
            conn.execute("update auth_session set last_seen_at = now() where token_hash = %s", (th,))
        orgs = conn.execute(
            """select o.id, o.name, m.role from membership m join org o on o.id = m.org_id
               where m.user_id = %s order by o.name""",
            (user_id,),
        ).fetchall()
    return {
        "user": {"id": user_id, "email": row[2], "name": row[3]},
        "is_admin": row[2] in admin_emails(),
        "org": org,
        "orgs": [{"id": r[0], "name": r[1], "role": r[2]} for r in orgs],
        "expires_at": row[4].isoformat(),
    }


@router.post("/auth/signout")
def signout(body: Annotated[dict, Body()], c: Annotated[Caller, Depends(signed)]) -> dict:
    with connect() as conn:
        conn.execute(
            "delete from auth_session where token_hash = %s",
            (token_hash(str(body.get("session_token") or "")),),
        )
    return {"signed_out": True}


@router.post("/auth/switch-org")
def switch_org(body: SwitchIn, c: Annotated[Caller, Depends(signed)]) -> dict:
    """Work in another organization the user belongs to."""
    th = token_hash(body.session_token)
    with connect() as conn:
        ok = conn.execute(
            """update auth_session s set org_id = %s from membership m
               where s.token_hash = %s and s.expires_at > now() and m.user_id = s.user_id and m.org_id = %s
               returning s.user_id""",
            (body.org_id, th, body.org_id),
        ).fetchone()
    if ok is None:
        raise HTTPException(403, "You are not a member of that organization.")
    return {"org_id": body.org_id}


# ---- the organization ----


@router.get("/account")
def account(c: Annotated[Caller, Depends(member)]) -> dict:
    """The organization, its members and open invites, the plan, and the plans on offer."""
    with connect() as conn:
        org = _org_view(conn, c.org_id, c.user_id)
        members = conn.execute(
            """select u.id, u.email, m.role, m.created_at from membership m join account_user u on u.id = m.user_id
               where m.org_id = %s order by (m.role = 'owner') desc, u.email""",
            (c.org_id,),
        ).fetchall()
        invites = conn.execute(
            """select id, email, created_at, expires_at from org_invite
               where org_id = %s and accepted_at is null and expires_at > now() order by created_at""",
            (c.org_id,),
        ).fetchall()
    return {
        "user": {"id": c.user_id, "email": c.email},
        "org": org,
        "members": [
            {"id": r[0], "email": r[1], "role": r[2], "since": r[3].date().isoformat()} for r in members
        ],
        "invites": [
            {"id": r[0], "email": r[1], "sent": r[2].date().isoformat(), "expires": r[3].date().isoformat()}
            for r in invites
        ],
        "plans": plans(),
    }


class OrgPatch(BaseModel):
    name: str = Field(min_length=1, max_length=120)


@router.patch("/account/org")
def rename_org(body: OrgPatch, c: Annotated[Caller, Depends(owner)]) -> dict:
    with connect() as conn:
        conn.execute("update org set name = %s where id = %s", (body.name.strip(), c.org_id))
    with scoped(connect(), c) as conn:
        audit(conn, c, "org.rename", c.org_id, name=body.name.strip())
    return {"name": body.name.strip()}


class InviteIn(BaseModel):
    email: str
    base_url: str


@router.post("/account/invites", status_code=201)
def invite(body: InviteIn, c: Annotated[Caller, Depends(owner)]) -> dict:
    """Invite a teammate by email. They join when they sign in with that address."""
    if "invites" not in c.features:
        raise HTTPException(402, "Teammates are part of Pro.")
    email = clean_email(body.email)
    check_rate("invite", c.key)
    with connect() as conn:
        if conn.execute(
            """select 1 from membership m join account_user u on u.id = m.user_id
               where m.org_id = %s and u.email = %s""",
            (c.org_id, email),
        ).fetchone():
            raise HTTPException(409, f"{email} is already a member.")
        iid = conn.execute(
            """insert into org_invite (org_id, email, invited_by) values (%s, %s, %s)
               on conflict (org_id, email) do update set created_at = now(), expires_at = now() + interval '14 days',
                 accepted_at = null, invited_by = excluded.invited_by
               returning id""",
            (c.org_id, email, c.user_id),
        ).fetchone()[0]
        org_name = conn.execute("select name from org where id = %s", (c.org_id,)).fetchone()[0]
    link = f"{body.base_url.rstrip('/')}/signin?email={quote(email)}"
    sent = mail.send(
        email, f"Join {org_name} on 25x125", mail.invite_text(org_name, c.email or "A teammate", link)
    )
    with scoped(connect(), c) as conn:
        audit(conn, c, "invite.create", email)
    return {"id": iid, "email": email, "sent": sent}


@router.delete("/account/invites/{invite_id}", status_code=204)
def cancel_invite(invite_id: int, c: Annotated[Caller, Depends(owner)]) -> Response:
    with connect() as conn:
        gone = conn.execute(
            "delete from org_invite where id = %s and org_id = %s returning email", (invite_id, c.org_id)
        ).fetchone()
    if gone is None:
        raise HTTPException(404, "invite not found")
    with scoped(connect(), c) as conn:
        audit(conn, c, "invite.cancel", gone[0])
    return Response(status_code=204)


@router.delete("/account/members/{user_id}", status_code=204)
def remove_member(user_id: str, c: Annotated[Caller, Depends(owner)]) -> Response:
    if user_id == c.user_id:
        raise HTTPException(400, "The owner cannot leave. Delete the account instead.")
    with connect() as conn:
        gone = conn.execute(
            "delete from membership where org_id = %s and user_id = %s returning user_id", (c.org_id, user_id)
        ).fetchone()
    if gone is None:
        raise HTTPException(404, "member not found")
    with scoped(connect(), c) as conn:
        audit(conn, c, "member.remove", user_id)
    return Response(status_code=204)


@router.get("/account/audit")
def audit_log(c: Annotated[Caller, Depends(owner)], limit: int = 200) -> list[dict]:
    """The organization's audit log, newest first (owner only)."""
    with scoped(connect(), c) as conn:
        rows = conn.execute(
            """select a.created_at, u.email, a.action, a.target, a.detail from audit_log a
               left join account_user u on u.id = a.user_id order by a.created_at desc, a.id desc limit %s""",
            (min(limit, 1000),),
        ).fetchall()
    return [
        {"at": r[0].isoformat(), "who": r[1], "action": r[2], "target": r[3], "detail": r[4]} for r in rows
    ]


# ---- data deletion ----


def delete_user(conn: psycopg.Connection, user_id: str, requested_by: str) -> dict:
    """Delete a user. Organizations they own with teammates pass to the longest-standing member; organizations
    they own alone go too, with all their deals, outreach log,
    saved searches, saved edits, invites and audit log; their Stripe subscription is canceled when billing is
    set up. Other members keep their accounts. Records the deletion without the email address.

    Runs on a plain connection (the database owner), outside row-level security."""
    user = conn.execute("select email from account_user where id = %s", (user_id,)).fetchone()
    if user is None:
        raise HTTPException(404, "user not found")
    owned = conn.execute(
        """select o.id, o.stripe_subscription_id from membership m join org o on o.id = m.org_id
           where m.user_id = %s and m.role = 'owner'""",
        (user_id,),
    ).fetchall()
    counts: dict[str, int] = {}
    canceled = 0
    handed_over = 0
    kept = []
    for org_id, sub in owned:
        # An organization with teammates passes to its longest-standing member instead of being deleted.
        heir = conn.execute(
            "select user_id from membership where org_id = %s and user_id <> %s order by created_at, user_id limit 1",
            (org_id, user_id),
        ).fetchone()
        if heir:
            conn.execute("delete from membership where org_id = %s and user_id = %s", (org_id, user_id))
            conn.execute(
                "update membership set role = 'owner' where org_id = %s and user_id = %s", (org_id, heir[0])
            )
            handed_over += 1
            continue
        kept.append((org_id, sub))
    owned = kept
    for org_id, sub in owned:
        conn.execute("select set_config('app.org_id', %s, true)", (org_id,))
        for t in ("deal", "deal_event", "saved_search", "saved_override", "audit_log"):
            n = conn.execute(f"select count(*) from {t} where org_id = %s", (org_id,)).fetchone()[0]
            counts[t] = counts.get(t, 0) + n
        counts["other_members"] = (
            counts.get("other_members", 0)
            + conn.execute(
                "select count(*) from membership where org_id = %s and user_id <> %s", (org_id, user_id)
            ).fetchone()[0]
        )
        canceled += billing.cancel_subscription(sub)
        conn.execute("delete from org where id = %s", (org_id,))
    # Feedback on the app's numbers stays for the product owner, without the person's email or account.
    n = conn.execute(
        "update feedback set email = null, user_id = null where user_id = %s or email = %s",
        (user_id, user[0]),
    ).rowcount
    if n:
        counts["feedback_anonymized"] = n
    conn.execute("delete from auth_token where email = %s", (user[0],))
    conn.execute("delete from org_invite where email = %s", (user[0],))
    conn.execute("delete from account_user where id = %s", (user_id,))
    conn.execute(
        "insert into deletion_log (email_sha256, orgs_deleted, rows_deleted, requested_by) values (%s, %s, %s, %s)",
        (
            hashlib.sha256(user[0].encode()).hexdigest(),
            len(owned),
            psycopg.types.json.Jsonb(counts),
            requested_by,
        ),
    )
    return {"email": user[0], "orgs_deleted": len(owned), "rows_deleted": counts,
            "orgs_handed_over": handed_over, "subscriptions_canceled": canceled}  # fmt: skip


@router.delete("/account")
def delete_account(c: Annotated[Caller, Depends(member)], confirm: Annotated[str, Query()] = "") -> dict:
    """Delete the signed-in user's account and data. `confirm` must be the account's email address."""
    if confirm.strip().lower() != (c.email or ""):
        raise HTTPException(400, "To delete the account, confirm with its email address.")
    with connect() as conn:
        return delete_user(conn, c.user_id, "self")


# ---- saved searches and saved feasibility edits ----


class SearchIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    params: str = Field(max_length=2000)


@router.get("/saved-searches")
def list_searches(c: Annotated[Caller, Depends(needs("saved_searches"))]) -> list[dict]:
    with scoped(connect(), c) as conn:
        rows = conn.execute(
            "select id, name, params, created_at from saved_search order by created_at desc"
        ).fetchall()
    return [{"id": r[0], "name": r[1], "params": r[2], "created_at": r[3].isoformat()} for r in rows]


@router.post("/saved-searches", status_code=201)
def save_search(body: SearchIn, c: Annotated[Caller, Depends(needs("saved_searches"))]) -> dict:
    params = body.params.lstrip("?")
    with scoped(connect(), c) as conn:
        sid = conn.execute(
            "insert into saved_search (user_id, name, params) values (%s, %s, %s) returning id",
            (c.user_id, body.name.strip(), params),
        ).fetchone()[0]
        audit(conn, c, "search.save", f"saved search {sid}", params=params)
    return {"id": sid, "name": body.name.strip(), "params": params}


@router.delete("/saved-searches/{search_id}", status_code=204)
def delete_search(search_id: int, c: Annotated[Caller, Depends(needs("saved_searches"))]) -> Response:
    with scoped(connect(), c) as conn:
        if (
            conn.execute("delete from saved_search where id = %s returning id", (search_id,)).fetchone()
            is None
        ):
            raise HTTPException(404, "saved search not found")
        audit(conn, c, "search.delete", f"saved search {search_id}")
    return Response(status_code=204)


class OverrideIn(BaseModel):
    exit: str | None = None
    target: str | None = None
    overrides: dict = Field(default_factory=dict)


def _pin(pin: str) -> str:
    pin = pin.replace("-", "").strip()
    if not pin.isdigit() or len(pin) not in (10, 14):
        raise HTTPException(400, "PIN must be 10 or 14 digits")
    return pin


@router.get("/overrides/{pin}")
def get_overrides(pin: str, c: Annotated[Caller, Depends(needs("saved_edits"))]) -> dict:
    """The feasibility edits saved to the organization for this parcel; 404 when none."""
    with scoped(connect(), c) as conn:
        row = conn.execute(
            """select s.exit, s.target, s.overrides, s.updated_at, u.email from saved_override s
               left join account_user u on u.id = s.updated_by where s.pin = %s""",
            (_pin(pin),),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "no saved edits for this parcel")
    return {"pin": _pin(pin), "exit": row[0], "target": row[1], "overrides": row[2],
            "updated_at": row[3].isoformat(), "updated_by": row[4]}  # fmt: skip


@router.put("/overrides/{pin}")
def put_overrides(pin: str, body: OverrideIn, c: Annotated[Caller, Depends(needs("saved_edits"))]) -> dict:
    """Save this parcel's feasibility edits to the organization (replaces the earlier ones)."""
    if body.exit not in (None, "sell", "hold"):
        raise HTTPException(400, "exit must be sell or hold")
    p = _pin(pin)
    with scoped(connect(), c) as conn:
        conn.execute(
            """insert into saved_override (pin, exit, target, overrides, updated_by) values (%s, %s, %s, %s, %s)
               on conflict (org_id, pin) do update set exit = excluded.exit, target = excluded.target,
                 overrides = excluded.overrides, updated_by = excluded.updated_by, updated_at = now()""",
            (p, body.exit, body.target, psycopg.types.json.Jsonb(body.overrides), c.user_id),
        )
        audit(
            conn, c, "override.save", f"PIN {p}", exit=body.exit, target=body.target, overrides=body.overrides
        )
    return get_overrides(p, c)


@router.delete("/overrides/{pin}", status_code=204)
def delete_overrides(pin: str, c: Annotated[Caller, Depends(needs("saved_edits"))]) -> Response:
    p = _pin(pin)
    with scoped(connect(), c) as conn:
        conn.execute("delete from saved_override where pin = %s", (p,))
        audit(conn, c, "override.delete", f"PIN {p}")
    return Response(status_code=204)


class ExportIn(BaseModel):
    kind: str
    target: str | None = None


@router.post("/exports")
def export_check(body: ExportIn, c: Annotated[Caller, Depends(needs("exports"))]) -> dict:
    """Called by the web app before it builds a PDF or CSV: checks the plan and the rate limit, and logs it."""
    if body.kind not in EXPORT_KINDS:
        raise HTTPException(400, f"kind must be one of {', '.join(EXPORT_KINDS)}")
    check_rate("export", c.key)
    with scoped(connect(), c) as conn:
        audit(conn, c, EXPORT_KINDS[body.kind], body.target)
    return {"ok": True}


def export_gate(c: Caller, what: str, target: str | None = None) -> None:
    """Plan check, rate limit and audit row for an export the engine builds itself (deals CSV, list CSV)."""
    if "exports" not in c.features:
        raise HTTPException(402, "PDF and CSV exports are part of Pro.")
    check_rate("export", c.key)
    with scoped(connect(), c) as conn:
        audit(conn, c, what, target)


def member_or_401(c: Caller) -> Caller:
    """The member behind a caller resolved without FastAPI's dependency injection."""
    if not c.signed or not c.user_id or not c.org_id:
        raise HTTPException(401, "Sign in to export.")
    with connect() as conn:
        return load_member(conn, c)
