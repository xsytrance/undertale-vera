#!/usr/bin/env python3
"""The Council — the whole Underground reacts to your run, at once.

Where chat is one voice and affinity is one stance, the Council is the room: every
character's stance and in-voice reaction side by side, so the CONTRAST tells the
story (Sans grieving while Flowey gloats on a Genocide run — that's the argument).

Deterministic and instant: each line is the character's route-shaped demeanor (their
FREE voice) plus, when relevant, the SACRED recorded fate of someone they care about.
It invents nothing — the demeanor is authored per route, the fates are real flags.
A model is never required.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

import affinity as affinity_mod
import relationships
from character_config import list_characters

_FATE_CLAUSE = {
    "killed": "{who} is gone, and that is not forgotten.",
    "spared": "{who} still draws breath, and that counts for something.",
    "befriended": "{who} calls you a friend now.",
}


def _line(name: str, save_truth: dict[str, Any], route: str) -> str:
    """A character's one-line reaction: their route demeanor + a relational clause."""
    char = next((c for c in list_characters() if c["name"] == name), {})
    demeanor = (char.get("route_demeanor") or {}).get(route) \
        or (char.get("route_demeanor") or {}).get("undetermined") or ""
    line = (demeanor[:1].upper() + demeanor[1:]).rstrip(".") + "." if demeanor else ""
    # add the most-pointed relational fact this speaker carries (a loved one's fate)
    fates = relationships.relevant_fates(name, save_truth)
    pointed = next((f for f in fates if f["status"] == "killed"), fates[0] if fates else None)
    if pointed:
        line = (line + " " + _FATE_CLAUSE[pointed["status"]].format(who=pointed["who"])).strip()
    return line


def build_council(save_truth: dict[str, Any]) -> list[dict[str, Any]]:
    """Every character's stance + in-voice reaction to the run (deterministic)."""
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    council: list[dict[str, Any]] = []
    for c in list_characters():
        name = c["name"]
        aff = affinity_mod.character_affinity(name, save_truth)
        council.append({
            "character": name,
            "stance": aff["stance"],
            "gloss": aff["gloss"],
            "line": _line(name, save_truth, route),
        })
    return council
