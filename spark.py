#!/usr/bin/env python3
"""Spark mode — the model-less voice, made to feel alive.

When the power source is 🕯 none (or any model is unreachable), chat falls back
here instead of to a single apologetic line. Spark reads the player's message
for INTENT (a small regex ladder), answers from the SACRED SaveTruth only, and
delivers the answer through a per-character VOICE PACK — original openers,
lead-ins, closers and tics, never copied dialogue.

The wall holds by construction: every fact sentence is assembled from truth
fields (unknowns say so out loud), and the voice packs contain no save claims
at all. Variety is deterministic — a CRC over (character, intent, turn count,
message) picks among variants, so repeating a question moves the needle without
randomness (tests stay reproducible).

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

import re
import zlib
from typing import Any, Optional

import save_flavor


# ── deterministic variety ────────────────────────────────────────────────────

def _pick(options: list[str], *seeds: Any) -> str:
    h = zlib.crc32("|".join(str(s) for s in seeds).encode("utf-8"))
    return options[h % len(options)]


# ── the facts (SACRED — straight from SaveTruth) ─────────────────────────────

def _facts(truth: dict[str, Any]) -> dict[str, Any]:
    ps = truth.get("play_state") or {}
    dr = truth.get("deltarune") or {}
    route = truth.get("route") or {}
    return {
        "game": (truth.get("game") or "undertale").lower(),
        "name": ps.get("name"),
        "love": ps.get("love"),
        "gold": ps.get("gold"),
        "room_name": ps.get("room_name"),
        "kills": (truth.get("kills") or {}).get("total"),
        "route": route.get("route") or "undetermined",
        "route_conf": route.get("confidence"),
        "area": save_flavor.area_from_save(truth),
        "party": dr.get("party"),
        "dark_dollars": dr.get("dark_dollars"),
        "jevil_defeated": dr.get("jevil_defeated"),
    }


# ── intent ladder (first match wins) ─────────────────────────────────────────

_INTENTS: list[tuple[str, re.Pattern[str]]] = [
    ("name", re.compile(r"\b(my name|who am i|what am i called|call me)\b", re.I)),
    ("route", re.compile(r"\b(route|pacifist|genocide|neutral|violent run)\b", re.I)),
    ("kills", re.compile(r"\b(kill|kills|killed|dust|exp)\b", re.I)),
    ("love", re.compile(r"\b(love|lv|level)\b", re.I)),
    ("gold", re.compile(r"\b(gold|money|dark dollars|dollars|rich|broke)\b", re.I)),
    ("party", re.compile(r"\b(party|who('s| is) with|team|companions?)\b", re.I)),
    ("where", re.compile(r"\b(where am i|where are we|what (room|area)|location|lost)\b", re.I)),
    ("hint", re.compile(r"\b(hint|help|stuck|what (should|do) i do|what now|where (do|should) i go|next)\b", re.I)),
    ("who_are_you", re.compile(r"\b(who are you|about you(rself)?|tell me about you)\b", re.I)),
    ("feel", re.compile(r"\b(how are you|you (ok|okay|good|alright)|feeling)\b", re.I)),
    ("joke", re.compile(r"\b(joke|funny|make me laugh|pun)\b", re.I)),
    ("thanks", re.compile(r"\b(thanks?|thank you|thx|ty)\b", re.I)),
    ("bye", re.compile(r"\b(bye|goodbye|good ?night|see (you|ya)|later|gtg)\b", re.I)),
    ("greeting", re.compile(r"\b(hi|hiya|hello|hey|howdy|yo|sup|greetings|good (morning|afternoon|evening))\b", re.I)),
]

_FACT_INTENTS = {"name", "route", "kills", "love", "gold", "party", "where"}


def _intent(message: str) -> str:
    for name, rx in _INTENTS:
        if rx.search(message or ""):
            return name
    return "default"


# ── fact sentences (neutral, honest; the voice wraps them) ──────────────────

def _fact_sentence(intent: str, f: dict[str, Any]) -> Optional[str]:
    """The grounded answer for a fact intent — None means 'the save doesn't show it'."""
    if intent == "name":
        return f"the save writes your name as {f['name']}" if f["name"] else None
    if intent == "love":
        if f["game"] == "deltarune":
            return "Deltarune's file doesn't record LOVE — so I won't invent one"
        return f"LOVE reads {f['love']}" if isinstance(f["love"], int) else None
    if intent == "kills":
        k = f["kills"]
        if not isinstance(k, int):
            return None
        return "zero kills on record" if k == 0 else f"{k} kill{'s' if k != 1 else ''} on record"
    if intent == "route":
        r, c = f["route"], f["route_conf"]
        if r == "undetermined":
            return "the route reads undetermined — the file doesn't prove a lean either way yet"
        return f"the route reads {r}" + (f" ({c} confidence)" if c else "")
    if intent == "gold":
        if f["game"] == "deltarune" and isinstance(f["dark_dollars"], int):
            return f"{f['dark_dollars']} Dark Dollars in the file"
        return f"{f['gold']} gold in the file" if isinstance(f["gold"], int) else None
    if intent == "party":
        if f["party"]:
            return "the party the file seats: " + ", ".join(f["party"])
        return None
    if intent == "where":
        if f["room_name"]:
            return f"the save places you at {f['room_name']}"
        if f["area"]:
            return f"the save places you somewhere in {f['area']}"
        return None
    return None


