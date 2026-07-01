#!/usr/bin/env python3
"""AgentMail bridge — let a character email the player (opt-in, env-gated).

A thin wrapper over the AgentMail send API (https://docs.agentmail.to). Sending is
OFF by default: a character never emails anyone unless AGENTMAIL_API_KEY and an
inbox are configured, a recipient is known, AND the user explicitly triggers it
from the UI. Any missing config or transport failure raises EmailUnavailable so
the endpoint degrades to a clear "not sent" — never a 500.

The character persona rides in the subject and the signed body; AgentMail sends
from the configured inbox address (it doesn't spoof arbitrary From names).

Env:
  AGENTMAIL_API_KEY          - AgentMail API key (required to send)
  AGENTMAIL_INBOX_ID         - the inbox id to send FROM (required)
  AGENTMAIL_BASE             - API base (default https://api.agentmail.to/v0)
  UNDERTALE_VERA_USER_EMAIL  - default recipient (the player)
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx

_DEFAULT_BASE = "https://api.agentmail.to/v0"


class EmailUnavailable(RuntimeError):
    """Raised when email isn't configured or the send failed — never a 500."""


def _base() -> str:
    return (os.environ.get("AGENTMAIL_BASE") or _DEFAULT_BASE).rstrip("/")


def default_recipient() -> Optional[str]:
    return os.environ.get("UNDERTALE_VERA_USER_EMAIL") or None


def is_configured() -> bool:
    """True when a send is possible (key + inbox present)."""
    return bool(os.environ.get("AGENTMAIL_API_KEY") and os.environ.get("AGENTMAIL_INBOX_ID"))


def status() -> dict[str, Any]:
    """A UI-facing summary so the client can enable/disable the email action."""
    recipient = default_recipient()
    return {
        "configured": is_configured(),
        "has_recipient": bool(recipient),
        # never leak the full address; a hint is enough for the UI
        "recipient_hint": _hint(recipient),
    }


def _hint(addr: Optional[str]) -> Optional[str]:
    if not addr or "@" not in addr:
        return None
    user, _, domain = addr.partition("@")
    shown = (user[:2] + "…") if len(user) > 2 else user
    return f"{shown}@{domain}"


def send(subject: str, text: str, to: Optional[str] = None, *, timeout: float = 15.0) -> dict[str, Any]:
    """Send one email via AgentMail. Raises EmailUnavailable on any problem."""
    key = os.environ.get("AGENTMAIL_API_KEY")
    inbox = os.environ.get("AGENTMAIL_INBOX_ID")
    recipient = to or default_recipient()
    if not key or not inbox:
        raise EmailUnavailable(
            "AgentMail not configured — set AGENTMAIL_API_KEY and AGENTMAIL_INBOX_ID"
        )
    if not recipient:
        raise EmailUnavailable(
            "no recipient — set UNDERTALE_VERA_USER_EMAIL or pass an address"
        )
    url = f"{_base()}/inboxes/{inbox}/messages/send"
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"to": recipient, "subject": subject, "text": text},
            timeout=timeout,
        )
        resp.raise_for_status()
        body = resp.json() if resp.content else {}
    except EmailUnavailable:
        raise
    except Exception as exc:  # httpx errors, non-2xx, bad JSON
        raise EmailUnavailable(f"AgentMail send failed: {exc}") from exc
    return {"sent": True, "to": recipient, "id": (body or {}).get("id"), "response": body}
