#!/usr/bin/env python3
"""Route detection — the moral spine of undertale-vera.

NORTH STAR: Undertale's save is morally-loaded state. The route a player is on
(Pacifist / Neutral / Genocide) is the single most consequential fact downstream,
because characters' grounding hinges on it. So this module is held to the strictest
parser-truth standard:

  - The route is DERIVED from real, observed save signals (LOVE, EXP, kill counts,
    documented flags) — never assumed.
  - When the available signals are absent or contradictory, the route is
    "undetermined". We NEVER guess a route to fill a blank. A wrong route breaks
    immersion (and trust) faster than an honest "I can't tell yet".

This is a PURE function module (no DB, no network) so the logic is unit-testable
and the Inspector can replay it deterministically.

A note on honesty / scope (documented in docs/SAVE_FORMAT.md): fully *canonical*
route certainty — especially confirming a completed Genocide run — depends on
area-clear flags whose exact undertale.ini indices vary across game versions. This
detector uses a conservative, documented subset (LOVE, total kills, and named ini
keys when present) and is explicit about its confidence. It will say "Neutral"
or "undetermined" rather than over-claim "Genocide".
"""
from __future__ import annotations

from typing import Any, Optional

ROUTES = ("Pacifist", "Neutral", "Genocide", "undetermined")

# LOVE thresholds. LV 1 means zero EXP gained (no kills). LV 20 is only reachable
# by killing essentially everything — the Genocide ceiling.
LOVE_NO_KILLS = 1
LOVE_GENOCIDE_CEILING = 20


def _maybe_int(v: Any) -> Optional[int]:
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError, AttributeError):
        return None


def extract_kill_signals(parsed) -> dict[str, Any]:
    """Pull kill-related signals out of a ParsedUndertaleSave, honestly.

    Returns total kills (or None) plus the raw ini keys we consulted, so the
    grounding can show its work. Never fabricates a count.
    """
    total = None
    consulted: list[str] = []
    # The [General] Kills counter resets per-room in canon, but its presence and
    # a non-zero value is still a real, observed signal. We read it if present.
    for section, key in (("general", "kills"), ("general", "kill"), ("flags", "kills")):
        raw = parsed.ini_get(section, key) if hasattr(parsed, "ini_get") else None
        if raw is not None:
            consulted.append(f"[{section}] {key}={raw}")
            v = _maybe_int(raw)
            if v is not None:
                total = v if total is None else total + v
    return {"total_kills": total, "consulted": consulted}


def detect_route(parsed) -> dict[str, Any]:
    """Derive the route block for SaveTruth from a ParsedUndertaleSave.

    Output shape:
      {
        "route": one of ROUTES,
        "confidence": confidence string,
        "love": int|None,        # the real LOVE that drove the call
        "total_kills": int|None,
        "signals": [...],        # the real fields/flags we used
        "reasons": [...],        # plain-language justification (auditable)
      }
    """
    love = getattr(parsed, "love", None)
    kills = extract_kill_signals(parsed)
    total_kills = kills["total_kills"]
    signals: list[str] = []
    reasons: list[str] = []

    if love is not None:
        signals.append(f"LOVE={love}")
    signals.extend(kills["consulted"])

    # No usable signal at all → undetermined. This is the honest default.
    if love is None and total_kills is None:
        return {
            "route": "undetermined",
            "confidence": "unknown",
            "love": None,
            "total_kills": None,
            "signals": signals,
            "reasons": [
                "No LOVE value and no kill counter could be read from the save; "
                "the route cannot be derived and is left undetermined."
            ],
        }

    # LV 20 is the Genocide ceiling — only reachable by near-total killing.
    if love == LOVE_GENOCIDE_CEILING:
        reasons.append(
            "LOVE is at the maximum of 20, which is only reachable by killing "
            "nearly every monster — consistent with a Genocide route."
        )
        return _result("Genocide", "high", love, total_kills, signals, reasons)

    # LV 1 with no kills observed → a confirmed no-kill run. This is necessary
    # (but not by itself sufficient) for True Pacifist, so we cap confidence at
    # medium and say so, rather than over-claiming the befriend/date flags.
    if love == LOVE_NO_KILLS and (total_kills in (0, None)):
        reasons.append(
            "LOVE is 1 (no EXP ever gained) and no kills are recorded — a no-kill "
            "run, consistent with a Pacifist route."
        )
        reasons.append(
            "Note: confirming TRUE Pacifist additionally requires befriend/date "
            "flags not read here, so confidence is held at medium."
        )
        return _result("Pacifist", "medium", love, total_kills, signals, reasons)

    # Any LOVE above 1 (and below the ceiling), or recorded kills, means the run
    # has spilled blood but is not a confirmed full Genocide — that is Neutral.
    if (love is not None and love > LOVE_NO_KILLS) or (total_kills not in (0, None)):
        reasons.append(
            "Some killing has occurred (LOVE above 1 and/or recorded kills) but "
            "not the total clearance that defines Genocide — consistent with a "
            "Neutral route."
        )
        if love is not None and love >= 15:
            reasons.append(
                "LOVE is unusually high; this leans toward Genocide but is not "
                "confirmed without area-clear flags — kept as Neutral, not guessed up."
            )
        return _result("Neutral", "medium", love, total_kills, signals, reasons)

    # Signals exist but don't fit a clear pattern → be honest.
    return {
        "route": "undetermined",
        "confidence": "low",
        "love": love,
        "total_kills": total_kills,
        "signals": signals,
        "reasons": [
            "Observed signals do not match a clear route pattern; left undetermined "
            "rather than guessed."
        ],
    }


def _result(route, confidence, love, total_kills, signals, reasons) -> dict[str, Any]:
    return {
        "route": route,
        "confidence": confidence,
        "love": love,
        "total_kills": total_kills,
        "signals": signals,
        "reasons": reasons,
    }
