#!/usr/bin/env python3
"""Relational awareness — characters react to what became of those they care about.

The disposition mining told us who was killed / spared / befriended. This makes it
PERSONAL: Sans cares about Papyrus, so on a run where Papyrus was killed, Sans is
given that hard fact, framed for him. Undyne cares about Alphys; Toriel about Asgore;
and so on (the `cares_about` web in character_config).

Everything here is SACRED — it surfaces only a real recorded disposition of someone
this speaker cares about, never an invented one. The character's REACTION is their
voice (FREE); the FACT is sacred and goes on the facts side of the wall.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

from character_disposition import _STATUS_PHRASE  # the definite-outcome set
from character_config import get_character

# How a loved one's recorded fate is stated to the speaker.
_FATE_LINE = {
    "killed": "was killed in this run",
    "spared": "was spared",
    "befriended": "was befriended",
}


def relevant_fates(character_name: str, save_truth: dict[str, Any]) -> list[dict[str, str]]:
    """The recorded fates of the people THIS character cares about (definite only)."""
    char = get_character(character_name) or {}
    cares = char.get("cares_about") or []
    dispositions = (save_truth or {}).get("dispositions") or {}
    out: list[dict[str, str]] = []
    for name in cares:
        status = (dispositions.get(name) or {}).get("status")
        if status in _STATUS_PHRASE:
            out.append({"who": name, "status": status})
    return out


def build_relational_grounding(character_name: str, save_truth: dict[str, Any]) -> str:
    """SACRED block: how the speaker's loved ones fared. "" when none is recorded."""
    fates = relevant_fates(character_name, save_truth)
    if not fates:
        return ""
    char = get_character(character_name) or {}
    speaker = char.get("name", character_name)
    lines = [
        f"── WHAT BECAME OF THOSE {speaker.upper()} CARES ABOUT (parser-confirmed; "
        "never invent beyond this) ──",
    ]
    for f in fates:
        lines.append(f"  - {f['who']}, who matters to {speaker}, {_FATE_LINE[f['status']]}.")
    lines.append(
        f"This is a hard fact from the save. Let it move {speaker} as it would — but "
        "never claim more than is recorded here."
    )
    return "\n".join(lines)
