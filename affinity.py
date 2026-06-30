#!/usr/bin/env python3
"""Affinity — how each character REGARDS you, derived from the save.

A single, honest stance per character: warm / wary / grieving / hostile / unreadable.
It is *derived* from SACRED facts — the route, whether this character or someone they
care about was killed — and is a TONE classification, never a new fact (the same
discipline as the Judgment verdict). It lets the roster answer, at a glance, "how does
the Underground feel about what you've done?"

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

import relationships
from character_config import get_character, list_characters

# stance → a short, in-accent gloss (FREE flavour over a SACRED-derived stance).
_STANCE_GLOSS = {
    "warm": "at ease with you",
    "wary": "taking your measure",
    "grieving": "carrying a loss you dealt",
    "hostile": "turned against you",
    "unreadable": "unable to read you yet",
}


def character_affinity(character_name: str, save_truth: dict[str, Any]) -> dict[str, str]:
    """Derive {stance, basis} for one character from the save. Never asserts a fact."""
    st = save_truth or {}
    route = (st.get("route") or {}).get("route") or "undetermined"
    fates = relationships.relevant_fates(character_name, st)
    loved_killed = [f["who"] for f in fates if f["status"] == "killed"]

    char = get_character(character_name) or {}
    dispositions = st.get("dispositions") or {}
    self_killed = (dispositions.get(char.get("name")) or {}).get("status") == "killed"

    if route == "undetermined":
        stance, basis = "unreadable", "the route is undetermined — no judgment is claimed"
    elif self_killed:
        stance = "hostile" if route == "Genocide" else "grieving"
        basis = "they were killed in this run"
    elif loved_killed:
        stance = "hostile" if route == "Genocide" else "grieving"
        basis = f"{', '.join(loved_killed)} — whom they care about — was killed"
    elif route == "Genocide":
        stance, basis = "hostile", "the route reads as Genocide"
    elif route == "Pacifist":
        stance, basis = "warm", "no harm is recorded on this route"
    else:  # Neutral
        stance, basis = "wary", "a mixed record — some spared, some not"

    return {"stance": stance, "gloss": _STANCE_GLOSS[stance], "basis": basis}


def all_affinities(save_truth: dict[str, Any]) -> dict[str, dict[str, str]]:
    """{character name → affinity} for the whole cast, given a save."""
    return {c["name"]: character_affinity(c["name"], save_truth) for c in list_characters()}
