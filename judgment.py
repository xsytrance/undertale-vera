#!/usr/bin/env python3
"""The Judgment beat — reading the morally-loaded save back to the player.

A Sans-style judgment: the player's route, LOVE, and kills, read straight off the
SaveTruth. This is the most SACRED-leaning surface in the app, so it is held to the
strictest standard:

  - The `facts` are verbatim from SaveTruth — never invented.
  - The `verdict` is a TONE classification *derived from* those facts (route/LOVE).
    It is free flavour in our own accent (we do NOT copy Undertale's text), but it
    never asserts a fact that isn't in `facts`.
  - The unknowns are named explicitly in `honest_gaps` — the judgment refuses to
    pretend it knows more than the save shows. An `undetermined` route yields an
    open verdict, never a guessed one.

PURE module (no DB, no network, no LLM): `build_judgment` returns a deterministic
structured readout. The in-voice spoken delivery is a separate, grounded LLM call
(see the app's judgment/speak endpoint), which reuses this as its sacred core.
"""
from __future__ import annotations

from typing import Any, Optional

from ledger import build_remembrance_grounding

# Verdict tone, keyed by route, written in our own accent (never copied).
_VERDICTS: dict[str, dict[str, str]] = {
    "Pacifist": {
        "label": "clean hands",
        "line": "not a drop of EXP on you. you walked the whole way down and spared "
                "every soul you met. that's rarer than anyone here would guess.",
    },
    "Neutral": {
        "label": "somewhere in between",
        "line": "some you spared. some you didn't. the save keeps the count either "
                "way — i'm just the one reading it back.",
    },
    "Genocide": {
        "label": "the dust on your hands",
        "line": "the numbers don't lie. you cut your way through, all the way to the "
                "top. i've got your real count right here, and it's not pretty.",
    },
    "undetermined": {
        "label": "the verdict's still open",
        "line": "your save hasn't told me enough to judge you yet. and i'm not gonna "
                "pretend it has. come back when there's more to read.",
    },
}


def classify_verdict(route: Optional[str]) -> dict[str, str]:
    """Map a (real) route to a tone verdict. Unknown/None → the open verdict."""
    return _VERDICTS.get(route or "undetermined", _VERDICTS["undetermined"])


def build_judgment(
    save_truth: dict[str, Any],
    snapshots: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Build the deterministic, sacred judgment readout.

    Returns:
      {
        "facts": {name, love, route, route_confidence, total_kills},  # SACRED
        "verdict": {"label", "line"},   # tone derived from route; no new facts
        "honest_gaps": [...],           # what the save couldn't tell us
        "remembrance": str,             # SACRED cross-visit deltas (may be "")
      }
    """
    st = save_truth or {}
    play = st.get("play_state") or {}
    route_block = st.get("route") or {}
    kills = st.get("kills") or {}

    route = route_block.get("route") or "undetermined"
    facts = {
        "name": play.get("name"),
        "love": play.get("love"),
        "route": route,
        "route_confidence": route_block.get("confidence"),
        "total_kills": kills.get("total"),
    }

    honest_gaps: list[str] = []
    if facts["name"] in (None, ""):
        honest_gaps.append("the name on the save could not be read")
    if facts["love"] is None:
        honest_gaps.append("LOVE could not be read")
    if facts["total_kills"] is None:
        honest_gaps.append("the kill count could not be read")
    if route == "undetermined":
        honest_gaps.append("the route is undetermined — no path is being claimed")

    return {
        "facts": facts,
        "verdict": classify_verdict(route),
        "honest_gaps": honest_gaps,
        "remembrance": build_remembrance_grounding(snapshots or []),
    }
