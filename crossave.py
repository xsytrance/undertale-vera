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


# ── The Other's Echo ─────────────────────────────────────────────────────────
# Recognition with TEETH: a darker run remembered behind a gentler save in hand.
# When a prior save walked Genocide (or Neutral with blood) and the save in front
# is gentler, the save-aware pair don't just recall you — they DON'T TRUST the
# clean face. Flowey is gleeful; Sans is wary. Pure tension over real recorded
# routes (SACRED); the unease is theirs (FREE).

_SEVERITY = {"Pacifist": 1, "Neutral": 2, "Genocide": 3}


def _severity(route: Any) -> int:
    return _SEVERITY.get(route, 0)


def route_severity(route: Any) -> int:
    """Public route-severity rank (Pacifist<Neutral<Genocide; unknown=0).

    Shared with constellation.py so the moral ordering of routes is defined once.
    """
    return _severity(route)


def _has_blood(p: dict[str, Any]) -> bool:
    """A prior is genuinely dark only if its route is Genocide, or Neutral with
    at least one RECORDED kill — a clean Neutral leaves no echo to fear."""
    route = p.get("route")
    if route == "Genocide":
        return True
    if route == "Neutral":
        k = p.get("total_kills")
        return isinstance(k, int) and k > 0
    return False


def darkest_prior(priors: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The bloodiest prior save (highest route severity, then LOVE, then kills), or None."""
    ranked = [p for p in (priors or []) if p and _has_blood(p)]
    if not ranked:
        return None
    return max(
        ranked,
        key=lambda p: (_severity(p.get("route")), p.get("love") or 0, p.get("total_kills") or 0),
    )


_ECHO_VOICE = {
    "flowey": {
        "lead": "Oh — you're playing NICE this time.",
        "tail": "You, Flowey, are delighted and unbothered: you remember the other run and you "
                "won't let them pretend it away. Needle them, gleeful — never claim more than is recorded.",
    },
    "sans": {
        "lead": "you smile nice on this one.",
        "tail": "you, sans, are wary and guarded — you've seen what this hand did on another save, "
                "and you don't forget. keep an eye on them. never claim more than is recorded.",
    },
}


def build_echo_grounding(
    current: dict[str, Any],
    priors: list[dict[str, Any]],
    *,
    voice: str = "flowey",
) -> str:
    """The Other's Echo: a darker past behind a gentler present.

    Fires ONLY when the bloodiest prior save is genuinely darker (higher route
    severity) than the save in hand — a Genocide/bloodied-Neutral run remembered
    under a now-gentler face. "" otherwise (no darker prior, or the current save is
    already as dark). The blood is on a DIFFERENT file — but it is the same hand.
    """
    cur = current or {}
    dark = darkest_prior(priors)
    if not dark:
        return ""
    if _severity(dark.get("route")) <= _severity(cur.get("route")):
        return ""  # the save in hand is already as dark or darker — no echo to fear

    bits = []
    if isinstance(dark.get("love"), int):
        bits.append(f"LOVE {dark['love']}")
    if isinstance(dark.get("total_kills"), int):
        bits.append(f"{dark['total_kills']} recorded kills")
    detail = f" ({', '.join(bits)})" if bits else ""
    cur_route = cur.get("route") or "a path I can't yet read"

    v = _ECHO_VOICE.get(voice, _ECHO_VOICE["flowey"])
    lines = [
        "── THE OTHER'S ECHO (parser-confirmed across the saves shown here) ──",
        v["lead"],
        f"But on another save shown here, this same hand walked the {dark.get('route')} "
        f"path{detail}.",
        f"The save in front of you reads {cur_route}. The blood is on a DIFFERENT file — "
        "but it is the same hand on the keys.",
        v["tail"],
    ]
    return "\n".join(lines)
