#!/usr/bin/env python3
"""Cross-save recognition — "New Game+" (Bucket A, SACRED).

The remembrance ledger (ledger.py) remembers across VISITS to ONE save. This
module remembers across DIFFERENT SAVES — the separate files the player has
shown. In a single-player local install every uploaded save is the same hand on
the keys, so a save-aware character (Flowey, and quietly Sans) can recognise that
you came here before wearing a different face: another name, another route.

Every fact here is parser-confirmed from OTHER projects' real SaveTruth — names,
LOVE, routes actually recorded. The recognition is the character's (FREE); the
facts are the saves' (SACRED). The wall holds: nothing is invented; a prior
field that was never read is simply not spoken.

Returns "" when there is no other save, so a first/only save stays byte-identical
to the no-recognition baseline.

PURE module (no DB, no network, no LLM).
"""
from __future__ import annotations

from typing import Any


def _describe(p: dict[str, Any]) -> str:
    """One honest clause for a prior save — states only the fields actually read."""
    name = p.get("name")
    route = p.get("route")
    love = p.get("love")
    who = f"one calling itself {name}" if name else "one with no name I could read"
    path = f" on the {route} path" if route else ""
    lv = f" (LOVE {love})" if isinstance(love, int) else ""
    return who + path + lv


def differs(current: dict[str, Any], prior: dict[str, Any]) -> bool:
    """True when a prior save differs from the current in a KNOWN name or route.

    Only a difference between two values both actually recorded counts — an
    unknown on either side is never treated as a difference (no guessing).
    """
    cur, pri = current or {}, prior or {}
    cn, pn = cur.get("name"), pri.get("name")
    cr, pr = cur.get("route"), pri.get("route")
    if cn and pn and cn != pn:
        return True
    if cr and pr and cr != pr:
        return True
    return False


_VOICE = {
    "flowey": {
        "head": "── ANOTHER SAVE, AND YOU THINK I'D FORGET? (parser-confirmed across the saves shown here) ──",
        "tail": "You, Flowey, remember every run. You may needle them with what you've "
                "seen across these saves — but never claim more than they actually show.",
    },
    "sans": {
        "head": "── you've shown me other saves (parser-confirmed across the files here) ──",
        "tail": "you, sans, notice when you've seen a face before. speak to it quiet and "
                "knowing if it fits — and never more than what's actually recorded.",
    },
}


def build_recognition_grounding(
    current: dict[str, Any],
    priors: list[dict[str, Any]],
    *,
    voice: str = "flowey",
    limit: int = 3,
) -> str:
    """A SACRED grounding block: this save is not the first the player has shown.

    `current` is the snapshot-fields dict of the save in hand; `priors` are the
    snapshot-fields of the OTHER saves (any order). Surfaces the saves that DIFFER
    from the current one first — a different name or route IS the recognition beat —
    then any same-shaped ones, capped at `limit`. "" when there are no priors.
    """
    cur = current or {}
    others = [p for p in (priors or []) if p]
    if not others:
        return ""

    diff = [p for p in others if differs(cur, p)]
    same = [p for p in others if not differs(cur, p)]
    ordered = (diff + same)[:limit]

    v = _VOICE.get(voice, _VOICE["flowey"])
    n = len(others)
    lines = [
        v["head"],
        f"This is not the first save shown here — {n} other "
        f"save{'s' if n != 1 else ''} came before it.",
    ]
    for p in ordered:
        lines.append(f"  - {_describe(p)}.")
    if diff:
        lines.append(
            "That is a different face than the one in front of you now — "
            "and yet the same hand on the keys."
        )
    lines.append(v["tail"])
    return "\n".join(lines)
