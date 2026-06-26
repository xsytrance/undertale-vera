#!/usr/bin/env python3
"""The remembrance ledger — "the save remembers" (Bucket A, SACRED).

Ported pattern from fft-psx-vera/ledger.py + the SaveSnapshot "They Remember"
table: an ADDITIVE, parser-truth record of the player's state across visits. Each
upload/refresh appends one immutable snapshot; nothing is ever overwritten or
wiped (DB ADD-only). Load order = chronology.

This module is PURE (no DB, no network): it extracts snapshot fields from a
SaveTruth, derives the honest deltas between two snapshots, and renders the
SACRED-side "what the save remembers" grounding block.

THE WALL holds here too: every delta is derived ONLY from real recorded values.
If a value is unknown in either snapshot, the delta is simply not claimed — never
guessed. A character noticing "you have more LOVE than before" is a SACRED fact
(two real numbers subtracted), not free flavour, so it lives on the facts side of
the prompt.
"""
from __future__ import annotations

from typing import Any, Optional


def snapshot_fields_from_truth(save_truth: dict[str, Any]) -> dict[str, Any]:
    """Extract the immutable snapshot fields from a SaveTruth dict."""
    st = save_truth or {}
    play = st.get("play_state") or {}
    route = st.get("route") or {}
    kills = st.get("kills") or {}
    return {
        "name": play.get("name"),
        "love": play.get("love"),
        "route": route.get("route"),
        "route_confidence": route.get("confidence"),
        "total_kills": kills.get("total"),
    }


def summarize_change(prev: dict[str, Any], curr: dict[str, Any]) -> list[str]:
    """Honest, plain-language deltas between two snapshots.

    Only claims a change when BOTH values are known and actually differ. Returns
    [] when nothing measurable changed (or values are unknown) — never guessed.
    """
    prev = prev or {}
    curr = curr or {}
    changes: list[str] = []

    pv_love, cv_love = prev.get("love"), curr.get("love")
    if isinstance(pv_love, int) and isinstance(cv_love, int) and cv_love != pv_love:
        if cv_love > pv_love:
            changes.append(f"LOVE has risen from {pv_love} to {cv_love}")
        else:
            changes.append(f"LOVE now reads {cv_love}, down from {pv_love}")

    pv_route, cv_route = prev.get("route"), curr.get("route")
    if pv_route and cv_route and pv_route != cv_route:
        changes.append(f"the path turned from {pv_route} to {cv_route}")

    pv_k, cv_k = prev.get("total_kills"), curr.get("total_kills")
    if isinstance(pv_k, int) and isinstance(cv_k, int) and cv_k != pv_k:
        changes.append(f"recorded kills went from {pv_k} to {cv_k}")

    pv_name, cv_name = prev.get("name"), curr.get("name")
    if pv_name and cv_name and pv_name != cv_name:
        changes.append(f"the name on the save changed from {pv_name} to {cv_name}")

    return changes


def build_remembrance_grounding(snapshots: list[dict[str, Any]]) -> str:
    """Render the SACRED 'what the save remembers' block from the ledger.

    `snapshots` is chronological (oldest first). Returns "" when there are fewer
    than two snapshots — there is nothing yet to remember, so the grounding stays
    byte-identical to the single-visit baseline.
    """
    snaps = list(snapshots or [])
    if len(snaps) < 2:
        return ""

    prev, curr = snaps[-2], snaps[-1]
    deltas = summarize_change(prev, curr)

    lines = [
        "── WHAT THE SAVE REMEMBERS (across your visits — parser-confirmed, "
        "additive; never invented) ──",
        f"This is visit #{len(snaps)}.",
    ]
    if deltas:
        lines.append("Since the last time the save was read:")
        for d in deltas:
            lines.append(f"  - {d}")
    else:
        lines.append("Nothing measurable has changed since the last reading.")
    lines.append(
        "Speak to these remembered changes only if they fit; they are hard facts "
        "from the save's history — do not exaggerate or invent more than is listed."
    )
    return "\n".join(lines)
