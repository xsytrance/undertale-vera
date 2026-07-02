"""Spark mode — the model-less voice: intent, grounding, honesty, variety."""
import pytest

import hallucination_guard
import spark
from character_config import list_characters


UT_TRUTH = {
    "game": "undertale",
    "play_state": {"name": "Frisk", "love": 5, "gold": 312, "room_name": "Snowdin Town"},
    "kills": {"total": 12},
    "route": {"route": "Neutral", "confidence": "high"},
}

DR_TRUTH = {
    "game": "deltarune",
    "play_state": {"name": "TESTER", "love": None, "gold": 3000, "room_name": None},
    "kills": {"total": None},
    "route": {"route": "undetermined", "confidence": None},
    "deltarune": {"party": ["Kris", "Susie", "Ralsei"], "dark_dollars": 3000, "jevil_defeated": True},
}

EMPTY_TRUTH = {"play_state": {}, "kills": {}, "route": {}}


def test_intent_ladder():
    cases = {
        "hey there": "greeting", "what's my name?": "name", "what route am i on": "route",
        "how many kills do i have": "kills", "what's my LOVE": "love",
        "how much gold do I have": "gold", "who's with me in the party": "party",
        "where am I right now": "where", "i'm stuck, help": "hint",
        "who are you anyway": "who_are_you", "thanks!": "thanks", "gotta go, bye": "bye",
        "tell me a joke": "joke", "how are you doing": "feel", "purple monkey dishwasher": "default",
    }
    for msg, want in cases.items():
        assert spark._intent(msg) == want, msg


def test_facts_are_sacred_and_verbatim():
    # sans lowercases his voice — but never the fact itself
    r = spark.spark_reply("sans", "what route am i on?", UT_TRUTH)
    assert "Neutral" in r
    r = spark.spark_reply("sans", "what's my name?", UT_TRUTH)
    assert "Frisk" in r
    r = spark.spark_reply("papyrus", "how many kills?", UT_TRUTH)
    assert "12 kills" in r
    r = spark.spark_reply("toriel", "how much gold do i have?", UT_TRUTH)
    assert "312" in r
    r = spark.spark_reply("undyne", "where am i?", UT_TRUTH)
    assert "Snowdin Town" in r


def test_deltarune_honesty():
    # Deltarune records no LOVE — Spark says so instead of inventing one
    r = spark.spark_reply("susie", "what's my LOVE?", DR_TRUTH)
    assert "LOVE" in r and "doesn't record" in r
    r = spark.spark_reply("ralsei", "who's in my party?", DR_TRUTH)
    assert "Kris" in r and "Susie" in r and "Ralsei" in r
    r = spark.spark_reply("jevil", "how much money do i have?", DR_TRUTH)
    assert "3000" in r and "Dark Dollars" in r
    r = spark.spark_reply("king", "what route am i on?", DR_TRUTH)
    assert "undetermined" in r


def test_unknowns_stay_unknown():
    r = spark.spark_reply("alphys", "what's my name?", EMPTY_TRUTH)
    assert "name" in r.lower()
    assert "Frisk" not in r          # nothing invented
    r = spark.spark_reply("napstablook", "how many kills?", EMPTY_TRUTH)
    assert "kill" in r.lower()


def test_every_character_speaks_every_intent_clean():
    """No crashes, no empty lines, no wall violations — the whole roster."""
    names = [c["name"] for c in list_characters()] + [c["name"] for c in list_characters("deltarune")]
    msgs = ["hi!", "what route am i on?", "what's my LOVE?", "i'm stuck, help",
            "who are you?", "thanks", "bye", "tell me a joke", "so anyway"]
    for name in set(names):
        truth = DR_TRUTH if name in ("Susie", "Ralsei", "Lancer", "Noelle", "King",
                                     "Rouxls Kaard", "Jevil", "Seam") else UT_TRUTH
        for msg in msgs:
            r = spark.spark_reply(name, msg, truth)
            assert isinstance(r, str) and len(r) > 10, (name, msg)
            guard = hallucination_guard.check_response(r, truth)
            assert guard["clean"], (name, msg, guard["issues"])


def test_deterministic_but_varied():
    a = spark.spark_reply("sans", "hello", UT_TRUTH, history=[])
    b = spark.spark_reply("sans", "hello", UT_TRUTH, history=[])
    assert a == b                                     # reproducible
    outs = {spark.spark_reply("sans", "hello", UT_TRUTH, history=[{}] * n) for n in range(6)}
    assert len(outs) >= 2                             # turn count moves the needle


def test_voice_styles_hold():
    assert spark.spark_reply("papyrus", "hello!", UT_TRUTH).isupper()
    s = spark.spark_reply("sans", "hello!", UT_TRUTH)
    assert s == s.lower()
    assert "…" in spark.spark_reply("napstablook", "hello!", UT_TRUTH)


def test_unknown_character_gets_default_voice():
    r = spark.spark_reply("some-modded-character", "what route am i on?", UT_TRUTH)
    assert "Neutral" in r
