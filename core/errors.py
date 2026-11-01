"""Error tracking hook. With SENTRY_DSN set, errors go to Sentry; without it they are only logged.

Uses Sentry's plain HTTP envelope endpoint, so no SDK is needed. Sending runs in a background thread and
never raises: a broken error tracker must not break a request.
"""

import json
import logging
import threading
import traceback
import urllib.request
import uuid
from datetime import UTC, datetime
from urllib.parse import urlparse

from core.settings import settings

log = logging.getLogger("x25x125.errors")


def _endpoint(dsn: str) -> tuple[str, str] | None:
    """(envelope URL, public key) from a DSN like https://<key>@o123.ingest.sentry.io/456."""
    u = urlparse(dsn)
    if not u.username or not u.hostname or not u.path.strip("/"):
        return None
    project = u.path.strip("/").split("/")[-1]
    port = f":{u.port}" if u.port else ""
    return f"{u.scheme}://{u.hostname}{port}/api/{project}/envelope/", u.username


def envelope(exc: BaseException, context: dict | None = None, now: datetime | None = None) -> bytes:
    """One Sentry error event as an envelope body."""
    event_id = uuid.uuid4().hex
    frames = [
        {"filename": f.filename, "function": f.name, "lineno": f.lineno}
        for f in traceback.extract_tb(exc.__traceback__)
    ]
    event = {
        "event_id": event_id,
        "timestamp": (now or datetime.now(UTC)).isoformat(),
        "platform": "python",
        "level": "error",
        "environment": settings.app_env,
        "server_name": "engine",
        "exception": {
            "values": [{"type": type(exc).__name__, "value": str(exc), "stacktrace": {"frames": frames}}]
        },
        "extra": context or {},
    }
    head = json.dumps({"event_id": event_id})
    item = json.dumps(event)
    return f'{head}\n{{"type":"event","length":{len(item.encode())}}}\n{item}\n'.encode()


def _send(url: str, key: str, body: bytes) -> None:
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-sentry-envelope")
    req.add_header("X-Sentry-Auth", f"Sentry sentry_version=7, sentry_key={key}, sentry_client=x25x125/0.1")
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as e:  # noqa: BLE001 - reporting must never fail the caller
        log.warning("could not send the error to Sentry: %s", e)


def report(exc: BaseException, context: dict | None = None, wait: bool = False) -> bool:
    """Log the error and, when SENTRY_DSN is set, send it. Returns True when a send was started.
    `wait` blocks up to 5 seconds for the send (for jobs that exit right after)."""
    log.error("%s: %s", type(exc).__name__, exc, exc_info=exc)
    target = _endpoint(settings.sentry_dsn) if settings.sentry_dsn else None
    if target is None:
        return False
    t = threading.Thread(target=_send, args=(*target, envelope(exc, context)), daemon=True)
    t.start()
    if wait:
        t.join(timeout=5)
    return True
