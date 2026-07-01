#!/usr/bin/env python3
"""Deltarune SaveTruth — the Chapter 1 save, normalized into the app's truth shape.

Produces a dict compatible with the Undertale SaveTruth consumed by the prompt wall,
the shelf, snapshots, and every feature module — so a Deltarune save flows through
the same machinery — plus a `deltarune` block for chapter-specific facts.

Honesty rules carried over verbatim:
  - unknowns are None, never guessed.
  - Chapter 1's route (Pacifist vs Violent) is NOT derivable from publicly
    corroborated flags yet, so route = "undetermined" with confidence "unknown".
    (Deltarune has no Genocide; the Weird route begins in Chapter 2.)
  - LV in Deltarune is famously always 1; we still only report what the save shows
    (v1 names no LV line, so love/lv stay None rather than asserting lore).

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1


def build_deltarune_truth(parsed: dict[str, Any], source_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize a parse_deltarune_save() result into a SaveTruth-compatible dict."""
    f = parsed.get("fields") or {}
    conf = parsed.get("confidence") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "game": "deltarune",
        "chapter": parsed.get("chapter"),
        "source": {
            "digest": parsed.get("digest"),
            "slot": parsed.get("slot"),
            "line_count": parsed.get("line_count"),
            **(source_meta or {}),
        },
        "play_state": {
            "name": f.get("name"),
            "love": None,       # Deltarune has no LOVE; never asserted from lore
            "lv": None,
            "max_hp": None,
            "room": None,
            "room_name": None,
            "play_time_frames": None,
            "gold": f.get("dark_dollars"),   # the shelf's "money" concept
            "fun": None,
            "toriel_pie": None,
        },
        "kills": {"total": None, "by_area": None},
        "route": {
            "route": "undetermined",
            "confidence": "unknown",
            "reasons": [
                "Chapter 1 route (Pacifist vs Violent) is not derivable from "
                "publicly corroborated save flags yet — reported honestly as "
                "undetermined rather than guessed."
            ],
        },
        "deltarune": {
            "dark_dollars": f.get("dark_dollars"),
            "party": None,      # not yet corroborated; promoted with evidence only
        },
        "confidence": {
            "name": conf.get("name", "unknown"),
            "dark_dollars": conf.get("dark_dollars", "unknown"),
            "route": "unknown",
        },
        "warnings": list(parsed.get("warnings") or []),
    }
