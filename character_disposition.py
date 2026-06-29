#!/usr/bin/env python3
"""Per-character disposition — who the player killed, spared, or befriended (SACRED).

Derived ONLY from documented undertale.ini flags, each corpus-corroborated across a
real 64-save corpus and cross-checked against community flag docs. This is the
richest grounding for character chat: it lets a character speak to a *real* outcome
("you befriended my brother" / "you killed Toriel") instead of guessing — but every
claim here is a parser-confirmed fact, so it lives on the SACRED side of the wall.

THE WALL holds: a disposition is asserted only when its flag is actually set. No
flag → status "unknown" (the character simply isn't recorded), never a guess. A
character flagged BOTH killed and spared/befriended is "contradicted" (an edited
save) and is NOT asserted as any outcome.

PURE module (no DB/network/LLM) so it is unit-testable in isolation.
"""
from __future__ import annotations

from typing import Any, Optional

# character → {disposition: (ini_section, ini_key)}. Only flags whose meaning is
# both community-documented AND corpus-validated (set on the expected route, ~never
# on the other) appear here. Extend only with the same evidence bar.
DISPOSITION_FLAGS: dict[str, dict[str, tuple[str, str]]] = {
    "Toriel":  {"killed": ("toriel", "tk"), "spared": ("toriel", "ts")},
    "Papyrus": {"killed": ("papyrus", "pk"), "spared": ("papyrus", "ps"),
                "befriended": ("papyrus", "pd")},
    "Undyne":  {"befriended": ("undyne", "ud")},
    "Alphys":  {"befriended": ("alphys", "ad")},
}

# Human-readable phrasing for each status (used in the SACRED grounding block).
_STATUS_PHRASE = {
    "killed": "killed",
    "spared": "spared (left alive)",
    "befriended": "befriended / dated",
}


def _is_set(raw: Optional[str]) -> bool:
    if raw is None:
        return False
    try:
        return float(str(raw).strip().strip('"')) != 0.0
    except (TypeError, ValueError):
        return True  # non-numeric but present counts as set


def derive_dispositions(parsed) -> dict[str, dict[str, Any]]:
    """Map each known character to a disposition derived from set flags.

    Returns {character: {"status", "flags": [keys set], "character"}}. Status is one
    of killed / befriended / spared / unknown / contradicted. Precedence when several
    are set: a kill flag alongside a mercy flag is a contradiction (impossible in a
    real run); otherwise killed > befriended > spared.
    """
    out: dict[str, dict[str, Any]] = {}
    has_ini = hasattr(parsed, "ini_get")
    for character, flagmap in DISPOSITION_FLAGS.items():
        set_keys = []
        present = {}
        for status, (section, key) in flagmap.items():
            raw = parsed.ini_get(section, key) if has_ini else None
            if _is_set(raw):
                present[status] = True
                set_keys.append(key)
        killed = present.get("killed", False)
        mercy = present.get("befriended", False) or present.get("spared", False)
        if killed and mercy:
            status = "contradicted"
        elif killed:
            status = "killed"
        elif present.get("befriended"):
            status = "befriended"
        elif present.get("spared"):
            status = "spared"
        else:
            status = "unknown"
        out[character] = {"character": character, "status": status, "flags": set_keys}
    return out


def known_dispositions(parsed) -> dict[str, str]:
    """Just the characters with a definite outcome: {character: status}.

    Excludes 'unknown' (not recorded) and 'contradicted' (edited/impossible) — only
    facts we can stand behind.
    """
    return {
        c: d["status"]
        for c, d in derive_dispositions(parsed).items()
        if d["status"] in _STATUS_PHRASE
    }


def _known_from_map(dispositions: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Filter a derived-dispositions map down to definite outcomes (shared helper)."""
    return {
        c: (d or {}).get("status")
        for c, d in (dispositions or {}).items()
        if (d or {}).get("status") in _STATUS_PHRASE
    }


def _render(known: dict[str, str]) -> str:
    if not known:
        return ""
    lines = [
        "── WHO YOU'VE MET (parser-confirmed from the save — never invent beyond this) ──",
        "The save records these outcomes with monsters encountered so far:",
    ]
    for character, status in known.items():
        lines.append(f"  - {character}: {_STATUS_PHRASE[status]}")
    lines.append(
        "Speak to these only as they fit, in character. They are hard facts. Anyone "
        "not listed is simply not recorded — do not invent an outcome for them."
    )
    return "\n".join(lines)


def grounding_from_truth(save_truth: dict[str, Any]) -> str:
    """SACRED disposition block built from a stored SaveTruth's `dispositions`.

    The chat path works off persisted SaveTruth (not a live parse), so this reads
    the already-derived map. "" when nothing definite is recorded (baseline-safe).
    """
    return _render(_known_from_map((save_truth or {}).get("dispositions") or {}))


def build_disposition_grounding(parsed) -> str:
    """SACRED prompt block listing parser-confirmed character outcomes (from a parse).

    Returns "" when nothing definite is recorded, so the no-disposition grounding
    stays byte-identical to the baseline (the same discipline as the other blocks).
    """
    return _render(known_dispositions(parsed))
