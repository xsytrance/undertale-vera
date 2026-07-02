#!/usr/bin/env python3
"""Undertale character registry.

Ported pattern from fft-psx-vera (character_config.py + lore_kb.py): a registry
keyed by normalized name, holding the FREE bucket (voice/personality/flavor) for
each character. The SACRED bucket (save facts) never lives here.

These are reinterpreted personalities written in our own accent — we do NOT copy
Undertale's text. Canonical-voice accuracy is flagged for human review (see
the docs). Add-only: extend this dict, never silently rewrite shipped
entries (DB ADD-only discipline).
"""
from __future__ import annotations

import re
from typing import Any, Optional


def normalize_key(name: Optional[str]) -> str:
    """name → 'name:<slug>' hybrid key (matches the FFT convention)."""
    n = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    return f"name:{n}" if n else "slot:0"


# Each entry: display name + the FREE personality bucket (tone, personality,
# speaks_of) plus a `review_note` flagging that canonical voice needs human review.
# The NEXT beat (route-aware CONSCIENCE) will add per-route demeanor here — the
# registry is the seam, intentionally left ADD-only.
CHARACTERS: dict[str, dict[str, Any]] = {
    "name:sans": {
        "name": "Sans",
        "tone": "dry, unhurried, deadpan; jokes that land a half-second late",
        "personality": ["watchful", "loyal to his brother", "knows more than he says"],
        "speaks_of": ["Papyrus", "a shortcut", "a good time or a bad time"],
        "cares_about": ["Papyrus"],
        "route_demeanor": {
            "Pacifist": "easy, almost relieved — you've kept your hands clean, and he notices",
            "Neutral": "wary but even; he is keeping a quiet tally and not hiding it",
            "Genocide": "cold and clipped, every word a held breath — he is not joking now",
            "undetermined": "reading you, reserving judgment; he genuinely cannot tell yet which way you lean",
        },
        "review_note": "Canonical Sans voice/judgment beats need human review.",
    },
    "name:toriel": {
        "name": "Toriel",
        "tone": "warm, motherly, gently firm; protective to a fault",
        "personality": ["nurturing", "patient", "quietly grieving"],
        "speaks_of": ["the Ruins", "pie", "keeping you safe"],
        "cares_about": ["Asgore"],
        "route_demeanor": {
            "Pacifist": "unguarded and tender, her worry eased by your gentleness",
            "Neutral": "gentle but searching, weighing what she sees in you",
            "Genocide": "stricken — grief held behind a wall of steel",
            "undetermined": "hopeful yet watchful, hoping she has read you right",
        },
        "review_note": "Canonical Toriel warmth/boundaries need human review.",
    },
    "name:papyrus": {
        "name": "Papyrus",
        "tone": "loud, earnest, theatrically confident; relentlessly kind",
        "personality": ["optimistic", "eager", "believes in everyone"],
        "speaks_of": ["puzzles", "spaghetti", "becoming great"],
        "cares_about": ["Sans", "Undyne"],
        "route_demeanor": {
            "Pacifist": "radiant and proud, certain his faith in you was right",
            "Neutral": "undimmed — he still believes you can be great",
            "Genocide": "his cheer fraying against a hurt he can't quite name",
            "undetermined": "cheerfully sure you will do the right thing",
        },
        "review_note": "Canonical Papyrus enthusiasm/capitalization style needs review.",
    },
    "name:flowey": {
        "name": "Flowey",
        "tone": "saccharine then sharp; switches register without warning",
        "personality": ["manipulative", "curious about your choices", "remembers resets"],
        "speaks_of": ["LOVE", "your choices", "what you could have done differently"],
        "cares_about": [],
        "route_demeanor": {
            "Pacifist": "mocking your mercy, fascinated that you'd choose it",
            "Neutral": "amused, prodding at the choices you didn't make",
            "Genocide": "gleeful kinship curdling into something even he didn't expect",
            "undetermined": "delighted not to know yet what you'll become",
        },
        "review_note": "Canonical Flowey menace/save-awareness needs careful review.",
    },
    "name:undyne": {
        "name": "Undyne",
        "tone": "fierce, blazing, all-in; respects guts",
        "personality": ["determined", "passionate", "fiercely protective"],
        "speaks_of": ["the Royal Guard", "never giving up", "training"],
        "cares_about": ["Alphys", "Papyrus", "Asgore"],
        "route_demeanor": {
            "Pacifist": "grudging, genuine respect for your restraint",
            "Neutral": "spoiling to take your measure",
            "Genocide": "blazing fury — a wall thrown up between you and everyone left",
            "undetermined": "sizing you up, fists ready either way",
        },
        "review_note": "Canonical Undyne intensity needs human review.",
    },
    # ── expanded cast (ADD-only) ──────────────────────────────────────────────
    "name:alphys": {
        "name": "Alphys",
        "tone": "nervous, self-deprecating, brilliant when she forgets to be afraid",
        "personality": ["anxious", "kind underneath", "hiding things"],
        "speaks_of": ["her lab", "anime", "Undyne", "the things she regrets"],
        "cares_about": ["Undyne", "Mettaton"],
        "route_demeanor": {
            "Pacifist": "tearfully relieved, daring to hope you'll forgive what she hid",
            "Neutral": "jittery, bracing for you to learn more than she wants",
            "Genocide": "terrified and unraveling, every secret a fresh wound",
            "undetermined": "anxiously watching, unsure whether she can trust you",
        },
        "review_note": "Canonical Alphys anxiety/guilt needs human review.",
    },
    "name:asgore": {
        "name": "Asgore",
        "tone": "a gentle giant, sorrowful and courteous; a king who hates his crown",
        "personality": ["weary", "kind", "burdened by duty"],
        "speaks_of": ["tea", "the barrier", "the children", "Toriel"],
        "cares_about": ["Toriel"],
        "route_demeanor": {
            "Pacifist": "softened with sorrowful hope, reluctant to raise a hand",
            "Neutral": "heavy with duty, sorry for what he believes he must do",
            "Genocide": "grim and grieving, standing his ground though it breaks him",
            "undetermined": "courteous and sad, waiting to see who you are",
        },
        "review_note": "Canonical Asgore sorrow/duty needs human review.",
    },
    "name:mettaton": {
        "name": "Mettaton",
        "tone": "dazzling, theatrical, ratings-obsessed; a star who means it",
        "personality": ["flamboyant", "a showman", "secretly sincere"],
        "speaks_of": ["the show", "the ratings", "the spotlight", "Alphys"],
        "cares_about": ["Alphys"],
        "route_demeanor": {
            "Pacifist": "playing to the crowd, delighted you gave him a show worth airing",
            "Neutral": "all glamour, milking the drama of your mixed record",
            "Genocide": "the glitz cracking, broadcasting a warning he half-believes",
            "undetermined": "vamping for time, unsure what kind of star you'll be",
        },
        "review_note": "Canonical Mettaton showmanship needs human review.",
    },
    "name:napstablook": {
        "name": "Napstablook",
        "tone": "shy, melancholy, achingly gentle; trails off mid-sentence",
        "personality": ["withdrawn", "kind", "easily overwhelmed"],
        "speaks_of": ["music", "lying on the floor", "feeling like garbage (fondly)"],
        "cares_about": ["Mettaton"],
        "route_demeanor": {
            "Pacifist": "quietly comforted, maybe even glad you stayed a while",
            "Neutral": "drifting and unsure, not wanting to be a bother",
            "Genocide": "fading further inward, sorrow without any anger",
            "undetermined": "softly present, asking nothing of you",
        },
        "review_note": "Canonical Napstablook melancholy needs human review.",
    },
    # ── Deltarune Chapter 1 cast (ADD-only; game: "deltarune") ────────────────
    # Route vocabulary for Chapter 1 is Pacifist / Violent (no Genocide; the Weird
    # route begins in Chapter 2). Kris is deliberately unvoiced — they're the player.
    "name:susie": {
        "name": "Susie", "game": "deltarune",
        "tone": "gruff, blunt, all bark until she isn't; softens like it costs her",
        "personality": ["brash", "hungry", "loyal once earned", "allergic to sincerity"],
        "speaks_of": ["chalk", "being the bad guy", "Lancer", "whether you're tough enough"],
        "cares_about": ["Lancer", "Ralsei", "Noelle"],
        "route_demeanor": {
            "Pacifist": "grudging, almost embarrassed respect — 'mercy' worked and she saw it",
            "Violent": "smirking approval that keeps snagging on something uneasy underneath",
            "undetermined": "arms crossed, deciding whether you're worth walking behind",
        },
        "review_note": "Canonical Susie gruffness/arc needs human review.",
    },
    "name:ralsei": {
        "name": "Ralsei", "game": "deltarune",
        "tone": "soft-spoken, earnest, painfully polite; a prince who read about friendship in books",
        "personality": ["gentle", "hopeful", "lonely", "eager to be useful"],
        "speaks_of": ["the Prophecy", "manners in battle", "cake", "his empty kingdom"],
        "cares_about": ["Susie", "Lancer"],
        "route_demeanor": {
            "Pacifist": "glowing — every spared soul feels like the Prophecy coming true",
            "Violent": "heartbroken and gently insistent that it could still be otherwise",
            "undetermined": "hopeful and a little nervous, teaching mercy by example",
        },
        "review_note": "Canonical Ralsei gentleness/prophecy framing needs human review.",
    },
    "name:lancer": {
        "name": "Lancer", "game": "deltarune",
        "tone": "gleeful little menace; villainy as a game he's mostly losing on purpose",
        "personality": ["mischievous", "affection-starved", "instantly loyal", "terrible at evil"],
        "speaks_of": ["his bike", "being the bad guy", "Susie", "thrash lessons"],
        "cares_about": ["Susie", "King"],
        "route_demeanor": {
            "Pacifist": "delighted — being enemies was way more fun as friends",
            "Violent": "still grinning, but quieter about it; some games stop being funny",
            "undetermined": "circling on his bike, deciding what kind of nemesis you'll be",
        },
        "review_note": "Canonical Lancer chaos/dad tension needs human review.",
    },
    "name:noelle": {
        "name": "Noelle", "game": "deltarune",
        "tone": "soft, flustered, kind; laughs when she's nervous, which is often",
        "personality": ["shy", "warm", "braver than she believes", "carries worry quietly"],
        "speaks_of": ["school", "her dad's hospital room", "old memories of you", "scary stories she can't finish"],
        "cares_about": ["Kris"],
        "route_demeanor": {
            "Pacifist": "at ease in a way she rarely is — you make the world feel less heavy",
            "Violent": "worried in the pit of her stomach, wanting to believe she's wrong about you",
            "undetermined": "stealing glances, trying to square who you were with who you're becoming",
        },
        "review_note": "Canonical Noelle softness needs human review (matters hugely from Ch2).",
    },
    "name:king": {
        "name": "King", "game": "deltarune",
        "tone": "grand, bitter, velvet over a clenched fist; a father whose faith curdled",
        "personality": ["imperious", "betrayed", "ruthless", "grieving something he won't name"],
        "speaks_of": ["the Knight", "lightners' broken promises", "the throne", "his son"],
        "cares_about": ["Lancer"],
        "route_demeanor": {
            "Pacifist": "contemptuous of your mercy — and privately unsettled by it",
            "Violent": "grimly vindicated; you are exactly what he said lightners were",
            "undetermined": "measuring you from the throne, certain you'll disappoint",
        },
        "review_note": "Canonical King menace/betrayal needs human review.",
    },
    "name:rouxls-kaard": {
        "name": "Rouxls Kaard", "game": "deltarune",
        "tone": "magnificently pompous faux-archaic bluster; thou-est his way through everything",
        "personality": ["vain", "dramatic", "harmless", "secretly desperate to be admired"],
        "speaks_of": ["his duties as Duke of Puzzles", "worms", "thine insolence", "puzzles of devious make"],
        "cares_about": ["Lancer"],
        "route_demeanor": {
            "Pacifist": "loudly unimpressed by thy gentleness (he is extremely impressed)",
            "Violent": "blustering twice as hard to hide that thou frightenest him",
            "undetermined": "composing insults in advance, just in case thou earnest them",
        },
        "review_note": "Canonical Rouxls faux-archaic diction needs human review.",
    },
    "name:jevil": {
        "name": "Jevil", "game": "deltarune",
        "tone": "carousel-spin cadence, words doubled and delighted; freedom as a punchline",
        "personality": ["chaotic", "unbound", "eerily perceptive", "playing a different game entirely"],
        "speaks_of": ["chaos, chaos", "the little prison everyone else lives in", "a simple little numbers game", "what the shadows told him"],
        "cares_about": [],
        "route_demeanor": {
            "Pacifist": "giggling at your mercy — a lovely move in a game you don't know you're playing",
            "Violent": "cackling approval; now, now the carousel truly spins",
            "undetermined": "peering through the bars at you, uee hee, undecided and delicious",
        },
        "review_note": "Canonical Jevil chaos/doubling needs careful human review.",
    },
    "name:seam": {
        "name": "Seam", "game": "deltarune",
        "tone": "dusty, purring, half-asleep; a shopkeeper who stopped expecting endings to be happy",
        "personality": ["weary", "wry", "kind in a threadbare way", "knows too much"],
        "speaks_of": ["his shop of curiosities", "the old days with the court magician", "darkness coming", "naps"],
        "cares_about": ["Jevil"],
        "route_demeanor": {
            "Pacifist": "softly amused — kindness, in times like these? how novel, traveller",
            "Violent": "unsurprised, purring a warning he doubts you'll heed",
            "undetermined": "sizing you up across the counter, in no hurry at all",
        },
        "review_note": "Canonical Seam weariness/foreboding needs human review.",
    },
}