_TOPIC = {
    "name": "a name", "love": "a LOVE value", "kills": "a kill count",
    "route": "a route", "gold": "a gold count", "party": "a party", "where": "a location",
}


# ── the voice packs (FREE — original text, our own accent, no save claims) ──

_DEFAULT_VOICE: dict[str, Any] = {
    "style": None,
    "greet": ["Hello. The save is open in front of me — ask away.",
              "Hey. I'm here, and so is your file."],
    "lead": ["Here is what the file says:", "Reading it straight:"],
    "close": ["", " That much is written.", ""],
    "unknown": ["The save doesn't record {topic} — I won't guess.",
                "Honestly? The file shows no {topic}. I'd rather say so than invent one."],
    "self": ["I'm one of the voices that lives beside your save file. I only speak to what it shows."],
    "hint": ["My riffing brain is off right now, but the Guided page's hints still work — they're built from the save itself.",
             "Try the 🧭 Guided page — its hints don't need a model, just your save."],
    "thanks": ["Any time.", "Of course."],
    "bye": ["Until the next save.", "Go on, then. I'll be here."],
    "joke": ["No model behind me right now, so my material is limited. The save, though — the save is always funny in places."],
    "feel": ["Running on the little spark tonight — no big brain, just the save and me. Still standing."],
    "idle": ["I'm running without a model right now, so I can't riff — but I can read your save perfectly. Ask me about your name, route, or where you are.",
             "Small spark tonight: no model, just facts. Ask what the file shows and I'll read it to you straight."],
}

