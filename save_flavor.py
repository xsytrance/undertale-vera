#!/usr/bin/env python3
"""Save texture + the Fun-value anomaly — the deep cuts that make a save feel KNOWN.

Beyond route and stats, an Undertale save records small, intimate things — how long
you've been Underground, the flavour of the pie Toriel baked you, and the single
most mysterious number in the game: the **Fun value**, which silently gates Gaster's
followers, the gray-door Mystery Man, and the Goner Kid.

Everything here is parser-derived FACT (the recorded number/flag), so it grounds the
SACRED side of the wall. The Fun-value *events* are documented, community-verified
lore tied to a real recorded number — surfaced for the save/meta-aware characters
(Sans, Flowey) as an unsettling truth, never invented.

PURE module (no DB/network/LLM). Sources cross-checked against the Undertale Wiki
and CYBERPEDIA Fun-value documentation.
"""
from __future__ import annotations

from typing import Any, Optional

# ── area, from the documented room name ──────────────────────────────────────
# undertale.ini [General].RoomName is the reliable area signal (room *numbers*
# shift across versions, so we don't guess area from those). Substring → area.
_AREA_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("ruins",), "the Ruins"),
    (("snowdin", "tundra"), "Snowdin"),
    (("water",), "Waterfall"),
    (("hotland", "fire"), "Hotland"),
    (("core",), "the CORE"),
    (("truelab", "true_lab"), "the True Lab"),
    (("lab",), "the Lab"),
    (("castle", "new_home", "newhome", "barrier", "throne"), "the King's castle"),
    (("town",), "a town"),
)


# Room-id → area fallback, used ONLY when no room name is recorded. Boundaries were
# derived from the real 64-save corpus (each room id cross-checked against its scene
# label) and matched 64/64. Room numbers can shift across game versions, so this is a
# best-effort secondary to the room name; ids outside the validated span → None.
ROOM_AREA_RANGES: tuple[tuple[int, int, str], ...] = (
    (1, 45, "the Ruins"),
    (46, 82, "Snowdin"),
    (83, 138, "Waterfall"),
    (139, 195, "Hotland"),
    (196, 218, "the CORE"),
    (219, 245, "the King's castle"),
    (246, 260, "the True Lab"),
)


def _area_from_room_id(room: Any) -> Optional[str]:
    try:
        rid = int(room)
    except (TypeError, ValueError):
        return None
    for lo, hi, area in ROOM_AREA_RANGES:
        if lo <= rid <= hi:
            return area
    return None


def area_from_save(save_truth: dict[str, Any]) -> Optional[str]:
    """The area: from the recorded room NAME first, else the room-id range fallback.

    None when neither is available or in range — never guessed.
    """
    play = (save_truth or {}).get("play_state") or {}
    room_name = (play.get("room_name") or "").strip().lower()
    if room_name:
        for keywords, area in _AREA_KEYWORDS:
            if any(k in room_name for k in keywords):
                return area
        # A room name we don't recognise — fall through to the id, don't guess.
    return _area_from_room_id(play.get("room"))


# ── Toriel's pie flavour ([Toriel] Bscotch: 1 butterscotch, 2 cinnamon) ──────
_PIE = {1: "butterscotch", 2: "cinnamon"}


def pie_flavor(save_truth: dict[str, Any]) -> Optional[str]:
    """The flavour of pie Toriel made, if recorded. (Disposition's warm cousin.)"""
    bscotch = ((save_truth or {}).get("play_state") or {}).get("toriel_pie")
    if bscotch is None:
        return None
    try:
        return _PIE.get(int(bscotch))
    except (TypeError, ValueError):
        return None


# ── play time (file0/[General] Time is in frames at 30 fps) ──────────────────
def humanize_playtime(frames: Optional[int]) -> Optional[str]:
    """Frames → a soft human phrase ('about 3 hours'). None when unknown."""
    if not isinstance(frames, int) or frames <= 0:
        return None
    seconds = frames / 30.0
    minutes = seconds / 60.0
    if minutes < 1:
        return "under a minute"
    if minutes < 60:
        n = max(1, round(minutes))
        return f"about {n} minute" + ("s" if n != 1 else "")
    hours = minutes / 60.0
    n = round(hours)
    if n < 1:
        return "about an hour"
    return f"about {n} hour" + ("s" if n != 1 else "")


