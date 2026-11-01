"""Who is calling: signed requests from the web app, the organization scope for row-level security,
plans and their features, rate limits and the audit log.

The web app signs a short claim on every engine call: {"uid", "org", "ip", "exp"}, HMAC-SHA256 with
ENGINE_SHARED_SECRET, in the X-25x125-Claim header. Routes that touch organization data need a valid claim
with a user and an organization; the engine then checks the membership in the database, switches to the
restricted x25_app role and sets app.org_id, so Postgres row-level security limits every query to that
organization. A claim that is present but does not verify is rejected on every route.
"""

import base64
import hashlib
import hmac
import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Annotated

import psycopg
from fastapi import Depends, HTTPException, Request

from core.db import connect
from core.settings import settings
from engine.comps import RULES_DIR

log = logging.getLogger("x25x125.auth")

CLAIM_HEADER = "x-25x125-claim"
DEV_SECRET = "dev-only-shared-secret-not-for-production"
MAX_AGE_S = 300  # a claim older than this, or dated further ahead, is refused
APP_ROLE = "x25_app"


def is_production() -> bool:
    return settings.app_env.lower() == "production"


def shared_secret() -> str:
    if settings.engine_shared_secret:
        return settings.engine_shared_secret
    if is_production():
        raise HTTPException(500, "ENGINE_SHARED_SECRET is not set on the engine")
    return DEV_SECRET


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _mac(body: str, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())


def sign_claim(claim: dict, secret: str | None = None) -> str:
    """The header value for a claim (used by tests and scripts; the web app does the same in lib/claim.ts)."""
    body = _b64(json.dumps(claim, separators=(",", ":")).encode())
    return f"{body}.{_mac(body, secret or shared_secret())}"


def make_claim(uid: str | None = None, org: str | None = None, ip: str = "127.0.0.1", ttl: int = 60) -> str:
    return sign_claim({"uid": uid, "org": org, "ip": ip, "exp": int(time.time()) + ttl})


def read_claim(value: str, now: float | None = None) -> dict | None:
    """The claim when the signature and the time check out; None otherwise."""
    if "." not in value:
        return None
    body, sig = value.rsplit(".", 1)
    if not hmac.compare_digest(_mac(body, shared_secret()), sig):
        return None
    try:
        claim = json.loads(_unb64(body))
    except ValueError:
        return None
    now = time.time() if now is None else now
    exp = claim.get("exp") if isinstance(claim, dict) else None
    if not isinstance(exp, int | float) or exp < now or exp > now + MAX_AGE_S:
        return None
    return claim


@cache
def plans() -> dict:
    return json.loads((RULES_DIR / "plans.json").read_text())


def effective_plan(
    plan: str, status: str, trial_ends_at: datetime | None, now: datetime | None = None
) -> str:
    """The plan whose features apply now. A trial counts until it ends; past_due keeps Pro while Stripe retries."""
    now = now or datetime.now(UTC)
    if status in ("active", "past_due", "comp"):
        return plan
    if status == "trialing" and trial_ends_at is not None and trial_ends_at > now:
        return "pro"
    return "free"


def features(plan: str) -> frozenset[str]:
    return frozenset(plans()["plans"].get(plan, plans()["plans"]["free"])["features"])


@dataclass(frozen=True)
class Caller:
    signed: bool
    ip: str
    user_id: str | None = None
    org_id: str | None = None
    role: str | None = None
    email: str | None = None
    plan: str = "free"
    features: frozenset[str] = field(default_factory=frozenset)

    @property
    def key(self) -> str:
        """Who a rate limit counts against."""
        return f"user:{self.user_id}" if self.user_id else f"ip:{self.ip}"


def caller(request: Request) -> Caller:
    """The caller as the signed claim describes it; anonymous and unsigned when there is no claim."""
    host = request.client.host if request.client else "unknown"
    raw = request.headers.get(CLAIM_HEADER)
    if not raw:
        return Caller(signed=False, ip=host)
    claim = read_claim(raw)
    if claim is None:
        raise HTTPException(401, "The request signature did not verify or has expired.")
    return Caller(
        signed=True, ip=str(claim.get("ip") or host), user_id=claim.get("uid"), org_id=claim.get("org")
    )


def signed(c: Annotated[Caller, Depends(caller)]) -> Caller:
    """Any signed call from the web app (signed in or not)."""
    if not c.signed:
        raise HTTPException(401, "This route takes signed requests from the 25x125 web app only.")
    return c


def load_member(conn: psycopg.Connection, c: Caller) -> Caller:
    row = conn.execute(
        """select m.role, u.email, o.plan, o.plan_status, o.trial_ends_at
           from membership m join org o on o.id = m.org_id join account_user u on u.id = m.user_id
           where m.org_id = %s and m.user_id = %s""",
        (c.org_id, c.user_id),
    ).fetchone()
    if row is None:
        raise HTTPException(403, "You are not a member of this organization.")
    plan = effective_plan(row[2], row[3], row[4])
    return Caller(True, c.ip, c.user_id, c.org_id, row[0], row[1], plan, features(plan))


