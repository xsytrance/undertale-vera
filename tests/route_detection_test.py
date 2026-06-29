"""Route detection: derived from real flags; ambiguous → undetermined, never guessed."""
import os

from route_detection import detect_route
from save_parser import parse_undertale_save

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _route(stem, ini=None):
    f0 = os.path.join(FIX, stem)
    ini_path = os.path.join(FIX, ini) if ini else None
    return detect_route(parse_undertale_save(f0, ini_path))


def test_pacifist_consistent_is_medium_not_overclaimed():
    r = _route("file0_pacifist", "undertale_pacifist.ini")
    assert r["route"] == "Pacifist"
    assert r["confidence"] == "medium"           # not "high" — befriend flags unknown
    assert any("LOVE=1" in s for s in r["signals"])


def test_genocide_at_love_ceiling():
    r = _route("file0_genocide", "undertale_genocide.ini")
    assert r["route"] == "Genocide"
    assert r["confidence"] == "high"


def test_neutral_when_some_killing():
    r = _route("file0_neutral", "undertale_neutral.ini")
    assert r["route"] == "Neutral"


def test_undetermined_when_no_signals():
    r = _route("file0_ambiguous")  # LOVE unreadable, no ini
    assert r["route"] == "undetermined"
    assert r["confidence"] == "unknown"


def test_reasons_are_present_for_audit():
    r = _route("file0_genocide", "undertale_genocide.ini")
    assert r["reasons"] and all(isinstance(x, str) for x in r["reasons"])
