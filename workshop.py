#!/usr/bin/env python3
"""The Prompt Workshop — the prompts this app runs on, shown live.

Nothing here is documentation-by-copy: the anatomy example is assembled by the
REAL prompt builder against a demo SaveTruth, and every feature instruction is
imported from (or, for the few inline ones, kept verbatim with a source pointer
and covered by a drift test) the module that actually uses it. If the prompts
change, this page changes with them.

PURE module (no DB/network/LLM).
"""
from __future__ import annotations

from typing import Any

import divergence
import journal
import proactive
import reports as reports_mod
import session_story
from prompt_builder import build_system_prompt

# A small, honest demo truth — clearly labelled, never a real player's save.
DEMO_TRUTH: dict[str, Any] = {
    "schema_version": "undertale-savetruth-v1",
    "play_state": {"name": "DEMO", "love": 5, "gold": 312, "room_name": "Snowdin Town"},
    "kills": {"total": 12},
    "route": {
        "route": "Neutral",
        "confidence": "high",
        "reasons": ["LOVE is 5 with 12 kills recorded — EXP was gained but the save shows no genocide-tier signals."],
    },
    "parser_confidence": {"name": "confirmed", "love": "confirmed", "kills": "high", "route": "high"},
    "warnings": [],
}

# Verbatim copies of the instructions that live inline in undertale_vera_app.py.
# tests/workshop_test.py greps the app source to keep these from drifting.
JUDGMENT_INSTRUCTION = (
    "Deliver your judgment of this player now. Read back what the save shows — "
    "their route, their LOVE, their kills — in your own voice. State only what "
    "is in the save; name the unknowns honestly; invent nothing."
)
GUIDED_REACT_INSTRUCTION = (
    "The human is playing RIGHT NOW, with you riding along. The block above "
    "records exactly what changed between their last two saves. In one or two "
    "sentences, in your own voice, react to what just changed — and nothing "
    "beyond it."
)


def anatomy() -> list[dict[str, str]]:
    """The system prompt's section order, labelled by bucket."""
    return [
        {"n": "1", "bucket": "FREE", "label": "Identity",
         "what": "One line: you are this character; speak first-person, never as an AI assistant."},
        {"n": "2", "bucket": "SACRED", "label": "The SaveTruth block",
         "what": "The parsed facts, stated verbatim inside a hard-fenced block — name, LOVE, kills, "
                 "route with its confidence and reasons. Anchored high so it governs everything after."},
        {"n": "2a-2d", "bucket": "SACRED", "label": "Dispositions · relations · remembrance · texture",
         "what": "Who was spared or dusted, the fate of those THIS speaker loves, parser-confirmed "
                 "history across visits, and small recorded details (area, play time, the pie)."},
        {"n": "3", "bucket": "FREE", "label": "Voice & personality",
         "what": "Tone, quirks, what they talk about, how this route colours their demeanor — the "
                 "character's accent on the facts, never a source of facts."},
        {"n": "4", "bucket": "FREE", "label": "Living Memory",
         "what": "Out-of-game recollections of past chats, clearly labelled as such — warmth, not truth."},
        {"n": "5", "bucket": "WALL", "label": "The rules",
         "what": "The closing laws: save facts win, unknowns stay unknown, never invent name/LOVE/route/"
                 "kills. Then a hallucination guard re-checks the actual reply after generation."},
    ]


def instructions() -> list[dict[str, str]]:
    """The per-feature ask, pulled live from the modules that use them."""
    return [
        {"feature": "Chat", "icon": "💬", "source": "prompt_builder.build_system_prompt",
         "text": "(no extra instruction — the player's own message rides beneath the system prompt above)"},
        {"feature": "Keepsake Journal", "icon": "📖", "source": "journal.inscription_instruction",
         "text": journal.inscription_instruction(DEMO_TRUTH)},
        {"feature": "Report Cards", "icon": "📋", "source": "reports.report_instruction",
         "text": reports_mod.report_instruction(DEMO_TRUTH)},
        {"feature": "Reach-outs", "icon": "🕊", "source": "proactive.reach_out_instruction",
         "text": proactive.reach_out_instruction(DEMO_TRUTH)},
        {"feature": "Judgment", "icon": "⚖", "source": "undertale_vera_app.py (verbatim)",
         "text": JUDGMENT_INSTRUCTION},
        {"feature": "Two-Save Divergence", "icon": "🔀", "source": "divergence.instruction",
         "text": divergence.instruction()},
        {"feature": "Session Stories", "icon": "📜", "source": "session_story.instruction",
         "text": session_story.instruction(3)},
        {"feature": "Guided reactions", "icon": "🧭", "source": "undertale_vera_app.py (verbatim)",
         "text": GUIDED_REACT_INSTRUCTION},
    ]


def workshop_state() -> dict[str, Any]:
    """Everything the Workshop page renders that must stay live-true."""
    return {
        "example_prompt": build_system_prompt("sans", DEMO_TRUTH),
        "example_note": "Assembled by the real prompt builder against a labelled DEMO save "
                        "(Neutral, LOVE 5, 12 kills) — exactly what sans would be handed.",
        "anatomy": anatomy(),
        "instructions": instructions(),
    }
