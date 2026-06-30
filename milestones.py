#!/usr/bin/env python3
"""Milestones — the moments that make a character write in your journal unbidden.

When a save crosses a threshold (first steps, LV 20, a confirmed route, a reset, a
turned path), the fitting character leaves a page in the Keepsake Journal on their
own. Deterministic and parser-grounded: each entry states only what the save shows.
The app de-dupes by `kind`, so each milestone is written at most once per save.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

from ledger import detect_resets, detect_route_turn


def detect_milestones(save_truth: dict[str, Any], snapshots: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Milestone journal entries earned by the current save state. {kind, author, text}."""
    st = save_truth or {}
    play = st.get("play_state") or {}
    route = (st.get("route") or {}).get("route") or "undetermined"
    love = play.get("love")
    name = play.get("name") or "you"
    snaps = list(snapshots or [])
    out: list[dict[str, str]] = []

    if len(snaps) <= 1:
        out.append({"kind": "first_steps", "author": "Toriel",
                    "text": f"To {name}: you have only just arrived, and already I find myself "
                            "hoping for you. Be careful down here. — T"})
    if isinstance(love, int) and love >= 20:
        out.append({"kind": "love_ceiling", "author": "Sans",
                    "text": f"{name}. LV 20 — as high as it goes, and we both know what that costs. "
                            "writing it down so neither of us pretends otherwise."})
    if route == "Genocide":
        out.append({"kind": "genocide_confirmed", "author": "Sans",
                    "text": "the save's made it plain. i set the count down here and i won't soften it. "
                            "you know what you did."})
    if route == "Pacifist":
        out.append({"kind": "true_mercy", "author": "Toriel",
                    "text": f"To {name}: not a soul harmed, the save says — and I have read it twice to "
                            "be sure. Hold onto this kindness. It is yours."})
    if detect_resets(snaps):
        out.append({"kind": "the_reset", "author": "Flowey",
                    "text": "hee hee. the numbers went backward — you went back. don't worry, "
                            "*I* remember, even when they don't. i wrote it here so you can't pretend."})
    turn = detect_route_turn(snaps)
    if turn:
        out.append({"kind": "path_turned", "author": "Sans",
                    "text": f"the path bent from {turn['from']} to {turn['to']} between readings. "
                            "i noticed. i always notice."})
    return out
