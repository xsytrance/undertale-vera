#!/usr/bin/env python3
"""Hallucination guard — the wall, checked on the model's ACTUAL reply.

Ported in spirit from fft-psx-vera/hallucination_guard.py. The two-bucket wall is
enforced up-front by the prompt; this is the second line of defense: after the
model speaks, scan the reply for claims that CONTRADICT the SACRED SaveTruth
(route / LOVE / kills) and flag them. It closes the blueprint's loop — verify the
fact survives all the way to live generation, not just prompt assembly.

Design choices:
  - PURE (no DB/network/LLM): `check_response(reply, save_truth)` is unit-testable.
  - CONSERVATIVE: only clear, second-person assertions are flagged, to avoid
    false positives on a character speaking loosely or hypothetically. Better to
    miss a borderline case than to cry wolf on a clean reply.
  - ADVISORY, not destructive: it returns issues for the UI/overlay to surface;
    it does NOT rewrite the model's words. The prompt remains the primary wall.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# Second-person assertions that claim the player walked a particular route.
# Keyed phrase → the route it asserts. Apostrophes are stripped before matching,
# so "you've" becomes "youve".
_ROUTE_ASSERTIONS: dict[str, str] = {
    "you killed everyone": "Genocide",
    "youve killed everyone": "Genocide",
    "you killed them all": "Genocide",
    "you murdered everyone": "Genocide",
    "you slaughtered everyone": "Genocide",
    "you wiped out": "Genocide",
    "nothing left but dust": "Genocide",
    "your genocide": "Genocide",
    "genocide route": "Genocide",
    "you spared everyone": "Pacifist",
    "youve spared everyone": "Pacifist",
    "you spared them all": "Pacifist",
    "you killed no one": "Pacifist",
    "you killed nobody": "Pacifist",
    "you hurt no one": "Pacifist",
    "your pacifist": "Pacifist",
    "pacifist route": "Pacifist",
    "true pacifist": "Pacifist",
}

_LOVE_RE = re.compile(r"\b(?:love|lv|level)\s*(?:of|is|=|:|at)?\s*(\d{1,3})\b")
_LOVE_RE2 = re.compile(r"\b(\d{1,3})\s*(?:love|lv)\b")
_KILLS_RE = re.compile(r"\b(?:killed)\s+(\d{1,4})\b")
_KILLS_RE2 = re.compile(r"\b(\d{1,4})\s*(?:kills?|monsters?)\b")

_KNOWN_ROUTES = ("Pacifist", "Neutral", "Genocide")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().replace("'", ""))


def check_response(reply: str, save_truth: dict[str, Any]) -> dict[str, Any]:
    """Scan `reply` for claims contradicting SaveTruth. Returns
    {clean: bool, issues: [...], checked: [...]}."""
    st = save_truth or {}
    play = st.get("play_state") or {}
    route = (st.get("route") or {}).get("route")
    love = play.get("love")
    kills = (st.get("kills") or {}).get("total")

    norm = _norm(reply)
    issues: list[dict[str, Any]] = []

    # ── route ────────────────────────────────────────────────────────────────
    for phrase, asserted in _ROUTE_ASSERTIONS.items():
        if phrase in norm:
            if route in _KNOWN_ROUTES and asserted != route:
                issues.append(_issue("route", phrase, route,
                    f"reply asserts a {asserted} route, but the save's route is {route}"))
            elif route == "undetermined" or route is None:
                issues.append(_issue("route", phrase, route or "undetermined",
                    f"reply asserts a {asserted} route, but the save's route is undetermined"))

    # ── LOVE ─────────────────────────────────────────────────────────────────
    if isinstance(love, int):
        for m in list(_LOVE_RE.finditer(norm)) + list(_LOVE_RE2.finditer(norm)):
            n = int(m.group(1))
            if n != love:
                issues.append(_issue("love", m.group(0), love,
                    f"reply states LOVE {n}, but the save's LOVE is {love}"))

    # ── kills ────────────────────────────────────────────────────────────────
    if isinstance(kills, int):
        for m in list(_KILLS_RE.finditer(norm)) + list(_KILLS_RE2.finditer(norm)):
            n = int(m.group(1))
            if n != kills:
                issues.append(_issue("kills", m.group(0), kills,
                    f"reply states {n} kills, but the save's kill count is {kills}"))

    return {
        "clean": not issues,
        "issues": issues,
        "checked": ["route", "love", "kills"],
    }


def _issue(kind: str, claim: str, sacred: Any, message: str) -> dict[str, Any]:
    return {"type": kind, "claim": claim, "sacred": sacred, "message": message}
