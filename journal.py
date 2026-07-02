#!/usr/bin/env python3
"""The Keepsake Journal — a book the characters fill, that you carry between worlds.

A character writes a short entry IN their own voice, grounded in the save's truth at
the moment. The entry is FREE expression (their words) anchored to SACRED facts (the
real route/LOVE/kills via the grounded system prompt) — the same two-bucket wall as
chat. This module is the pure part: the writing INSTRUCTION the character is given, a
deterministic fallback when no model is reachable, and the markdown export so the
journal can be carried out of the Underground.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any


def inscription_instruction(save_truth: dict[str, Any]) -> str:
    """The user-side prompt asking the character to inscribe an entry (grounded)."""
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    return (
        "Write a short journal entry — two or three sentences — directly to the human "
        "whose journey you've witnessed, in your own voice. Speak to what their save "
        "actually shows"
        + (f" (their path reads as {route})" if route != "undetermined"
           else " (their path is not yet clear)")
        + ". Address them as someone leaving a keepsake they'll carry with them. Do not "
        "invent any save facts beyond what you've been told."
    )


def fallback_inscription(character_name: str, save_truth: dict[str, Any]) -> str:
    """A deterministic, honest entry when no model is reachable — never invented."""
    play = (save_truth or {}).get("play_state") or {}
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    name = play.get("name") or "traveler"
    if route == "undetermined":
        return (f"To {name}: I cannot yet say which way you walk. I'll keep this page open "
                "until your save tells me more. — leave room here.")
    return (f"To {name}: your save reads as a {route} path, and I've set that down here as "
            "it stands. Carry this with you. — written plainly, nothing added.")


def build_journal_markdown(entries: list[dict[str, Any]], project_name: str = "this save") -> str:
    """Render the journal to portable markdown — the keepsake you take with you."""
    lines = [
        f"# The Keepsake Journal — {project_name}",
        "",
        "*A book the Underground filled. Carry it with you.*",
        "",
    ]
    if not entries:
        lines.append("*(No one has written here yet.)*")
        return "\n".join(lines)
    for e in entries:
        author = e.get("author", "someone")
        ctx = e.get("route_context")
        head = f"### {author}" + (f"  ·  *{ctx}*" if ctx else "")
        lines += [head, "", e.get("text", ""), ""]
    return "\n".join(lines)
