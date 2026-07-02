#!/usr/bin/env python3
"""Deltarune SaveTruth — the Chapter 1 save, normalized into the app's truth shape.

Produces a dict compatible with the Undertale SaveTruth consumed by the prompt wall,
the shelf, snapshots, and every feature module — plus a `deltarune` block for
chapter-specific facts (party, dark dollars, the Jevil flag, room, time).

Honesty rules carried over verbatim:
  - unknowns are None, never guessed.
  - Chapter 1's route (Pacifist vs Violent) is NOT derivable from corroborated flags
    yet (the corpus is a single peaceful run), so route = "undetermined"/"unknown".
  - LV in Deltarune is famously always 1; we report it only when dr.ini SAYS so.
  - dr.ini (optional) corroborates: agreements lift nothing silently, disagreements
    become warnings — cross-source honesty, not averaging.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any, Optional

SCHEMA_VERSION = 2


def build_deltarune_truth(
    parsed: dict[str, Any],
    dr_ini: Optional[dict[str, Any]] = None,
    source_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a parse_deltarune_save() result (+ optional parse_dr_ini) to truth."""
    f = parsed.get("fields") or {}
    conf = dict(parsed.get("confidence") or {})
    warnings = list(parsed.get("warnings") or [])
    ini = dr_ini or {}

    # cross-source checks (dr.ini is the completion-time summary)
    if ini:
        if ini.get("name") and f.get("name") and ini["name"] != f["name"]:
            warnings.append(f"dr.ini Name {ini['name']!r} disagrees with save line 1 {f['name']!r}")
        if ini.get("room") is not None and f.get("room") is not None and ini["room"] != f["room"]:
            warnings.append("dr.ini Room disagrees with the save's room line")

    # the Jevil flag: 0 = untouched; 2 = resolved/defeated (dr.ini UraBoss agrees).
    jevil_state = f.get("jevil_state")
    if jevil_state is None and ini.get("uraboss") is not None:
        jevil_state = ini["uraboss"]
        conf["jevil_state"] = "medium"   # summary-only source

    return {
        "schema_version": SCHEMA_VERSION,
        "game": "deltarune",
        "chapter": parsed.get("chapter"),
        "source": {
            "digest": parsed.get("digest"),
            "slot": parsed.get("slot"),
            "line_count": parsed.get("line_count"),
            "expected_layout": parsed.get("expected_layout"),
            "dr_ini": bool(ini),
            **(source_meta or {}),
        },
        "play_state": {
            "name": f.get("name"),
            "love": ini.get("love"),            # only when dr.ini says so (famously 1)
            "lv": ini.get("level"),
            "max_hp": None,
            "room": f.get("room") if f.get("room") is not None else ini.get("room"),
            "room_name": None,                  # no corroborated id→name map yet
            "play_time_frames": f.get("time") if f.get("time") is not None else ini.get("time"),
            "gold": f.get("dark_dollars"),      # the shelf's "money" concept
            "fun": None,
            "toriel_pie": None,
        },
        "kills": {"total": None, "by_area": None},
        "route": {
            "route": "undetermined",
            "confidence": "unknown",
            "reasons": [
                "Chapter 1 route (Pacifist vs Violent) is not derivable from "
                "corroborated save flags yet — reported honestly as undetermined "
                "rather than guessed."
            ],
        },
        "deltarune": {
            "dark_dollars": f.get("dark_dollars"),
            "party": f.get("party"),
            "jevil_state": jevil_state,
            "jevil_defeated": (jevil_state == 2) if jevil_state is not None else None,
        },
        "confidence": {
            "name": conf.get("name", "unknown"),
            "dark_dollars": conf.get("dark_dollars", "unknown"),
            "party": conf.get("party", "unknown"),
            "jevil_state": conf.get("jevil_state", "unknown"),
            "room": conf.get("room", "unknown"),
            "time": conf.get("time", "unknown"),
            "route": "unknown",
        },
        "warnings": warnings,
    }


def deltarune_delta(prev_truth: dict[str, Any], curr_truth: dict[str, Any]) -> list[str]:
    """Honest plain-language deltas between two Deltarune truths (the Dark World's
    own change language — the generic ledger only speaks LOVE/route/kills, which
    Chapter 1 saves don't move). Facts only; nothing inferred."""
    out: list[str] = []
    p = (prev_truth or {}).get("deltarune") or {}
    c = (curr_truth or {}).get("deltarune") or {}
    pp, cp = (prev_truth or {}).get("play_state") or {}, (curr_truth or {}).get("play_state") or {}

    # dark dollars
    a, b = p.get("dark_dollars"), c.get("dark_dollars")
    if isinstance(a, int) and isinstance(b, int) and a != b:
        out.append(f"dark dollars {'rose' if b > a else 'fell'} from {a} to {b}")

    # the party
    pa, pb = p.get("party") or [], c.get("party") or []
    joined = [m for m in pb if m not in pa]
    left = [m for m in pa if m not in pb]
    for m in joined:
        out.append(f"{m} joined the party")
    for m in left:
        out.append(f"{m} left the party")

    # the jester
    if p.get("jevil_defeated") is not True and c.get("jevil_defeated") is True:
        out.append("the freed jester below the castle was faced, and bested")

    # the room (id only — names are honestly unmapped)
    ra, rb = pp.get("room"), cp.get("room")
    if isinstance(ra, int) and isinstance(rb, int) and ra != rb:
        out.append(f"moved on (room {ra} → {rb})")
    return out