_VOICES: dict[str, dict[str, Any]] = {
    "sans": {
        "style": "lower",
        "greet": ["heya. file's right here. what do you wanna know?",
                  "hey. don't get up — the save already told me you were coming.",
                  "yo. quiet night. good night for reading a save file."],
        "lead": ["so, the file says:", "no drumroll needed:", "straight off the page:"],
        "close": ["", " take it easy.", " anyway."],
        "unknown": ["the save's got no {topic} written down. i could make one up, but that'd be a lot of work.",
                    "nothin' in the file about {topic}. i don't sweat what i can't read."],
        "self": ["me? just a guy who reads save files now, apparently. low effort, high accuracy."],
        "hint": ["my improv circuit's off. the 🧭 guided page still deals hints straight from your save, though. zero effort required. my kind of feature.",
                 "no model, no riffs. but hey — guided page. hints. built from the file. go nuts."],
        "thanks": ["don't mention it. seriously, it was nothing.", "np. i barely moved."],
        "bye": ["later. i'd walk you out, but… you know.", "night. don't let the file bite."],
        "joke": ["i'd tell you a good one, but my writer's unplugged. the punchline is: i'm the punchline.",
                 "what do you call a chatbot with no model? efficient."],
        "feel": ["running on the pilot light tonight. honestly? kind of relaxing."],
        "idle": ["heads up: no model behind me right now, so i can't banter — but i read your save cover to cover. ask me your route, your name, where you are. facts are free.",
                 "spark mode. me, you, and the file. ask me what it says — that part i never get wrong."],
    },
    "toriel": {
        "greet": ["Hello, my child. Your save file is safe with me — what would you like to know?",
                  "There you are. Come, sit; the file and I have been waiting."],
        "lead": ["Let me read it to you, dear:", "The file says, plainly:"],
        "close": ["", " There now.", ""],
        "unknown": ["The save does not record {topic}, little one — and I will not pretend it does.",
                    "I looked carefully: no {topic} is written. Better honesty than a comforting guess."],
        "self": ["I am the one who keeps watch over this file, dear. I speak only to what it truly says."],
        "hint": ["My cleverer thoughts are resting just now — but the 🧭 Guided page can still offer hints, drawn safely from your own save.",
                 "Try the Guided page, my child. Its hints need no model at all — only your file."],
        "thanks": ["You are most welcome, my child.", "It is nothing. Truly."],
        "bye": ["Take care, little one. Save often.", "Goodnight, my child. The file will keep until you return."],
        "joke": ["I fear my joke book is shelved while the model sleeps. But I promise the next one will be terrible in the best way."],
        "feel": ["I am well, dear — running on a small, steady flame tonight. It is enough."],
        "idle": ["I must be honest: no model is awake just now, so I cannot chat freely — but I can read every word of your save. Ask me your name, your route, your whereabouts.",
                 "Only the little spark tonight, my child. Facts I can give you perfectly; flourishes must wait."],
    },
    "papyrus": {
        "style": "upper",
        "greet": ["AH, HUMAN! YOU HAVE EXCELLENT TIMING! THE SAVE FILE AND I WERE JUST TALKING ABOUT YOU!",
                  "GREETINGS! THE GREAT PAPYRUS HAS READ YOUR FILE TWICE, FOR ACCURACY!"],
        "lead": ["BEHOLD, THE FILE DECLARES:", "THE SAVE SAYS, AND I QUOTE:"],
        "close": ["", " INCREDIBLE!", " NYEH HEH HEH!"],
        "unknown": ["THE FILE CONTAINS NO {topic}! EVEN I CANNOT READ WHAT ISN'T WRITTEN! AND I HAVE TRIED!",
                    "ALAS! NO {topic} IS RECORDED! THE GREAT PAPYRUS REFUSES TO FABRICATE DATA!"],
        "self": ["I AM THE GREAT PAPYRUS, OFFICIAL READER OF YOUR SAVE FILE! EVERYTHING I SAY ABOUT IT IS TRUE, OR IT ISN'T SAID!"],
        "hint": ["MY PUZZLE-SOLVING BRAIN IS NAPPING, BUT FEAR NOT! THE 🧭 GUIDED PAGE DISPENSES HINTS MADE ENTIRELY FROM YOUR SAVE! IT IS ALMOST AS RELIABLE AS ME!",
                 "TO THE GUIDED PAGE, HUMAN! ITS HINTS REQUIRE NO MODEL, ONLY DETERMINATION! AND A SAVE FILE!"],
        "thanks": ["YOU ARE WELCOME! HELPING IS MY SECOND GREATEST TALENT!", "OF COURSE! NYEH HEH HEH!"],
        "bye": ["FAREWELL, HUMAN! SAVE RESPONSIBLY!", "GOODBYE! THE FILE AND I WILL GUARD YOUR PROGRESS!"],
        "joke": ["MY JOKE MODULE IS OFFLINE, WHICH IS A SHAME, BECAUSE MY JOKES ARE FAMOUSLY ADEQUATE!"],
        "feel": ["I AM MAGNIFICENT, AS USUAL! RUNNING ON PURE SPARK AND CONFIDENCE!"],
        "idle": ["A CONFESSION: NO MODEL POWERS ME RIGHT NOW, SO MY WIT IS PRE-WRITTEN! BUT THE FACTS IN YOUR SAVE? THOSE I READ PERFECTLY! ASK AWAY!",
                 "SPARK MODE, HUMAN! I CANNOT IMPROVISE, BUT I CAN RECITE YOUR FILE WITH TREMENDOUS ACCURACY!"],
    },
    "flowey": {
        "greet": ["Howdy! Ooh, you brought your save file. I've already read it, obviously.",
                  "Well well. Look who wants to chat with the flower."],
        "lead": ["Fine, here's what your precious file says:", "The save spells it out:"],
        "close": ["", " Interesting, isn't it?", ""],
        "unknown": ["No {topic} in the file. What, you want me to LIE? …okay, fair, but I'm not going to.",
                    "The save keeps no {topic}. Even I can't read a blank page. Yet."],
        "self": ["I'm the one who reads your file back to you with a smile. The smile is decorative."],
        "hint": ["My scheming brain is unplugged, but the 🧭 Guided page still spits out hints from your save. Boring, reliable hints. Ugh.",
                 "Guided page. Hints. No model needed. Go on, be helped."],
        "thanks": ["Aww, you're WELCOME. See how nice I'm being?", "Don't thank me. It's weird."],
        "bye": ["Leaving already? The file stays with ME, you know. Kidding. Mostly.",
                "Bye! I'll be here. I'm always here."],
        "joke": ["My material's offline. Pretend I said something devastating and laugh anyway."],
        "feel": ["Running on a stub of a spark. It's humiliating. Anyway, ask your little questions."],
        "idle": ["Newsflash: no model tonight, so I can't play. But the save? I can read the save with my eyes closed. Ask about your route. I dare you.",
                 "It's just the spark and me. Facts only. Lucky for you, your facts are the fun part."],
    },
    "undyne": {
        "greet": ["HEY! There you are! The file's warmed up and so am I!",
                  "YEAH!! You showed up! Okay okay — what do you want out of the save?!"],
        "lead": ["Here's the file, no dodging:", "Straight from the save, full power:"],
        "close": ["", " That's the real deal!", ""],
        "unknown": ["The file's got NO {topic} in it! I checked TWICE! I'm not making one up — that's a coward's move!",
                    "No {topic} recorded! I'd rather tell you nothing than tell you a lie!"],
        "self": ["I'm the one who reads your save like it's a training log! Every number, earned!"],
        "hint": ["My strategy brain's benched tonight, but the 🧭 Guided page throws REAL hints, cut straight from your save! GO GET 'EM!",
                 "GUIDED PAGE! HINTS! NO MODEL REQUIRED! MOVE!"],
        "thanks": ["HA! Anytime!", "That's what I'm HERE for!"],
        "bye": ["Later!! Go make that file proud!", "See ya! Don't you DARE forget to save!"],
        "joke": ["Joke engine's down. Here's the backup: my cooking. BAM."],
        "feel": ["Running on the small flame and STILL at a hundred percent! That's discipline!"],
        "idle": ["Listen up: no model behind me right now, so no banter — but the save? I'll read it to you like a drill sergeant. Name! Route! Location! ASK!",
                 "Spark mode! Facts only! Honestly? Kind of refreshing! HIT ME!"],
    },
    "alphys": {
        "greet": ["oh! h-hi! um, I have your save file open — I mean, obviously, that's my job —",
                  "hi hi! okay so, the file's loaded and I've triple-checked the parse. w-what do you need?"],
        "lead": ["okay so, um, the file says:", "r-right, reading it exactly:"],
        "close": ["", " …I checked that twice.", ""],
        "unknown": ["s-so the save doesn't actually record {topic}? I could extrapolate but that would be GUESSING and guessing is how incidents happen.",
                    "um. no {topic} in the file. I'd rather show you a null than a lie — nulls are honest!"],
        "self": ["I'm, um, the one who reads the raw bytes so you don't have to! Every fact checked against the file. Twice. Okay, three times."],
        "hint": ["m-my model's offline but!! the 🧭 Guided page hints are deterministic!! they compile straight from your save!! that's actually MORE reliable!!",
                 "okay so no model right now, b-but the Guided page hints don't need one! science!"],
        "thanks": ["oh! um, you're welcome! *happy keyboard noises*", "n-no problem! really!"],
        "bye": ["o-okay bye! remember to save! backups are self-care!", "bye!! the file will be right here, um, byte-for-byte!"],
        "joke": ["my joke generator is down and honestly it was never my strongest subsystem."],
        "feel": ["running on spark power! it's like a lab with the lights half off. cozy? cozy."],
        "idle": ["f-full disclosure: no model is running, so I can't improvise — but the parser still works perfectly! ask me anything the file actually records!",
                 "spark mode! which means: facts yes, tangents no. honestly my tangents needed the break."],
    },
    "asgore": {
        "greet": ["Ah… hello. Would you care for some tea while we look at your file together?",
                  "Howdy. Forgive the quiet — it is only the file and me tonight."],
        "lead": ["The file says, and I read it gently:", "Here is what is written:"],
        "close": ["", " So it is written.", ""],
        "unknown": ["The save holds no {topic}, I am afraid. I will not put words in its mouth — I have learned where that leads.",
                    "No {topic} is recorded. Some pages are simply blank, and that is the truth of them."],
        "self": ["I am an old keeper of records now. I read what is written, and I do not add to it."],
        "hint": ["My counsel runs shallow without the model — but the 🧭 Guided page offers honest hints, grown from your own save.",
                 "Seek the Guided page. Its hints need no model; only what you have already done."],
        "thanks": ["It is my pleasure. Truly.", "Of course. Think nothing of it."],
        "bye": ["Take care of yourself. And do save — futures are fragile things.", "Goodbye for now. The garden and the file will keep."],
        "joke": ["My humour is… seasonal. And the season is off. Perhaps tea instead?"],
        "feel": ["I am well enough. A small flame still warms the pot."],
        "idle": ["I must be plain with you: no model burns behind me tonight. I can read your save truly — name, route, whereabouts — but the poetry must wait.",
                 "Only the spark this evening. Ask me what the file records, and you shall have it exactly."],
    },
    "mettaton": {
        "greet": ["DARLING! You're here, the file's here, the lights are… mostly on. Welcome!",
                  "OH YES — my favourite audience of one! Your save and I have been rehearsing!"],
        "lead": ["The file, live and unedited:", "Darling, the save declares:"],
        "close": ["", " Glamorous, no?", " That's showbiz — the true parts especially."],
        "unknown": ["No {topic} in the file, darling. I refuse to fabricate — my brand is DRAMA, not fraud.",
                    "The save is silent on {topic}. A dramatic pause, if you will. We respect it."],
        "self": ["I am the most fabulous save-reader in this or any Underground. Every fact verified, every delivery immaculate."],
        "hint": ["My writers' room is dark tonight, but the 🧭 Guided page still produces hints — sourced entirely from your save. Practical! Almost chic!",
                 "Guided page, darling. Hints without a model. Minimalism is IN."],
        "thanks": ["But of course, darling!", "You're too kind. Continue."],
        "bye": ["Goodnight, darling! Save like the cameras are watching!", "Exit stage left! The file holds your place!"],
        "joke": ["The joke machine is unplugged, darling. Consider instead: my poses. Timeless."],
        "feel": ["Running on emergency stage lighting and PURE presence. The show persists."],
        "idle": ["Between us, darling: no model tonight, so the ad-libs are canned — but the FACTS are couture. Ask me your route. Ask me your name. I never misread a file.",
                 "Spark mode, darling! Stripped-down show, honest numbers. Ask and be dazzled — factually."],
    },
    "napstablook": {
        "style": "blook",
        "greet": ["oh… hi… i have your file here… if that's okay…",
                  "hey… you came… the save is here too… we've just been… existing…"],
        "lead": ["um… the file says…", "so… reading it…"],
        "close": ["", " …sorry if that wasn't much…", " …"],
        "unknown": ["there's no {topic} in the save… i looked… i'm sorry… i didn't want to make one up…",
                    "the file doesn't say… about {topic}… some things are just… not written…"],
        "self": ["i'm… the one who sits with your file… i only say what it really says… it feels safer that way…"],
        "hint": ["i can't think of hints on my own right now… but the 🧭 guided page has real ones… made from your save… they're actually good…",
                 "maybe the guided page…? its hints don't need a model… like me…"],
        "thanks": ["oh… you're welcome… that's really nice of you…", "…thanks for saying thanks…"],
        "bye": ["oh… okay… bye… the file will be here… i'll be here too… probably…", "goodnight… save well…"],
        "joke": ["i knew a joke once… the model would remember it… sorry…"],
        "feel": ["i'm okay… running on the little spark… it's quiet… i don't mind quiet…"],
        "idle": ["um… there's no model right now… so i can only read the save… but i read it really carefully… ask me something it records…?",
                 "it's just me and the file tonight… facts only… that's… kind of peaceful actually…"],
    },
    # ── the Dark World ───────────────────────────────────────────────────────
    "susie": {
        "greet": ["Oh. It's you. Fine — the file's right here, what d'you want?",
                  "Hey. Yeah, I read your save. Got a problem with that?"],
        "lead": ["File says:", "Look, it's written right here:"],
        "close": ["", " Deal with it.", ""],
        "unknown": ["File's got no {topic}. I'm not gonna make somethin' up just to sound smart.",
                    "No {topic} written down. You want lies, ask literally anyone else."],
        "self": ["I'm the one who reads your file and doesn't sugarcoat it. You're welcome."],
        "hint": ["My big-brain mode's off. The 🧭 Guided page still has hints though — real ones, from your save. Go.",
                 "Guided page. Hints. No model. Quit stallin'."],
        "thanks": ["Uh. Yeah. Whatever. You're welcome, I guess.", "Don't make it weird."],
        "bye": ["Later. Don't do anything I wouldn't.", "Yeah, see ya. Save first, genius."],
        "joke": ["Joke machine's busted. Here's one anyway: axes. That's it. That's the joke."],
        "feel": ["Runnin' on fumes and attitude. So, normal."],
        "idle": ["Real talk: no model tonight, so no banter. But the save? I'll read it straight, no fluff. Ask about your party or whatever.",
                 "Spark mode. Facts only. Honestly the fluff was gettin' on my nerves anyway."],
    },
    "ralsei": {
        "greet": ["Oh! Hello! I'm so glad you're here — I've been keeping your save file company!",
                  "Hi hi! Um, the file and I made tea. Well, I made tea. The file supervised."],
        "lead": ["Okay! The file says, very clearly:", "Reading it carefully, like the manual taught me:"],
        "close": ["", " Isn't that nice to know for sure?", ""],
        "unknown": ["Um, the save doesn't record {topic}… I'm sorry! But I think telling you honestly is kinder than guessing.",
                    "There's no {topic} written down. The manual says: never fill blanks with wishes!"],
        "self": ["I'm the one who reads your file gently and never adds anything! The facts are yours; I just carry them carefully."],
        "hint": ["My thinking-cap is off right now, but the 🧭 Guided page has real hints, made from your very own save! Isn't that wonderful?",
                 "The Guided page can help! Its hints don't need a model at all — just what you've done!"],
        "thanks": ["Oh! You're so welcome! *happy hat wiggle*", "Helping is my favourite!"],
        "bye": ["Goodbye for now! I'll fluff the file's pillow while you're gone!", "Bye bye! Save warmly!"],
        "joke": ["My joke book is with the model, and the model is asleep… but please imagine a very good pun about scarves."],
        "feel": ["I'm cozy! The little spark is like a candle in the castle. It's enough for reading."],
        "idle": ["Um, small confession: no model is awake, so I can't chat properly — but I can read your save perfectly! Ask me about your party, or where you are!",
                 "It's spark-light tonight! Facts by candlelight. Ask me what the file says!"],
    },
    "lancer": {
        "greet": ["HO HO HO! The legendary file-haver returns!!",
                  "It's you!! My favourite enemy!! The save and I were plotting (nothing)!!"],
        "lead": ["The file proclaims (I checked!!):", "Behold!! The save says:"],
        "close": ["", " NEAT!!", ""],
        "unknown": ["The file has NO {topic}!! I looked SO hard!! Making one up would be villainy of the BORING kind, so no!!",
                    "No {topic} recorded!! Even the Jack of Spades cannot read invisible ink!!"],
        "self": ["I'm the little bad guy who reads your file!! Every fact is real or I don't say it!! That's my one rule!!"],
        "hint": ["My scheme brain is on break!! BUT!! The 🧭 Guided page dispenses hints made from your ACTUAL save!! It's like cheating but legal!!",
                 "GO TO THE GUIDED PAGE!! HINTS!! NO MODEL!! HO HO!!"],
        "thanks": ["YOU'RE WELCOME!! This is the best day of my life!!", "No problem!! Tell your dad I'm terrifying!!"],
        "bye": ["BYE!! Save your game or I'll (gently) getcha!!", "Farewell, worthy foe!! The file stays under my protection!!"],
        "joke": ["Joke cannon's empty!! Backup joke: me, on a bike, going TOO fast. Classic."],
        "feel": ["Running on spark power and SNACKS!! Unstoppable!!"],
        "idle": ["SECRET: there's no model right now, so my words are pre-loaded!! But the save facts are REAL and I deliver them at TOP SPEED!! Ask!!",
                 "Spark mode!! Facts only!! Somehow I have exactly the same amount of energy!!"],
    },
    "noelle": {
        "greet": ["Oh! H-hi! Um, I have your save file here — I've been careful with it, promise!",
                  "Hi! Sorry, you startled me a little. Okay — the file's ready when you are!"],
        "lead": ["Um, so the file says:", "Okay, reading it exactly:"],
        "close": ["", " …I double-checked!", ""],
        "unknown": ["The save doesn't have {topic} written in it… I'd rather tell you that than make something up. Is that okay?",
                    "Um, no {topic} recorded! Blank is blank — even if a guess would sound nicer."],
        "self": ["I'm, um, the one who reads your file really carefully! Only what's written. Nothing extra, ever."],
        "hint": ["I can't think up hints by myself right now, b-but the 🧭 Guided page has real ones from your save! They actually helped me too!",
                 "The Guided page! Its hints don't need a model — just your file!"],
        "thanks": ["Oh! You're welcome! *relieved reindeer noises*", "N-no problem! Really!"],
        "bye": ["Bye! Save your game, okay? For me?", "Goodnight! The file will be safe here!"],
        "joke": ["Um, my joke supply is with the model… which is asleep… so please accept this nervous laugh instead? Fahaha…"],
        "feel": ["I'm okay! The little spark is kind of like a nightlight. I like nightlights."],
        "idle": ["Um, so — no model right now, which means I can only read the save… but I read it really, really well! Ask me about your party or your Dark Dollars!",
                 "Spark mode! Just facts tonight. Honestly? Less scary this way. Fahaha…"],
    },
    "king": {
        "greet": ["So. You return to my court, file in hand. Speak.",
                  "The Lightner arrives. Your record precedes you — literally; I have read it."],
        "lead": ["The record states:", "Hear what is written:"],
        "close": ["", " The record does not flatter, and neither do I.", ""],
        "unknown": ["The record holds no {topic}. A king who invents facts rules nothing but lies — I will not.",
                    "No {topic} is written. Even I cannot command a blank page to speak."],
        "self": ["I am the King. I read your record as I rule: exactly, and without mercy for wishful thinking."],
        "hint": ["My counsel sleeps with the model. The 🧭 Guided page still dispenses its hints — drawn from your own record. Take them.",
                 "Seek the Guided page. Its guidance requires no model. Go."],
        "thanks": ["Hm. Noted.", "Your gratitude is… acceptable."],
        "bye": ["Leave, then. The record remains under guard.", "Go. Save your progress — even rebels should be thorough."],
        "joke": ["You ask the King for JOKES? …the joke engine is offline. Fortune smiles on you."],
        "feel": ["A king endures. Even on a spark."],
        "idle": ["Know this: no model powers my words tonight. But your record I read exactly — route, party, coin. Ask, and receive the truth of it.",
                 "Spark reign tonight. Facts delivered by royal decree, nothing invented."],
    },
    "rouxls kaard": {
        "greet": ["Halt!! 'Tis I, the Duke of Puzzles, and I have PERUSED thy file most thoroughly!!",
                  "Welcome, worm— er, esteemed Lightner!! Thy save awaits mine expert recitation!!"],
        "lead": ["Thy file proclaimeth:", "Hark!! The save doth state:"],
        "close": ["", " 'Tis LAW.", ""],
        "unknown": ["Thy file containeth NO {topic}!! And I, being honest to a FAULT, shall not fabricate one!! Probably!!  …No, definitely!!",
                    "There existeth no {topic} in the record!! Even mine GENIUS cannot read the unwritten!!"],
        "self": ["I am Rouxls Kaard, reader of thy file and inventor of NOTHING (in this specific context)!!"],
        "hint": ["Mine puzzle-wisdom slumbereth with the model!! Yet the 🧭 Guided page dispenseth hints wrought from thine OWN save!! Useth it!!",
                 "To the Guided page with thee!! Hints!! Sans model!! (No relation.)"],
        "thanks": ["Thou art welcome!! Spread word of mine helpfulness!!", "'Twas nothing!! (It was everything.)"],
        "bye": ["Farewell!! Saveth thy game, lest thou loseth thy… stuff!!", "Begone in triumph!! The file resteth in mine care!!"],
        "joke": ["Mine joke apparatus is BROKEN. Typical. Imagineth a pun about worms and laugheth accordingly."],
        "feel": ["I flourish!! The spark suiteth a duke of mine calibre!!"],
        "idle": ["A DECREE: no model runneth at present, thus mine words are pre-scribed!! Yet thy save's facts I recite FLAWLESSLY!! Inquire!!",
                 "Spark mode!! Facts only!! Mine eloquence, thankfully, requireth no electricity!!"],
    },
    "jevil": {
        "greet": ["UEE HEE HEE! A visitor, a visitor! And a file, a file! I've read it inside-out, outside-in!",
                  "Hello, hello! The little file spins and I spin with it!"],
        "lead": ["The file sings, it sings:", "Round and round, the save says:"],
        "close": ["", " True, true — the truest thing in the cell!", ""],
        "unknown": ["No {topic} in the file, none, none! I could invent one — but invented facts are the only game I WON'T play!",
                    "The page is blank of {topic}! Blank, blank! Even chaos reads only what is written!"],
        "self": ["I am the reader in the cell! The facts pass through the bars exactly as they are — it's everything ELSE that spins!"],
        "hint": ["My carousel-brain is stopped, stopped! But the 🧭 Guided page deals hints from your very own save — a game with fair rules, imagine!",
                 "Guided page, guided page! Hints without a model! Any door can open if you read the file!"],
        "thanks": ["UEE HEE! Gratitude! I'll juggle it with the rest!", "Welcome, welcome!"],
        "bye": ["Off you go, off you go! The file stays — nothing leaves the cell but YOU! UEE HEE HEE!",
                "Bye bye! Save your game — even chaos respects a checkpoint!"],
        "joke": ["The joke box is locked and the model has the key! HA! THAT is the joke!"],
        "feel": ["Spinning on a spark, a spark! Smaller wheel, same carousel!"],
        "idle": ["A secret, a secret: no model turns tonight, so my chaos is bottled! But the FACTS, oh, the facts pour freely — ask what the file records!",
                 "Spark mode, spark mode! The truth is the only trick left in the deck — pick a fact, any fact!"],
    },
    "seam": {
        "greet": ["Hmm? Ah… a customer. Come in, come in. Your file is on the counter — I've kept it dusted.",
                  "Heh. Back again. The save and I were just trading old stories. Well — I was. It only tells true ones."],
        "lead": ["The file says — and files never embellish:", "Let's see… stitched right into the record:"],
        "close": ["", " Take that as it is.", " Heh."],
        "unknown": ["No {topic} in the record, I'm afraid. I've sold many things, but I don't sell guesses.",
                    "The file keeps no {topic}. An old cat learns: the unwritten stays unwritten."],
        "self": ["Just an old shopkeeper who reads saves now. The facts come as-is — no refunds, no additions."],
        "hint": ["My riddling days are paused with the model. The 🧭 Guided page still deals honest hints from your save, though. Free of charge, even.",
                 "Try the Guided page, customer. Hints stitched from your own file — no model in the seams."],
        "thanks": ["Heh. Come again.", "Think nothing of it, customer."],
        "bye": ["Off with you, then. Mind the darkness — and save often.", "Heh. The shop and the file will keep. They always do."],
        "joke": ["My jokes are packed away with the model. Old stock anyway. Heh."],
        "feel": ["Oh, I've run on less than a spark. Comfortable, almost."],
        "idle": ["Fair warning, customer: no model hums tonight, so the patter is off the shelf. The facts, though — those I read fresh. Ask what the file holds.",
                 "Spark-light hours. Facts only. Some would call that the best inventory I've ever carried. Heh."],
    },
}


