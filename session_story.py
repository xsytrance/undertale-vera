#!/usr/bin/env python3
"""Session Stories — a character narrates the arc of a play session.

Guided Mode records every save as a snapshot; a session story stitches the range
into a short second-person tale told in a character's voice. The beats are SACRED
(they come from ledger.summarize_change between consecutive snapshots); the telling
is FREE. With no model, a deterministic stitched recap keeps it honest.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

import ledger


def session_beats(snapshots: list[dict[str, Any]], since_visit: int = 1) -> list[dict[str, Any]]:
    """The arc: per-visit deltas across the snapshot range (SACRED, from the ledger)."""
    snaps = [s for s in (snapshots or []) if (s.get("counter") or 0) >= max(1, since_visit - 1)]
    snaps.sort(key=lambda s: s.get("counter") or 0)
    out: list[dict[str, Any]] = []
    for prev, curr in zip(snaps, snaps[1:]):
        out.append({
            "visit": curr.get("counter"),
            "changes": ledger.summarize_change(prev, curr) or ["a quiet save — nothing measured moved"],
        })
    return out


def story_block(snapshots: list[dict[str, Any]], since_visit: int = 1) -> str:
    """The SACRED block describing the session for the prompt."""
    snaps = sorted((snapshots or []), key=lambda s: s.get("counter") or 0)
    if not snaps:
        return ""
    beats = session_beats(snapshots, since_visit)
    first, last = snaps[0], snaps[-1]

    def state(s: dict[str, Any]) -> str:
        bits = [s.get("name") or "an unnamed run"]
        if s.get("route"):
            bits.append(f"route {s['route']}")
        if isinstance(s.get("love"), int):
            bits.append(f"LOVE {s['love']}")
        if isinstance(s.get("total_kills"), int):
            bits.append(f"{s['total_kills']} kills")
        return ", ".join(bits)

    lines = [
        "═══ THE SESSION THE SAVE RECORDS (HARD FACTS — NEVER OVERRIDE OR INVENT) ═══",
        f"  It began: {state(first)}.",
    ]
    for b in beats:
        for c in b["changes"]:
            lines.append(f"  save #{b['visit']}: {c}")
    lines.append(f"  It stands now: {state(last)}.")
    lines.append("═══ END ═══")
    return "\n".join(lines)


def instruction(beat_count: int) -> str:
    return (
        "The human just finished a play session with you riding along. The block above "
        "records exactly what happened between their saves"
        + (f" ({beat_count} beats)" if beat_count else "")
        + ". Tell the session back to them as a short story — four to seven sentences, "
        "second person, in your own voice, with a beginning and an end. Use only what "
        "the block records; invent nothing beyond it."
    )


def fallback(character_name: str, snapshots: list[dict[str, Any]], since_visit: int = 1) -> str:
    """A deterministic stitched recap when no model is reachable."""
    beats = session_beats(snapshots, since_visit)
    if not beats:
        return (f"— {character_name}: one save, no measured change yet. "
                "the story starts the next time you save.")
    lines = "; ".join(c for b in beats[:6] for c in b["changes"][:1])
    return (f"— {character_name}: the session as the save wrote it — {lines}. "
            f"{len(beats)} beat{'s' if len(beats) != 1 else ''}, all of them yours.")
