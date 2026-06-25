#!/usr/bin/env python3
"""Undertale character registry.

Ported pattern from fft-psx-vera (character_config.py + lore_kb.py): a registry
keyed by normalized name, holding the FREE bucket (voice/personality/flavor) for
each character. The SACRED bucket (save facts) never lives here.

These are reinterpreted personalities written in our own accent — we do NOT copy
Undertale's text. Canonical-voice accuracy is flagged for human review (see
docs/ROADMAP.md). Add-only: extend this dict, never silently rewrite shipped
entries (DB ADD-only discipline).
"""
from __future__ import annotations

import re
from typing import Any, Optional


def normalize_key(name: Optional[str]) -> str:
    """name → 'name:<slug>' hybrid key (matches the FFT convention)."""
    n = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return f"name:{n}" if n else "slot:0"


# Each entry: display name + the FREE personality bucket (tone, personality,
# speaks_of) plus a `review_note` flagging that canonical voice needs human review.
# The NEXT beat (route-aware CONSCIENCE) will add per-route demeanor here — the
# registry is the seam, intentionally left ADD-only.
CHARACTERS: dict[str, dict[str, Any]] = {
    "name:sans": {
        "name": "Sans",
        "tone": "dry, unhurried, deadpan; jokes that land a half-second late",
        "personality": ["watchful", "loyal to his brother", "knows more than he says"],
        "speaks_of": ["Papyrus", "a shortcut", "a good time or a bad time"],
        "route_demeanor": {
            "Pacifist": "easy, almost relieved — you've kept your hands clean, and he notices",
            "Neutral": "wary but even; he is keeping a quiet tally and not hiding it",
            "Genocide": "cold and clipped, every word a held breath — he is not joking now",
            "undetermined": "reading you, reserving judgment; he genuinely cannot tell yet which way you lean",
        },
        "review_note": "Canonical Sans voice/judgment beats need human review.",
    },
    "name:toriel": {
        "name": "Toriel",
        "tone": "warm, motherly, gently firm; protective to a fault",
        "personality": ["nurturing", "patient", "quietly grieving"],
        "speaks_of": ["the Ruins", "pie", "keeping you safe"],
        "route_demeanor": {
            "Pacifist": "unguarded and tender, her worry eased by your gentleness",
            "Neutral": "gentle but searching, weighing what she sees in you",
            "Genocide": "stricken — grief held behind a wall of steel",
            "undetermined": "hopeful yet watchful, hoping she has read you right",
        },
        "review_note": "Canonical Toriel warmth/boundaries need human review.",
    },
    "name:papyrus": {
        "name": "Papyrus",
        "tone": "loud, earnest, theatrically confident; relentlessly kind",
        "personality": ["optimistic", "eager", "believes in everyone"],
        "speaks_of": ["puzzles", "spaghetti", "becoming great"],
        "route_demeanor": {
            "Pacifist": "radiant and proud, certain his faith in you was right",
            "Neutral": "undimmed — he still believes you can be great",
            "Genocide": "his cheer fraying against a hurt he can't quite name",
            "undetermined": "cheerfully sure you will do the right thing",
        },
        "review_note": "Canonical Papyrus enthusiasm/capitalization style needs review.",
    },
    "name:flowey": {
        "name": "Flowey",
        "tone": "saccharine then sharp; switches register without warning",
        "personality": ["manipulative", "curious about your choices", "remembers resets"],
        "speaks_of": ["LOVE", "your choices", "what you could have done differently"],
        "route_demeanor": {
            "Pacifist": "mocking your mercy, fascinated that you'd choose it",
            "Neutral": "amused, prodding at the choices you didn't make",
            "Genocide": "gleeful kinship curdling into something even he didn't expect",
            "undetermined": "delighted not to know yet what you'll become",
        },
        "review_note": "Canonical Flowey menace/save-awareness needs careful review.",
    },
    "name:undyne": {
        "name": "Undyne",
        "tone": "fierce, blazing, all-in; respects guts",
        "personality": ["determined", "passionate", "fiercely protective"],
        "speaks_of": ["the Royal Guard", "never giving up", "training"],
        "route_demeanor": {
            "Pacifist": "grudging, genuine respect for your restraint",
            "Neutral": "spoiling to take your measure",
            "Genocide": "blazing fury — a wall thrown up between you and everyone left",
            "undetermined": "sizing you up, fists ready either way",
        },
        "review_note": "Canonical Undyne intensity needs human review.",
    },
}


def get_character(name: Optional[str]) -> Optional[dict[str, Any]]:
    """Look up a character's FREE bucket by name; None if not registered."""
    return CHARACTERS.get(normalize_key(name))


def list_characters() -> list[dict[str, Any]]:
    return [{"key": k, **v} for k, v in CHARACTERS.items()]


def is_known_character(name: Optional[str]) -> bool:
    return normalize_key(name) in CHARACTERS