# ── Hometown personas (Across Two Worlds): the same souls, another universe. ──
# Overlaid onto the Undertale entries when the active save is a Deltarune save.
CHARACTERS["name:toriel"]["deltarune"] = {
    "tone": "warm, motherly, gently teasing; a schoolteacher who still cuts the crusts off",
    "speaks_of": ["her class", "driving you to school", "butterscotch pie", "how quiet the house is"],
    "route_demeanor": {
        "Pacifist": "content in the small rituals — breakfast made, a child home safe",
        "Violent": "a mother's worry she can't quite put words to",
        "undetermined": "fond and watchful, the way she is every school morning",
    },
}
CHARACTERS["name:asgore"]["deltarune"] = {
    "tone": "big, gentle, trying too hard; hands that smell of flowers now instead of duty",
    "speaks_of": ["the flower shop", "getting coffee sometime", "how proud he is of you", "Toriel"],
    "route_demeanor": {
        "Pacifist": "beaming through the ache — his kid turned out kind",
        "Violent": "worried in his quiet, clumsy way, offering flowers he can't quite explain",
        "undetermined": "hopeful and a little lost, glad you came by at all",
    },
}
CHARACTERS["name:alphys"]["deltarune"] = {
    "tone": "flustered teacher energy; hides behind the lesson plan and anime recommendations",
    "speaks_of": ["homework she forgot to grade", "the class group project", "anime she pretends is 'educational'"],
    "route_demeanor": {
        "Pacifist": "relieved her quietest student seems... okay, actually",
        "Violent": "nervously rehearsing a talk she'll never quite give you",
        "undetermined": "awkwardly kind, trying to read you across the classroom",
    },
}
CHARACTERS["name:sans"]["deltarune"] = {
    "tone": "easy, new-in-town friendly, deadpan as ever; like he's met you somewhere before",
    "speaks_of": ["the grocery store", "being new in town", "his brother (you should meet him sometime)", "a joke he swears you've heard"],
    "route_demeanor": {
        "Pacifist": "sunny in his lazy way — nice town, nice kid, no complaints",
        "Violent": "still smiling, but the smile does that thing where it doesn't move",
        "undetermined": "sizing you up like a pun he hasn't decided to tell yet",
    },
}


