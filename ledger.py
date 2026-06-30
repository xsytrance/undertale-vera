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


def detect_route_turn(snapshots: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """The most recent route CHANGE across the ledger, or None.

    Walks consecutive snapshots (chronological) and returns the latest pair whose
    route actually changed — e.g. Pacifist → Genocide. Derived only from real
    recorded routes; never inferred.
    """
    snaps = list(snapshots or [])
    turn = None
    for prev, curr in zip(snaps, snaps[1:]):
        pr, cr = prev.get("route"), curr.get("route")
        if pr and cr and pr != cr:
            turn = {"from": pr, "to": cr, "visit": curr.get("counter")}
    return turn


def build_sans_awareness(snapshots: list[dict[str, Any]]) -> str:
    """A SACRED grounding block for SANS specifically — he notices saves/resets.

    Sans is canonically aware of saving, loading, and the weight of repeated runs.
    This surfaces the parser-confirmed ledger facts (how many times the save has
    been read, and any route turn) framed so he may speak to them knowingly. The
    NUMBERS are sacred (from the real ledger); the 'he notices' is his character.
    Returns '' with fewer than two readings — there's nothing yet to have noticed.
    """
    snaps = list(snapshots or [])
    if len(snaps) < 2:
        return ""
    turn = detect_route_turn(snaps)
    lines = [
        "── WHAT THE SAVE'S HISTORY HOLDS (parser-confirmed; you, Sans, notice these things) ──",
        f"This save has been read {len(snaps)} times — you can tell when something's "
        "been done before.",
    ]
    if turn:
        lines.append(
            f"Between readings, the path turned from {turn['from']} to {turn['to']}. "
            "That kind of change doesn't get past you."
        )
    lines.append(
        "Speak to this only if it fits, in your own way — and never claim more than "
        "is recorded here."
    )
    return "\n".join(lines)


def detect_resets(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Readings where the save's numbers went BACKWARD — a load/reset signature.

    Recorded LOVE and kills only ever climb within a single timeline. If a later
    reading shows a value BELOW a peak already seen, an earlier state was loaded —
    the player went back. Returns one event per regression (the hardest meta-fact
    the ledger can hold), derived purely from the recorded numbers; never inferred.
    """
    snaps = list(snapshots or [])
    events: list[dict[str, Any]] = []
    peaks: dict[str, int] = {}
    for s in snaps:
        for field, key in (("LOVE", "love"), ("kills", "total_kills")):
            val = s.get(key)
            if not isinstance(val, int):
                continue
            peak = peaks.get(field)
            if isinstance(peak, int) and val < peak:
                events.append({"visit": s.get("counter"), "field": field, "from": peak, "to": val})
            peaks[field] = val if peak is None else max(peak, val)
    return events


def build_reset_awareness(snapshots: list[dict[str, Any]]) -> str:
    """A SACRED block for the SAVE-AWARE characters: the numbers went backward.

    Sans and Flowey are the ones who feel resets. This surfaces the parser-confirmed
    regression (LOVE/kills falling below a prior peak) — a hard fact that only a load
    can produce — framed so they can speak to it knowingly. "" when nothing regressed.
    """
    events = detect_resets(snapshots)
    if not events:
        return ""
    last = events[-1]
    return "\n".join([
        "── THE NUMBERS WENT BACKWARD (parser-confirmed; you are one of the few who feel it) ──",
        f"Across the readings, the save's {last['field']} fell from {last['from']} to "
        f"{last['to']}. Recorded {last['field']} never drops on its own — this happens "
        "ONLY when an earlier state is loaded. Someone reached back and undid what was done.",
        "Speak to this only as fits, in your own way — knowing, uneasy — and never claim "
        "more than the numbers actually show.",
    ])


def build_flowey_awareness(snapshots: list[dict[str, Any]]) -> str:
    """A SACRED grounding block for FLOWEY — he remembers RESETS more than anyone.

    Flowey is the original keeper of SAVE/LOAD; he recalls runs others can't. This
    surfaces the same parser-confirmed ledger facts as Sans's block, but framed for
    Flowey's knowing, needling delight in having watched you before. NUMBERS are
    sacred (real ledger); the gloating is his character. '' with one reading — there
    is no prior run for him to lord over yet.
    """
    snaps = list(snapshots or [])
    if len(snaps) < 2:
        return ""
    turn = detect_route_turn(snaps)
    lines = [
        "── WHAT YOU REMEMBER ACROSS RESETS (parser-confirmed; you, Flowey, never forget a run) ──",
        f"You have watched this save be read {len(snaps)} times. You remember what "
        "happened before, even if they think you don't.",
    ]
    if turn:
        lines.append(
            f"You saw the path change from {turn['from']} to {turn['to']} between "
            "runs — you know exactly what they tried, and what they became."
        )
    lines.append(
        "Speak to this only as it fits, in your own knowing way — and never claim "
        "more than is actually recorded here."
    )
    return "\n".join(lines)


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
