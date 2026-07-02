#!/usr/bin/env python3
"""Proactive contact — the characters reach out to YOU, unprompted.

A mode where the Underground doesn't wait to be spoken to. Given a save, this picks
the character with the most at stake (by their derived affinity — grief and hostility
speak loudest, then fondness) and frames an unprompted message in their voice,
grounded in the save's truth. The message is FREE voice over SACRED facts, same wall
as chat.

PURE module (no DB/network/LLM): picks the reacher and writes the instruction +
deterministic fallback.
"""
from __future__ import annotations

from typing import Any, Optional

import affinity as affinity_mod

# Which stance is most likely to break the silence and reach for you.
_STANCE_URGENCY = {"grieving": 5, "hostile": 4, "warm": 3, "wary": 2, "unreadable": 1}


def pick_reacher(save_truth: dict[str, Any], exclude: Optional[list[str]] = None) -> Optional[dict[str, Any]]:
    """Choose who reaches out: the character with the most emotional stake. None if empty."""
    exclude = set(exclude or [])
    best = None
    best_score = -1
    for name, aff in affinity_mod.all_affinities(save_truth).items():
        if name in exclude:
            continue
        score = _STANCE_URGENCY.get(aff["stance"], 0)
        if score > best_score:
            best_score, best = score, {"character": name, "stance": aff["stance"], "basis": aff["basis"]}
    return best


def reach_out_instruction(save_truth: dict[str, Any]) -> str:
    """The prompt asking a character to send an UNPROMPTED message (grounded)."""
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    return (
        "You are reaching out to the human first — they did NOT message you. Send them a "
        "short, unprompted message (one or two sentences) in your own voice, as if breaking "
        "the silence. Speak to what their save actually shows"
        + (f" (their path reads as {route})" if route != "undetermined"
           else " (their path is not yet clear)")
        + ". Do not invent any save facts beyond what you've been told."
    )


def fallback_reach_out(character_name: str, save_truth: dict[str, Any]) -> str:
    """A deterministic unprompted line when no model is reachable — honest, grounded."""
    play = (save_truth or {}).get("play_state") or {}
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    name = play.get("name") or "you"
    if route == "undetermined":
        return f"hey, {name}. it's {character_name}. your save hasn't shown me which way you'll go yet. i just wanted to *reach out*."
    return f"hey, {name}. it's {character_name}. your save reads as a {route} path — i *couldn't not* say something."