# ── the Fun value (the deepest cut) ──────────────────────────────────────────
# (lo, hi, name, where, blurb, tier). 'gaster' tier = the eerie W. D. Gaster
# mysteries; 'quirk' = the lighter rare events. Ranges per the Undertale Wiki.
FUN_EVENTS: tuple[tuple[int, int, str, str, str, str], ...] = (
    (2, 39, "the Wrong Number Song", "Snowdin", "a phone rings with a song meant for no one", "quirk"),
    (46, 50, "a mysterious mis-dialed call", "Snowdin", "a call comes through that was never meant for you", "quirk"),
    (56, 57, "the Nightmare in the word search", "Snowdin", "a bear-faced figure hides where it shouldn't", "quirk"),
    (61, 61, "a Gaster Follower", "Hotland", "a monster speaks of the royal scientist who came before — W. D. Gaster", "gaster"),
    (62, 62, "a Gaster Follower", "Hotland", "a monster recalls the scientist who shattered across time and space", "gaster"),
    (63, 63, "a Gaster Follower", "Hotland", "a monster who barely remembers the one who fell into his own creation", "gaster"),
    (65, 65, "the Sound Test Room", "Snowdin", "a hidden room of music that should not exist", "gaster"),
    (66, 66, "the gray door / the Mystery Man", "Waterfall", "a door that isn't there, and a man who melts into Gaster's theme", "gaster"),
    (90, 100, "the Goner Kid", "Waterfall", "a gray, hollow child who isn't sure they were ever real", "gaster"),
)


def fun_value_event(fun: Optional[int]) -> Optional[dict[str, Any]]:
    """The documented event a Fun value unlocks, or None for the common (no-event) values."""
    if not isinstance(fun, int):
        return None
    for lo, hi, name, where, blurb, tier in FUN_EVENTS:
        if lo <= fun <= hi:
            return {"value": fun, "name": name, "where": where, "blurb": blurb, "tier": tier}
    return None


# ── grounding blocks ─────────────────────────────────────────────────────────
def build_texture_grounding(save_truth: dict[str, Any]) -> str:
    """SACRED 'small recorded details' block (area, time, pie). '' when nothing known."""
    st = save_truth or {}
    play = st.get("play_state") or {}
    bits: list[str] = []
    area = area_from_save(st)
    if area:
        bits.append(f"Right now the save sits in {area}.")
    pt = humanize_playtime(play.get("play_time_frames"))
    if pt:
        bits.append(f"Time on this save: {pt} Underground.")
    pie = pie_flavor(st)
    if pie:
        bits.append(f"The pie Toriel baked was {pie}.")
    if not bits:
        return ""
    return (
        "── SMALL THINGS THE SAVE REMEMBERS (parser-confirmed; reference only if it fits) ──\n"
        + " ".join(bits)
    )


def build_anomaly_grounding(save_truth: dict[str, Any]) -> str:
    """SACRED Fun-value anomaly block for save/meta-aware characters. '' when no event."""
    play = (save_truth or {}).get("play_state") or {}
    event = fun_value_event(play.get("fun"))
    if not event:
        return ""
    head = (
        "── AN ANOMALY IN THE CODE (the Fun value is a real recorded number — do not "
        "explain it away, but never invent beyond this) ──"
    )
    body = (
        f"This save's Fun value is {event['value']}. At that exact number the game "
        f"quietly allows {event['name']} to surface in {event['where']} — {event['blurb']}."
    )
    if event["tier"] == "gaster":
        body += (
            " This is one of the deepest secrets in the Underground — the trace of "
            "someone the world forgot. You may speak of it knowingly, uneasily, as "
            "something you were never quite supposed to notice."
        )
    return head + "\n" + body
