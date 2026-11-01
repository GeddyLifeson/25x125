"""Plans and Stripe billing: Checkout, the customer portal and the webhook that sets an organization's plan.

Talks to Stripe's REST API directly (no SDK). Needs STRIPE_SECRET_KEY (test mode key while building),
STRIPE_WEBHOOK_SECRET and the price ids STRIPE_PRICE_PRO_MONTHLY and STRIPE_PRICE_FOUNDING_MONTHLY.
Without the key, Checkout and the portal answer 503 with a plain note; the 14-day trial still works.
Stripe Tax is on for every Checkout session (data/rules/plans.json, stripe_tax).
"""

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from core.db import connect
from core.settings import settings
from engine.auth import Caller, owner, plans

router = APIRouter()
STRIPE_API = "https://api.stripe.com/v1"
SIGNATURE_TOLERANCE_S = 300


class StripeError(Exception):
    pass


def stripe_call(method: str, path: str, params: dict | None = None) -> dict:
    """One Stripe API call with form-encoded params (keys already in Stripe's a[b][c] form)."""
    if not settings.stripe_secret_key:
        raise HTTPException(503, "Billing is not set up yet: STRIPE_SECRET_KEY is empty on the engine.")
    data = urllib.parse.urlencode(params or {}).encode() if method != "GET" else None
    url = f"{STRIPE_API}{path}" + (f"?{urllib.parse.urlencode(params)}" if method == "GET" and params else "")
    req = urllib.request.Request(url, data=data, method=method)
    token = base64.b64encode(f"{settings.stripe_secret_key}:".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read())["error"]["message"]
        except (ValueError, KeyError):
            msg = str(e)
        raise StripeError(msg) from e


def verify_signature(payload: bytes, header: str, secret: str, now: float | None = None) -> bool:
    """Stripe-Signature check: t=<unix time>,v1=<hex HMAC-SHA256 of "t.payload">, within 5 minutes."""
    parts: dict[str, list[str]] = {}
    for item in (header or "").split(","):
        k, _, v = item.strip().partition("=")
        parts.setdefault(k, []).append(v)
    try:
        t = int(parts["t"][0])
    except (KeyError, ValueError):
        return False
    now = time.time() if now is None else now
    if abs(now - t) > SIGNATURE_TOLERANCE_S:
        return False
    want = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(want, v) for v in parts.get("v1", []))