def member(c: Annotated[Caller, Depends(caller)]) -> Caller:
    """A signed-in member of the organization named in the signed claim."""
    if not c.signed or not c.user_id or not c.org_id:
        raise HTTPException(401, "Sign in first.")
    with connect() as conn:
        return load_member(conn, c)


def owner(c: Annotated[Caller, Depends(member)]) -> Caller:
    if c.role != "owner":
        raise HTTPException(403, "Only the organization's owner can do this.")
    return c


def admin_emails() -> frozenset[str]:
    """Product admins: the emails in ADMIN_EMAILS (comma-separated)."""
    return frozenset(e.strip().lower() for e in settings.admin_emails.split(",") if e.strip())


def user_email(conn: psycopg.Connection, user_id: str | None) -> str | None:
    if not user_id:
        return None
    row = conn.execute("select email from account_user where id = %s", (user_id,)).fetchone()
    return row[0] if row else None


def admin(c: Annotated[Caller, Depends(caller)]) -> Caller:
    """A signed-in user whose email is in ADMIN_EMAILS. The user comes from the signed claim; the email from
    the database."""
    if not c.signed or not c.user_id:
        raise HTTPException(401, "Sign in first.")
    with connect() as conn:
        email = user_email(conn, c.user_id)
    if email is None or email not in admin_emails():
        raise HTTPException(403, "Only product admins can see this.")
    return Caller(True, c.ip, c.user_id, c.org_id, None, email)


def needs(feature: str):
    """Dependency: a member whose plan includes `feature` (data/rules/plans.json)."""

    def dep(c: Annotated[Caller, Depends(member)]) -> Caller:
        if feature not in c.features:
            label = plans()["feature_labels"].get(feature, feature)
            raise HTTPException(
                402,
                f"{label} are part of Pro. Your saved data is kept; start or renew Pro on the account page.",
            )
        return c

    return dep


@contextmanager
def scoped(conn: psycopg.Connection, c: Caller) -> Iterator[psycopg.Connection]:
    """One transaction as the restricted role with app.org_id set, so row-level security limits every query
    to the caller's organization. Commits on success, rolls back on error, closes the connection."""
    if not c.org_id:
        raise HTTPException(401, "Sign in first.")
    with conn:
        conn.execute(f"set local role {APP_ROLE}")
        conn.execute(
            "select set_config('app.org_id', %s, true), set_config('app.user_id', %s, true)",
            (c.org_id, c.user_id or ""),
        )
        yield conn


def audit(conn: psycopg.Connection, c: Caller, action: str, target: str | None = None, /, **detail) -> None:
    """Record who did what in which organization. Runs inside the caller's scoped transaction."""
    conn.execute(
        "insert into audit_log (org_id, user_id, action, target, detail, ip) values (%s, %s, %s, %s, %s, %s)",
        (c.org_id, c.user_id, action, target, json.dumps(detail, default=str), c.ip),
    )


@cache
def _limits() -> dict:
    return json.loads((RULES_DIR / "rate_limits.json").read_text())["buckets"]


def take(conn: psycopg.Connection, bucket: str, who: str) -> float | None:
    """Take one token from a bucket. Returns None when allowed, else the seconds until a token is back."""
    lim = _limits()[bucket]
    burst, per_s = float(lim["burst"]), float(lim["per_hour"]) / 3600
    row = conn.execute(
        """insert into rate_bucket as b (key, tokens, updated_at) values (%(k)s, %(burst)s - 1, now())
           on conflict (key) do update set
             tokens = least(%(burst)s, b.tokens + extract(epoch from now() - b.updated_at) * %(rate)s) - 1,
             updated_at = now()
           returning tokens""",
        {"k": f"{bucket}:{who}", "burst": burst, "rate": per_s},
    ).fetchone()
    tokens = row[0]
    if tokens >= 0:
        return None
    # Over the limit: put the token back so waiting refills the bucket, and say how long to wait.
    conn.execute("update rate_bucket set tokens = tokens + 1 where key = %s", (f"{bucket}:{who}",))
    return max(1.0, (-tokens) / per_s)


def check_rate(bucket: str, who: str) -> None:
    with connect() as conn:
        wait = take(conn, bucket, who)
    if wait is not None:
        raise HTTPException(
            429,
            f"Too many requests. Try again in {int(wait) + 1} seconds.",
            headers={"Retry-After": str(int(wait) + 1)},
        )


def rate_limited(bucket: str):
    """Dependency: one token from `bucket` for this caller (user when signed in, else IP address)."""

    def dep(c: Annotated[Caller, Depends(caller)]) -> Caller:
        check_rate(bucket, c.key)
        return c

    return dep


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