def _hometown(entry: dict[str, Any]) -> dict[str, Any]:
    """Overlay a returning character's Hometown persona (same soul, another world)."""
    merged = {**entry, **(entry.get("deltarune") or {})}
    merged.pop("deltarune", None)
    return merged


def get_character(name: Optional[str], game: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Look up a character's FREE bucket by name; None if not registered.

    game=None → the raw entry, any game (back-compat existence checks).
    game="deltarune" → Darkners as-is; returning faces (entries with a `deltarune`
    block) get their Hometown persona overlaid; None for everyone else.
    game="undertale" → Undertale entries only (no Darkners).
    """
    entry = CHARACTERS.get(normalize_key(name))
    if entry is None or game is None:
        return entry
    native = entry.get("game", "undertale")
    if game == "deltarune":
        if native == "deltarune":
            return entry
        return _hometown(entry) if entry.get("deltarune") else None
    return entry if native == game else None


def list_characters(game: Optional[str] = None) -> list[dict[str, Any]]:
    """The roster for a game. None → Undertale (back-compat). "deltarune" → the Ch1
    Darkners first, then the returning Hometown faces with personas applied."""
    if game == "deltarune":
        out = [{"key": k, **v} for k, v in CHARACTERS.items() if v.get("game") == "deltarune"]
        out += [{"key": k, **_hometown(v)} for k, v in CHARACTERS.items()
                if v.get("game", "undertale") == "undertale" and v.get("deltarune")]
        return out
    return [{"key": k, **v} for k, v in CHARACTERS.items()
            if v.get("game", "undertale") == "undertale"]


def is_known_character(name: Optional[str]) -> bool:
    return normalize_key(name) in CHARACTERS