def signature_header(payload: bytes, secret: str, t: int | None = None) -> str:
    """Build a Stripe-Signature header (for tests and for replaying a saved event locally)."""
    t = int(time.time()) if t is None else t
    v1 = hmac.new(secret.encode(), f"{t}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={t},v1={v1}"


def _ts(v) -> datetime | None:
    return datetime.fromtimestamp(int(v), UTC) if v else None


def _plan_for_price(price_id: str | None) -> str:
    """Every paid price is Pro for now; the founding price is Pro at $79."""
    return "pro" if price_id else "free"


def handle_event(conn, event: dict) -> str | None:
    """Apply one Stripe event to the organization it names. Returns the org id changed, or None."""
    if (
        conn.execute(
            "insert into stripe_event (id, type) values (%s, %s) on conflict (id) do nothing returning id",
            (event["id"], event["type"]),
        ).fetchone()
        is None
    ):
        return None  # already handled
    obj = event["data"]["object"]
    at = _ts(event.get("created")) or datetime.now(UTC)
    org_id = None
    if event["type"] == "checkout.session.completed":
        org_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("org_id")
        if org_id:
            conn.execute(
                """update org set stripe_customer_id = coalesce(%s, stripe_customer_id),
                          stripe_subscription_id = coalesce(%s, stripe_subscription_id) where id = %s""",
                (obj.get("customer"), obj.get("subscription"), org_id),
            )
    elif event["type"].startswith("customer.subscription."):
        org_id = (obj.get("metadata") or {}).get("org_id")
        if not org_id and obj.get("customer"):
            row = conn.execute(
                "select id from org where stripe_customer_id = %s", (obj["customer"],)
            ).fetchone()
            org_id = row[0] if row else None
        if org_id:
            status = (
                "canceled" if event["type"] == "customer.subscription.deleted" else obj.get("status", "none")
            )
            item = ((obj.get("items") or {}).get("data") or [{}])[0]
            price_id = (item.get("price") or {}).get("id")
            period_end = obj.get("current_period_end") or item.get("current_period_end")
            conn.execute(
                """update org set plan = %s, plan_status = %s, trial_ends_at = coalesce(%s, trial_ends_at),
                          current_period_end = %s, stripe_customer_id = coalesce(%s, stripe_customer_id),
                          stripe_subscription_id = %s, stripe_price_id = %s, plan_updated_at = %s
                   where id = %s and (plan_updated_at is null or plan_updated_at <= %s)""",
                (_plan_for_price(price_id) if status != "canceled" else "free", status, _ts(obj.get("trial_end")),
                 _ts(period_end), obj.get("customer"), obj.get("id"), price_id, at, org_id, at),
            )  # fmt: skip
    conn.execute("update stripe_event set org_id = %s where id = %s", (org_id, event["id"]))
    return org_id


def cancel_subscription(subscription_id: str | None) -> bool:
    """Cancel at once (used when an owner deletes the account). False when billing is not set up."""
    if not subscription_id or not settings.stripe_secret_key:
        return False
    try:
        stripe_call("DELETE", f"/subscriptions/{subscription_id}")
    except StripeError:
        return False
    return True


def _base(body: dict) -> str:
    base = str(body.get("base_url") or "").rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise HTTPException(400, "base_url must be the web app's address")
    return base


@router.get("/billing/plans")
def billing_plans() -> dict:
    """Plans, prices and features (data/rules/plans.json), and whether billing is set up on this engine."""
    return {
        **plans(),
        "billing_ready": bool(settings.stripe_secret_key and settings.stripe_price_pro_monthly),
    }


@router.post("/billing/checkout")
def checkout(body: Annotated[dict, Body()], c: Annotated[Caller, Depends(owner)]) -> dict:
    """A Stripe Checkout session for Pro (founding price when the org has it), with Stripe Tax on.
    Time left on the trial carries into the subscription, so the first charge comes when the trial ends."""
    base = _base(body)
    price = settings.stripe_price_pro_monthly
    with connect() as conn:
        org = conn.execute(
            "select name, stripe_customer_id, founding, trial_ends_at from org where id = %s", (c.org_id,)
        ).fetchone()
    if org[2] and settings.stripe_price_founding_monthly:
        price = settings.stripe_price_founding_monthly
    if not price:
        raise HTTPException(
            503, "Billing is not set up yet: STRIPE_PRICE_PRO_MONTHLY is empty on the engine."
        )
    try:
        customer = org[1]
        if not customer:
            customer = stripe_call(
                "POST", "/customers", {"email": c.email, "name": org[0], "metadata[org_id]": c.org_id}
            )["id"]
            with connect() as conn:
                conn.execute("update org set stripe_customer_id = %s where id = %s", (customer, c.org_id))
        params = {
            "mode": "subscription",
            "customer": customer,
            "client_reference_id": c.org_id,
            "line_items[0][price]": price,
            "line_items[0][quantity]": 1,
            "success_url": f"{base}/account?billing=done",
            "cancel_url": f"{base}/account?billing=canceled",
            "automatic_tax[enabled]": "true" if plans().get("stripe_tax") else "false",
            "customer_update[address]": "auto",
            "customer_update[name]": "auto",
            "billing_address_collection": "required",
            "tax_id_collection[enabled]": "true",
            "allow_promotion_codes": "true",
            "metadata[org_id]": c.org_id,
            "subscription_data[metadata][org_id]": c.org_id,
        }
        # Stripe needs a trial end at least 48 hours ahead.
        if org[3] and org[3] > datetime.now(UTC) + timedelta(hours=49):
            params["subscription_data[trial_end]"] = int(org[3].timestamp())
        session = stripe_call("POST", "/checkout/sessions", params)
    except StripeError as e:
        raise HTTPException(502, f"Stripe: {e}") from e
    return {"url": session["url"]}


@router.post("/billing/portal")
def portal(body: Annotated[dict, Body()], c: Annotated[Caller, Depends(owner)]) -> dict:
    """A Stripe customer portal session: card, invoices, cancel."""
    base = _base(body)
    with connect() as conn:
        customer = conn.execute("select stripe_customer_id from org where id = %s", (c.org_id,)).fetchone()[0]
    if not customer:
        raise HTTPException(409, "This organization has no billing account yet. Start Pro first.")
    try:
        session = stripe_call(
            "POST", "/billing_portal/sessions", {"customer": customer, "return_url": f"{base}/account"}
        )
    except StripeError as e:
        raise HTTPException(502, f"Stripe: {e}") from e
    return {"url": session["url"]}


@router.post("/billing/webhook")
async def webhook(request: Request) -> dict:
    """Stripe calls this (through the web app's /api/billing/webhook) on subscription changes."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(503, "STRIPE_WEBHOOK_SECRET is empty on the engine.")
    payload = await request.body()
    if not verify_signature(
        payload, request.headers.get("stripe-signature", ""), settings.stripe_webhook_secret
    ):
        raise HTTPException(400, "Stripe signature did not verify")
    try:
        event = json.loads(payload)
    except ValueError as e:
        raise HTTPException(400, "body is not JSON") from e
    with connect() as conn:
        org_id = handle_event(conn, event)
    return {"received": True, "org_id": org_id}
