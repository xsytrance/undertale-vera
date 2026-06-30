#!/usr/bin/env python3
"""The Constellation of You — the whole shape of a player across ALL their saves.

New Game+ recognition (crossave.py) is PAIRWISE: this save versus another. The
Constellation is the AGGREGATE: every save the player has ever shown, read as one
identity. How many runs, which routes, the moral RANGE from the kindest face to
the cruelest — and, when the spread is total (a full Pacifist AND a full Genocide
both shown), the hardest truth the save history can hold: the same hands did both.

The tallies are SACRED (counted from real recorded routes/LOVE/kills across the
saves). The verdict is FREE (Sans's read on the shape). The wall holds: nothing is
invented, and a run whose route was never read simply isn't counted into a route.

PURE module (no DB, no network, no LLM).
"""
from __future__ import annotations

from typing import Any

from crossave import route_severity


def aggregate(saves: list[dict[str, Any]]) -> dict[str, Any]:
    """Tally the whole save history (each entry = snapshot-fields of one save).

    Returns counts, the route tally, the darkest and kindest runs (by route
    severity, then LOVE, then kills), the peak LOVE seen, and `full_spectrum` —
    true only when BOTH a Pacifist and a Genocide save have been shown.
    """
    saves = [s for s in (saves or []) if s]
    routes: dict[str, int] = {}
    for s in saves:
        r = s.get("route")
        if r:
            routes[r] = routes.get(r, 0) + 1

    rated = [s for s in saves if route_severity(s.get("route")) > 0]
    darkest = max(
        rated,
        key=lambda s: (route_severity(s.get("route")), s.get("love") or 0, s.get("total_kills") or 0),
        default=None,
    )
    kindest = min(
        rated,
        key=lambda s: (route_severity(s.get("route")), s.get("love") or 0, s.get("total_kills") or 0),
        default=None,
    )
    loves = [s.get("love") for s in saves if isinstance(s.get("love"), int)]
    return {
        "count": len(saves),
        "routes": routes,
        "darkest": darkest,
        "kindest": kindest,
        "peak_love": max(loves) if loves else None,
        "full_spectrum": routes.get("Pacifist", 0) > 0 and routes.get("Genocide", 0) > 0,
    }


def _routes_phrase(routes: dict[str, int]) -> str:
    """'two Pacifist, one Genocide' — honest tally, kindest route first."""
    order = ["Pacifist", "Neutral", "Genocide"]
    parts = []
    for r in order:
        n = routes.get(r, 0)
        if n:
            parts.append(f"{n} {r}")
    # any non-standard/extra routes, appended as-is
    for r, n in routes.items():
        if r not in order and n:
            parts.append(f"{n} {r}")
    if not parts:
        return "no run I could read"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def build_verdict(agg: dict[str, Any], *, voice: str = "sans") -> str:
    """A FREE verdict line over the SACRED aggregate. "" with no saves.

    The strongest beat is `full_spectrum`: the same player has shown both the
    kindest and the cruelest run a soul can walk. Sans names that directly.
    """
    agg = agg or {}
    n = agg.get("count", 0)
    if not n:
        return ""

    routes = agg.get("routes") or {}
    phrase = _routes_phrase(routes)
    head = f"Across every save you've shown here ({n}): {phrase}."

    if agg.get("full_spectrum"):
        tail = (
            "you've shown me the kindest run a soul can walk, and the cruelest — "
            "and the same hands did both. i don't know which one's really you. "
            "maybe neither. maybe that's the point."
        )
    elif (agg.get("darkest") or {}).get("route") == "Genocide":
        tail = "every kind of run you've shown carries blood, or the memory of it. that follows a person."
    elif routes and all(r == "Pacifist" for r in routes):
        tail = "every save you've shown walked it kind. that... actually means something. don't lose it."
    else:
        tail = "that's the shape of you, so far. the save remembers all of it — and so do i."

    return f"{head} {tail}"
