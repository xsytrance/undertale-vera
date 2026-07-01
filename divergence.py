#!/usr/bin/env python3
"""Two-Save Divergence — a character speaks to the fork between any two save files.

Where the Constellation auto-compares the gentlest and cruelest runs across every
save, this lets the player pick ANY two files and hear a chosen character reflect on
the space between them: the same hands, two different paths. FREE voice over SACRED
facts — both files' routes/LOVE/kills/name are handed to the model verbatim and it
must not invent beyond them. A deterministic fallback keeps it working with no model.

PURE module (no DB/network/LLM). Inputs are `snapshot_fields_from_truth` dicts.
"""
from __future__ import annotations

from typing import Any


def _facts(s: dict[str, Any]) -> str:
    parts = []
    r = s.get("route")
    parts.append(f"route {r}" if r else "route not yet readable")
    if isinstance(s.get("love"), int):
        parts.append(f"LOVE {s['love']}")
    if isinstance(s.get("total_kills"), int):
        parts.append(f"{s['total_kills']} kills")
    nm = s.get("name")
    who = nm if nm else "a name I couldn't read"
    return f"{who} — " + ", ".join(parts)


def two_file_block(a: dict[str, Any], b: dict[str, Any]) -> str:
    """The SACRED block naming both files' facts (never to be overridden or invented)."""
    return (
        "═══ TWO SAVE FILES BY THE SAME HANDS (HARD FACTS — NEVER OVERRIDE OR INVENT) ═══\n"
        f"  FILE ONE: {_facts(a)}\n"
        f"  FILE TWO: {_facts(b)}\n"
        "═══ END ═══\n"
        "These are two different files the same human made. The truth of each is above; "
        "speak only to what is written there."
    )


def instruction() -> str:
    """The prompt asking the character to reflect on the fork (grounded, in voice)."""
    return (
        "Two of this human's save files are described above — the same hands having "
        "walked two different paths. In a few sentences, in your own voice, speak to "
        "the fork between them: what the space between those two saves says. Do not "
        "invent anything that isn't in the two files."
    )


def fallback(character_name: str, a: dict[str, Any], b: dict[str, Any]) -> str:
    """A deterministic, honest reflection when no model is reachable — never invented."""
    ra, rb = a.get("route"), b.get("route")

    def tag(s: dict[str, Any]) -> str:
        nm = s.get("name") or "a nameless face"
        love = f", LOVE {s['love']}" if isinstance(s.get("love"), int) else ""
        return f"{nm}{love}"

    if ra and rb and ra != rb:
        dk = b.get("total_kills")
        blood = f", {dk} of them dead" if isinstance(dk, int) and dk > 0 else ""
        return (
            f"— {character_name}. on one file you walked it {ra} ({tag(a)}); on another, "
            f"{rb} ({tag(b)}{blood}). same hands, two different paths. that space between "
            "them is the whole question, isn't it."
        )
    if ra and rb and ra == rb:
        return (
            f"— {character_name}: both files read as {ra} ({tag(a)} · {tag(b)}). the same "
            "road, walked twice. not much of a fork — you know who you are."
        )
    return (
        f"— {character_name}: one of these two files hasn't shown me enough to compare yet. "
        "read them a little further and ask me again."
    )