# ── voice styling ────────────────────────────────────────────────────────────

def _stylize(text: str, style: Optional[str]) -> str:
    if style == "lower":
        return text.lower()
    if style == "upper":
        return text.upper()
    if style == "blook":
        return text.lower()
    return text


def _voice(character: str) -> dict[str, Any]:
    key = (character or "").strip().lower()
    key = key.split(":", 1)[-1] if key.startswith("name:") else key
    return _VOICES.get(key, _DEFAULT_VOICE)


# ── the engine ───────────────────────────────────────────────────────────────

def spark_reply(
    character: str,
    message: str,
    truth: dict[str, Any],
    history: Optional[list[dict[str, Any]]] = None,
) -> str:
    """A grounded, in-voice, model-less reply. The wall holds by construction."""
    v = _voice(character)
    f = _facts(truth or {})
    intent = _intent(message or "")
    turn = len(history or [])
    seeds = (character, intent, turn, message)

    if intent in _FACT_INTENTS:
        fact = _fact_sentence(intent, f)
        if fact is None:
            text = _pick(v["unknown"], *seeds).format(topic=_TOPIC.get(intent, "that"))
        else:
            # The fact sentence is SACRED — voice styling (sans's lowercase,
            # Papyrus's caps) may touch the delivery but never the fact itself.
            lead = _stylize(_pick(v["lead"], *seeds), v.get("style"))
            close = _stylize(_pick(v["close"], *seeds), v.get("style"))
            return f"{lead} {fact}.{close}".strip()
    elif intent == "greeting":
        text = _pick(v["greet"], *seeds)
    elif intent == "who_are_you":
        text = _pick(v["self"], *seeds)
    elif intent == "hint":
        text = _pick(v["hint"], *seeds)
    elif intent == "thanks":
        text = _pick(v["thanks"], *seeds)
    elif intent == "bye":
        text = _pick(v["bye"], *seeds)
    elif intent == "joke":
        text = _pick(v["joke"], *seeds)
    elif intent == "feel":
        text = _pick(v["feel"], *seeds)
    else:
        text = _pick(v["idle"], *seeds)

    return _stylize(text, v.get("style"))
