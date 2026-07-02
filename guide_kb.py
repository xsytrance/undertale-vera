#!/usr/bin/env python3
"""Guided Mode's hint knowledge base — original, spoiler-tiered, progress-gated.

Three rungs on the hint ladder, chosen by the player's spoiler dial:
  nudge — a direction, no specifics ("keep heading east; talk before you fight")
  hint  — the shape of the next step, no solution
  tell  — plainly what to do next

All text here is OUR OWN concise phrasing (no copied guide text). Hints anchor to
what the save actually shows — Undertale: the current area (parser-derived);
Deltarune Ch1: coarse progression stages from corroborated facts (party
composition, the Jevil flag). We never reference content beyond the player's
recorded progress, and when the save doesn't show enough, we say so.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

import save_flavor

LEVELS = ("nudge", "hint", "tell")

# ── Undertale: keyed by area (parser-derived; never guessed) ─────────────────
UNDERTALE_GUIDE: dict[str, dict[str, str]] = {
    "the Ruins": {
        "nudge": "The Ruins teach by repetition — read the plaques, and remember you can always talk before you act.",
        "hint": "Puzzles here reset if you leave the room. Someone patient is guiding you; let her, until the road asks you to walk alone.",
        "tell": "Follow the rooms east and down, solving the switch and pressure-plate puzzles. When you reach the home at the end, the way onward is downstairs — you'll have to insist.",
    },
    "Snowdin": {
        "nudge": "The cold is friendlier than it looks. Every sentry here would rather be entertained than obeyed.",
        "hint": "The brothers' puzzles want an audience more than a solution. Keep east through the forest and the town will warm you.",
        "tell": "Head east through the puzzle gauntlet — most solve themselves if you play along. Past Snowdin town, the fog on the town's edge is the way forward.",
    },
    "Waterfall": {
        "nudge": "Water carries echoes here. Listen to the flowers — they only repeat what someone once meant.",
        "hint": "When the spears come, run and don't stop to fight the current. The tall grass hides more than it shows.",
        "tell": "Follow the marsh east: bridge seeds bloom when lined across the water, and when the chase comes, keep moving forward — the path ends at a cliff that isn't the end.",
    },
    "Hotland": {
        "nudge": "The heat measures resolve, not strength. Machines here follow rules — learn the rules, not the machine.",
        "hint": "Steam vents throw you where they point, and the conveyor mazes reward patience. Your phone is more useful than it was.",
        "tell": "Ride the vents in the direction they face, work the switch puzzles floor by floor, and take the elevators up. The show you keep getting pulled into ends at the Core's door.",
    },
    "the Core": {
        "nudge": "The Core rearranges itself for you — that isn't an accident.",
        "hint": "When the layout lies, trust the mercenaries' absence: the way that feels staged IS the stage. Look for the room that ends in an elevator.",
        "tell": "Push through the crossroads to the north; the force-field switches open the bridge. The elevator at the top leads to the final show, then to New Home.",
    },
    "New Home": {
        "nudge": "The house remembers a family. Let the keys find you.",
        "hint": "Two keys, two rooms on either wing, then the long hall of grey light. What you've done decides what the hall says.",
        "tell": "Take the kitchen key and the hallway key, unlock the chain on the stairs, and walk the Last Corridor. Beyond it, the throne room — and the choice the whole run was about.",
    },
    "_default": {
        "nudge": "Keep going the way the rooms lead — and talk before you act. Mercy is always on the table.",
        "hint": "The save shows where you are but not what's next from here; push to the next landmark and ask me again.",
        "tell": "I can only speak to what the save shows. Reach the next area or save point, save the game, and I'll read the road from there.",
    },
}

# ── Deltarune Ch1: coarse stages from corroborated facts (party, Jevil) ──────
DELTARUNE_STAGES: list[tuple[str, str, dict[str, str]]] = [
    # (stage key, human label, hints) — first match wins, checked in order
    ("jevil_done", "after the freed jester", {
        "nudge": "The lowest cell is quiet now. The only road left climbs.",
        "hint": "You've settled the thing beneath the castle. The throne above is waiting, and it won't settle itself.",
        "tell": "Take the Card Castle elevators to the top floors, through the throne room, and finish the chapter — the fountain is the end of the road.",
    }),
    ("full_party", "the whole party", {
        "nudge": "Three walk together now. Castles have doors for people like you.",
        "hint": "With the whole party mended, the Card Castle is the way — and if you like secrets, a shopkeeper mentioned a key in pieces.",
        "tell": "Head into Card Castle and climb floor by floor. Optional: gather the broken key pieces (the shop has one) and see the ??? cell in the basement before the throne.",
    }),
    ("with_ralsei", "two travellers", {
        "nudge": "A gentle prince makes a poor shield but a good compass. Keep east.",
        "hint": "The one who stormed off is still part of the prophecy. Follow the field toward the forest — you'll collect her the hard way.",
        "tell": "Cross the Field east (the Great Door, then the checkerboard), push through the Forest, and events will bring Susie back to the party at the castle's edge.",
    }),
    ("alone", "the very beginning", {
        "nudge": "Falling was the easy part. Walk — someone is waiting to explain everything far too politely.",
        "hint": "Head down and east through the dark until you meet a horned stranger with excellent manners.",
        "tell": "Follow the only road out of the starting caves; Ralsei meets you at the castle town and the adventure proper begins.",
    }),
]

DELTARUNE_UNKNOWN = {
    "nudge": "The Dark World keeps its own counsel — save the game and I'll read what it wrote.",
    "hint": "This save doesn't show me enough of your progress to point the way. Save again at the next fountain or door.",
    "tell": "I honestly can't tell where you are from this file. Save in-game and ask me again — the file will say more.",
}


def deltarune_stage(truth: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
    """The coarse Ch1 stage from corroborated facts. Honest fallback when unknown."""
    dr = (truth or {}).get("deltarune") or {}
    party = dr.get("party") or []
    if dr.get("jevil_defeated") is True:
        return DELTARUNE_STAGES[0]
    if "Susie" in party and "Ralsei" in party:
        return DELTARUNE_STAGES[1]
    if "Ralsei" in party:
        return DELTARUNE_STAGES[2]
    if party == ["Kris"] or party == []:
        if dr.get("party") is not None or (truth.get("play_state") or {}).get("name"):
            return DELTARUNE_STAGES[3]
    return ("unknown", "an unreadable stretch", DELTARUNE_UNKNOWN)


def hint_for(truth: dict[str, Any], level: str = "nudge") -> dict[str, Any]:
    """The progress-gated hint for a save, at a spoiler level. Never beyond the save."""
    lvl = level if level in LEVELS else "nudge"
    t = truth or {}
    if t.get("game") == "deltarune":
        key, label, hints = deltarune_stage(t)
        return {"game": "deltarune", "stage": key, "where": label, "level": lvl, "text": hints[lvl]}
    area = save_flavor.area_from_save(t)
    hints = UNDERTALE_GUIDE.get(area or "", UNDERTALE_GUIDE["_default"])
    return {"game": "undertale", "stage": area or "unknown", "where": area or "an unmarked stretch",
            "level": lvl, "text": hints[lvl]}
