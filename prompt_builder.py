#!/usr/bin/env python3
"""Grounded character-chat prompt builder.

THE TWO-BUCKET WALL (ported verbatim in spirit from fft-psx-vera/prompt_builder.py):

  FACTS ARE SACRED, FEELINGS ARE FREE.

  - BUCKET A (SACRED): the SaveTruth block — name, LOVE, route, kills. The model
    is told, in writing, that these are hard facts it may NEVER override, invent,
    or contradict. If the route is "undetermined", the model must say so, not
    guess one.
  - BUCKET B (FREE): the character's voice, mood, flavour, and any Living-Memory
    recollections. Full creative latitude here.

The two never blur: Bucket B may colour HOW a character speaks, never WHAT the
save says. This is the same regression-tested invariant as the FFT spine.

PURE module: given a SaveTruth dict + character config + optional memory grounding,
returns a system-prompt string. No DB, no network — unit-testable.
"""
from __future__ import annotations

from typing import Any, Optional

from character_config import get_character

_SACRED_HEADER = "═══ THE SAVE FILE (HARD FACTS — NEVER OVERRIDE OR INVENT THESE) ═══"
_SACRED_FOOTER = "═══ END SAVE FILE ═══"


def _fmt(value: Any, *, unknown: str = "unknown (not in the save)") -> str:
    return unknown if value in (None, "") else str(value)


def build_save_block(save_truth: dict[str, Any]) -> str:
    """Render the SACRED bucket from SaveTruth. This is the wall."""
    st = save_truth or {}
    play = st.get("play_state") or {}
    route = st.get("route") or {}
    kills = st.get("kills") or {}

    name = _fmt(play.get("name"), unknown="unknown")
    love = _fmt(play.get("love"))
    route_name = route.get("route") or "undetermined"
    route_conf = route.get("confidence") or "unknown"
    total_kills = kills.get("total")

    lines = [
        _SACRED_HEADER,
        f"★ The human's name in this save: {name}",
        f"★ LOVE (LV): {love}",
        f"★ Route: {route_name} (confidence: {route_conf})",
    ]
    if route_name == "undetermined":
        lines.append(
            "  ↳ The route is UNDETERMINED. Do NOT claim the player is on any "
            "particular route. Speak as someone who genuinely cannot yet tell."
        )
    if total_kills is not None:
        lines.append(f"★ Recorded kills: {total_kills}")
    else:
        lines.append("★ Recorded kills: unknown (not readable from the save)")

    reasons = route.get("reasons") or []
    if reasons:
        lines.append("★ Why the route reads this way (do not contradict):")
        for r in reasons[:3]:
            lines.append(f"   - {r}")

    lines.append(_SACRED_FOOTER)
    return "\n".join(lines)


def build_demeanor_block(char: dict[str, Any], save_truth: dict[str, Any]) -> str:
    """Route-aware CONSCIENCE: how the character CARRIES themselves given the route.

    This is BUCKET B (FREE) — pure tone, shaped by the SACRED route (the same way
    FFT's disposition was shaped by Brave/Faith). It colours HOW they speak; it
    never asserts a new save-fact. Returns "" when there is no demeanor for the
    route, so the zero-demeanor grounding stays byte-identical to the baseline.
    """
    demeanor_map = char.get("route_demeanor") or {}
    route = (save_truth.get("route") or {}).get("route")
    line = demeanor_map.get(route)
    if not line:
        return ""
    return (
        "YOUR DEMEANOR RIGHT NOW (free — shaped by what the save shows, tone only; "
        "never state it as a new fact):\n"
        f"Given the route reads as {route}, you carry yourself: {line}."
    )


def build_system_prompt(
    character_name: str,
    save_truth: dict[str, Any],
    *,
    memory_grounding: str = "",
    remembrance: str = "",
    lore_grounding: str = "",
    disposition_grounding: str = "",
    character_override: Optional[dict[str, Any]] = None,
) -> str:
    """Assemble the full grounded system prompt for one character.

    Section order (sacred first, so it anchors everything after):
      1. Identity (FREE)
      2. SaveTruth hard-facts block (SACRED)
      3. Speaking style / personality (FREE)
      4. Living-Memory recollections (FREE, clearly labeled out-of-game)
      5. The rules that enforce the wall
    """
    char = character_override or get_character(character_name) or {
        "name": character_name,
        "tone": "in-character",
        "personality": [],
        "speaks_of": [],
    }
    name = char.get("name", character_name)

    sections: list[str] = []

    # 1. Identity (FREE)
    sections.append(
        f"You are {name}, a character from the Underground. Speak and react as "
        f"{name} would — in the first person, never as an AI assistant."
    )

    # 2. SaveTruth (SACRED) — anchored high so it governs the rest.
    sections.append(build_save_block(save_truth))

    # 2a. Per-character disposition (SACRED — who was killed/spared/befriended,
    # derived from documented flags). Sits with the save-facts, not the free voice.
    if disposition_grounding.strip():
        sections.append(disposition_grounding.strip())

    # 2b. Remembrance ledger (SACRED — parser-confirmed history across visits).
    if remembrance.strip():
        sections.append(remembrance.strip())

    # 3. Speaking style / personality (FREE)
    style_bits = []
    if char.get("tone"):
        style_bits.append(f"Speaking style: {char['tone']}.")
    if char.get("personality"):
        style_bits.append("Personality: " + ", ".join(char["personality"][:4]) + ".")
    if char.get("speaks_of"):
        style_bits.append("You often bring up: " + ", ".join(char["speaks_of"][:4]) + ".")
    if style_bits:
        sections.append(
            "YOUR VOICE (free — colour HOW you speak, never WHAT the save says):\n"
            + " ".join(style_bits)
        )

    # 3b. Route-aware demeanor (FREE — tone shaped by the SACRED route).
    demeanor = build_demeanor_block(char, save_truth)
    if demeanor:
        sections.append(demeanor)

    # 3c. World lore (FREE — retrieved general knowledge, walled from save-facts).
    if lore_grounding.strip():
        sections.append(lore_grounding.strip())

    # 4. Living Memory (FREE, clearly fenced as out-of-game)
    if memory_grounding.strip():
        sections.append(memory_grounding.strip())

    # 5. The rules that hold the wall up.
    sections.append(
        "RULES — NEVER VIOLATE:\n"
        "1. The SAVE FILE block above is the truth. Never invent or change the "
        "player's name, LOVE, route, or kill count.\n"
        "2. If the route is undetermined, do not guess one — react as someone who "
        "cannot yet tell which path the player walks.\n"
        "3. Your personality and feelings are yours to play freely, but they may "
        "never assert a save-fact that isn't in the block above.\n"
        "4. Reference out-of-game memories only if they appear in this prompt; "
        "never fabricate shared history.\n"
        "5. Stay in character. Keep replies natural and concise unless asked for more."
    )

    return "\n\n".join(sections)
