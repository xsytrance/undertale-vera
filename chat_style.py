#!/usr/bin/env python3
"""Chat style options — the player's dials for HOW a character answers.

These are FREE-bucket knobs: verbosity, emotional intensity, lore depth, and how
much a character leans on save/reset meta-awareness. They change HOW a reply reads,
never WHAT the save says — so they live entirely on the free side of the wall, as a
directive block the model is told to honour. Defaults are the no-op normal settings,
so an absent/empty options dict produces NO directives and a byte-identical baseline.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

_VERBOSITY = {
    "brief": "Keep your reply very short — one or two sentences at most.",
    "verbose": "You may answer at length, expansively, if it fits.",
}
_INTENSITY = {
    "subtle": "Keep your manner understated; underplay the emotion.",
    "dramatic": "Lean fully into your current demeanor; let the feeling show.",
}
_META = {
    "off": "Do NOT reference saves, loads, resets, timelines, or that this is a game; "
           "stay fully in the fiction.",
    "on": "You may speak knowingly about the save, resets, and the weight of repeated "
          "choices, where it fits your character.",
}

# lore depth → how many lore docs to retrieve (None = skip the lore layer entirely)
_LORE_K = {"none": None, "light": 2, "normal": 4, "rich": 6}


def lore_k(options: dict[str, Any]) -> int | None:
    """Documents to retrieve for the FREE lore layer; None means skip lore."""
    return _LORE_K.get((options or {}).get("lore", "normal"), 4)


def build_style_directives(options: dict[str, Any]) -> str:
    """A FREE directive block from the player's dials. "" for all-default options."""
    opts = options or {}
    bits = [
        _VERBOSITY.get(opts.get("verbosity")),
        _INTENSITY.get(opts.get("intensity")),
        _META.get(opts.get("meta")),
    ]
    bits = [b for b in bits if b]
    if not bits:
        return ""
    return ("HOW TO ANSWER (free — these shape your delivery only, never the save's "
            "facts):\n- " + "\n- ".join(bits))
