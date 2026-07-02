#!/usr/bin/env python3
"""Report Cards — each character's after-action report on your run.

Where chat is a conversation and the Council is a room of one-liners, a Report is a
character sitting you down and telling you, plainly: how you did, one thing you
might have done differently, and what THEY would have done in your place. It is
FREE voice over SACRED facts — the same two-bucket wall as chat and the journal.

This is the pure part: the request instruction the character is given, a
deterministic fallback when no model is reachable, a small helper to lift the
one-line verdict off the top, and the markdown export (so a report — or the whole
set — can be carried out, or inscribed into the Keepsake Journal).

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any


def report_instruction(save_truth: dict[str, Any]) -> str:
    """The prompt asking a character to file a grounded after-action report."""
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    where = (f"their path reads as {route}" if route != "undetermined"
             else "their path is not yet clear")
    return (
        "File a short REPORT for the human on the journey their save records — an "
        "honest after-action assessment, in your own voice. In three to five "
        "sentences speak to: how they did, one thing they might have done "
        f"differently, and what YOU would have done in their place ({where}). "
        "Begin with a single verdict line of at most six words, prefixed exactly "
        "with 'Verdict:'. Then write the report. Do not invent any save facts "
        "beyond what you've been told."
    )


def fallback_report(character_name: str, save_truth: dict[str, Any]) -> str:
    """A deterministic, honest report when no model is reachable — never invented."""
    play = (save_truth or {}).get("play_state") or {}
    route = ((save_truth or {}).get("route") or {}).get("route") or "undetermined"
    name = play.get("name") or "you"
    if route == "undetermined":
        return (
            "Verdict: too soon to tell.\n\n"
            f"{name}, your save hasn't shown me enough to report on yet. Walk a little "
            "further and ask me again — I'll tell you straight what I see, and what I'd "
            f"have done in your place. — {character_name}"
        )
    return (
        f"Verdict: a {route} run, plainly.\n\n"
        f"{name}, your save reads as a {route} path, and I won't dress it up. I can only "
        "report what's recorded here — ask me in person and I'll say more about what I'd "
        f"have done differently. — {character_name}"
    )


def split_verdict(text: str) -> tuple[str, str]:
    """Lift a leading 'Verdict: …' (or a short first line) off as the headline.

    Returns (verdict, body). If no clear verdict, verdict is "" and body is the text.
    """
    t = (text or "").strip()
    if not t:
        return "", ""
    first, _, rest = t.partition("\n")
    first, rest = first.strip(), rest.strip()
    if first.lower().startswith("verdict:"):
        return first[len("verdict:"):].strip(" -—:"), rest
    # a short standalone first line reads as a headline too
    if rest and len(first) <= 60:
        return first, rest
    return "", t


def build_report_markdown(reports: list[dict[str, Any]], project_name: str = "this save") -> str:
    """Render one or many reports to portable markdown (also used for the journal)."""
    lines = [
        f"# Report Cards — {project_name}",
        "",
        "*The Underground's after-action reports on your run.*",
        "",
    ]
    if not reports:
        lines.append("*(No reports yet.)*")
        return "\n".join(lines)
    for r in reports:
        author = r.get("author", "someone")
        verdict = r.get("verdict")
        head = f"## {author}" + (f" — *{verdict}*" if verdict else "")
        lines += [head, "", (r.get("text") or "").strip(), ""]
    return "\n".join(lines).rstrip() + "\n"
