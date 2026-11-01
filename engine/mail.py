"""Outgoing email: sign-in links and invites.

With EMAIL_SERVER set (smtp://user:password@host:587 for STARTTLS, smtps://...:465 for TLS), mail goes out
through that server; any SMTP provider works (Resend, Postmark, Amazon SES, a Google Workspace relay).
Without it the engine is in dev mode: the message is printed to the engine console and written to
.dev-mail/<address>.txt in the repo root, and nothing is sent.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import unquote, urlparse

from core.settings import settings

log = logging.getLogger("x25x125.mail")
DEV_MAIL = Path(__file__).resolve().parent.parent / ".dev-mail"


def dev_mode() -> bool:
    return not settings.email_server


def _dev_file(to: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "@._-" else "_" for ch in to)
    return DEV_MAIL / f"{safe}.txt"


def send(to: str, subject: str, text: str) -> bool:
    """Send one plain-text email. Returns True when it went to an SMTP server, False in dev mode."""
    if dev_mode():
        DEV_MAIL.mkdir(exist_ok=True)
        _dev_file(to).write_text(f"To: {to}\nSubject: {subject}\n\n{text}\n", encoding="utf-8")
        print(
            f"\n[dev mode: EMAIL_SERVER is not set, nothing was sent]\nTo: {to}\nSubject: {subject}\n{text}\n"
        )
        return False
    u = urlparse(settings.email_server)
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    port = u.port or (465 if u.scheme == "smtps" else 587)
    ctx = ssl.create_default_context()
    if u.scheme == "smtps":
        server = smtplib.SMTP_SSL(u.hostname, port, context=ctx, timeout=20)
    else:
        server = smtplib.SMTP(u.hostname, port, timeout=20)
        server.starttls(context=ctx)
    with server:
        if u.username:
            server.login(unquote(u.username), unquote(u.password or ""))
        server.send_message(msg, from_addr=parseaddr(settings.email_from)[1])
    return True


def sign_in_text(link: str, minutes: int) -> str:
    return (
        f"Use this link to sign in to 25x125. It works once and expires in {minutes} minutes.\n\n{link}\n\n"
        "If you did not ask to sign in, ignore this email. No account changes until the link is used."
    )


def invite_text(org_name: str, inviter: str, link: str) -> str:
    return (
        f"{inviter} added you to {org_name} on 25x125, the Chicago parcel feasibility tool.\n\n"
        f"Sign in with this email address to join: {link}\n\nThe invite expires in 14 days."
    )
