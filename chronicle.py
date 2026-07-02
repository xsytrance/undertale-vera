#!/usr/bin/env python3
"""The Chronicle — a save's whole story, narrated from parser-truth alone.

Everything the app mined — route, the journey (area, play time), who was killed /
spared / befriended, the save's cross-visit memory, the Fun-value anomaly, and the
verdict — rendered as one shareable Markdown artifact. It is the payoff for the
SACRED side of the wall: a narrated record that invents NOTHING. Unknowns are left
unwritten, never guessed; an undetermined route is named, not filled in.

PURE module (no DB/network/LLM): `build_chronicle(save_truth, snapshots)` returns a
deterministic {markdown, title, route} dict, reusing the existing sacred helpers.
"""
from __future__ import annotations

from typing import Any, Optional

import affinity as affinity_mod
import save_flavor
from judgment import classify_verdict
from ledger import detect_route_turn, detect_resets

# How a recorded disposition reads in the Chronicle (definite outcomes only).
_DISPOSITION_PHRASE = {
    "killed": "killed",
    "spared": "spared",
    "befriended": "befriended",
}


def _definite_dispositions(save_truth: dict[str, Any]) -> dict[str, str]:
    return {
        char: (d or {}).get("status")
        for char, d in (save_truth.get("dispositions") or {}).items()
        if (d or {}).get("status") in _DISPOSITION_PHRASE
    }


def _fmt(value: Any, unknown: str = "not recorded") -> str:
    return unknown if value in (None, "") else str(value)


def build_chronicle(
    save_truth: dict[str, Any],
    snapshots: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Render the save into a narrated Markdown Chronicle. Facts only; unknowns blank."""
    st = save_truth or {}
    play = st.get("play_state") or {}
    route_block = st.get("route") or {}
    kills = st.get("kills") or {}
    snaps = list(snapshots or [])

    name = play.get("name")
    route = route_block.get("route") or "undetermined"
    confidence = route_block.get("confidence") or "unknown"
    title = f"The Chronicle of {name}" if name else "The Chronicle of an Unnamed Fallen Human"

    lines: list[str] = [
        f"# {title}",
        "",
        "*Recorded from the save, and nothing more. Facts are sacred; the unknown is "
        "left unwritten.*",
        "",
        "## The Path",
    ]
    if route == "undetermined":
        lines.append(
            "The save has not yet revealed which path is walked. No route is claimed "
            f"(confidence: {confidence})."
        )
    else:
        lines.append(f"This save walks the **{route}** route (confidence: {confidence}).")

    # ── The Record ───────────────────────────────────────────────────────────
    lines += ["", "## The Record",
              f"- LOVE (LV): {_fmt(play.get('love'))}",
              f"- Recorded kills: {_fmt(kills.get('total'))}"]
    area = save_flavor.area_from_save(st)
    if area:
        lines.append(f"- Furthest known place: {area}")
    playtime = save_flavor.humanize_playtime(play.get("play_time_frames"))
    if playtime:
        lines.append(f"- Time elapsed: {playtime} Underground")
    pie = save_flavor.pie_flavor(st)
    if pie:
        lines.append(f"- The pie Toriel baked: {pie}")

    # ── Those You Met ────────────────────────────────────────────────────────
    dispositions = _definite_dispositions(st)
    if dispositions:
        lines += ["", "## Those You Met"]
        for char, status in dispositions.items():
            lines.append(f"- {char} — {_DISPOSITION_PHRASE[status]}")

    # ── What the Save Remembers (across visits) ──────────────────────────────
    if len(snaps) >= 2:
        lines += ["", "## What the Save Remembers",
                  f"This save has been read {len(snaps)} times."]
        turn = detect_route_turn(snaps)
        if turn:
            lines.append(
                f"Between readings, the path turned from {turn['from']} to {turn['to']}."
            )
        resets = detect_resets(snaps)
        if resets:
            r = resets[-1]
            lines += ["", "## The Timeline Bends",
                      f"The recorded {r['field']} fell from {r['from']} to {r['to']} between "
                      "readings — a number that never drops on its own. An earlier state was "
                      "loaded. Someone reached back."]

    # ── An Anomaly (the Fun value) ───────────────────────────────────────────
    event = save_flavor.fun_value_event(play.get("fun"))
    if event:
        lines += ["", "## An Anomaly",
                  f"The Fun value reads {event['value']}. At that exact number, the "
                  f"Underground quietly allows {event['name']} to surface in "
                  f"{event['where']} — {event['blurb']}."]

    # ── How the Underground Regards You (derived stances) ────────────────────
    if route != "undetermined":
        lines += ["", "## How the Underground Regards You"]
        for who, a in affinity_mod.all_affinities(st).items():
            lines.append(f"- {who} — *{a['stance']}* ({a['gloss']})")

    # ── The Verdict ──────────────────────────────────────────────────────────
    verdict = classify_verdict(route)
    lines += ["", "## The Verdict", f"**{verdict['label']}.** {verdict['line']}"]

    lines += ["", "---",
              "*This Chronicle holds only what the save recorded. Everything it does "
              "not know, it does not say.*"]

    return {"markdown": "\n".join(lines), "title": title, "route": route}
