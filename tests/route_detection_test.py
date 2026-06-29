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


# ── contradiction guard (verified against a real save-editor corpus) ─────────
class _Stub:
    """Minimal stand-in for ParsedUndertaleSave (no copyrighted save data)."""
    def __init__(self, love, kills):
        self.love = love
        self._k = kills

    def ini_get(self, section, key):
        if (section, key) == ("general", "kills"):
            return None if self._k is None else str(self._k)
        return None


def test_maxed_love_with_zero_kills_is_undetermined_not_genocide():
    # Real edited saves (e.g. a "True Pacifist" file) carry LOVE 20 + Kills 0 —
    # internally contradictory. Honest answer: undetermined, never a guess.
    r = detect_route(_Stub(20, 0))
    assert r["route"] == "undetermined"
    assert any("contradict" in x for x in r["reasons"])


def test_love_one_with_recorded_kills_is_undetermined():
    r = detect_route(_Stub(1, 5))
    assert r["route"] == "undetermined"


def test_maxed_love_without_kill_signal_still_genocide():
    # No contradicting kill count present → LOVE 20 reads as Genocide.
    assert detect_route(_Stub(20, None))["route"] == "Genocide"
    assert detect_route(_Stub(20, 9))["route"] == "Genocide"


# ── documented boss-kill flags (community + corpus confirmed: TK/PK) ──────────
class _FlagStub:
    """Stand-in carrying undertale.ini kill flags ([Toriel] TK, [Papyrus] PK)."""
    def __init__(self, love, kills=None, tk=False, pk=False, flags=None):
        self.love = love
        self._k = kills
        self._flags = dict(flags or {})
        if tk:
            self._flags[("toriel", "tk")] = "1.000000"
        if pk:
            self._flags[("papyrus", "pk")] = "1.000000"

    def ini_get(self, section, key):
        if (section, key) == ("general", "kills"):
            return None if self._k is None else str(self._k)
        return self._flags.get((section, key))


def test_kill_flag_extracted_only_when_set():
    from route_detection import extract_kill_flags
    assert extract_kill_flags(_FlagStub(13, tk=True, pk=True)) and \
        {f["character"] for f in extract_kill_flags(_FlagStub(13, tk=True, pk=True))} == {"Toriel", "Papyrus"}
    assert extract_kill_flags(_FlagStub(1)) == []


def test_maxed_love_plus_kill_flags_is_genocide_confirmed():
    # Two independent records of total slaughter → the one "confirmed" case.
    r = detect_route(_FlagStub(20, kills=113, tk=True, pk=True))
    assert r["route"] == "Genocide"
    assert r["confidence"] == "confirmed"
    assert any("boss-kill flags" in x.lower() for x in r["reasons"])


def test_kill_flag_with_love_one_is_contradiction():
    # A boss-kill flag set but LOVE 1 (no EXP) cannot both hold → undetermined.
    r = detect_route(_FlagStub(1, tk=True))
    assert r["route"] == "undetermined"
    assert any("cannot both hold" in x for x in r["reasons"])


def test_kill_flag_keeps_midrun_at_neutral_not_overclaimed():
    # Killed Toriel + Papyrus but LOVE only 12 → killing is certain, but this is
    # NOT the full clearance Genocide demands. Honest answer: Neutral.
    r = detect_route(_FlagStub(12, kills=64, tk=True, pk=True))
    assert r["route"] == "Neutral"
    assert any("kill flag" in x.lower() for x in r["reasons"])


def test_kill_flag_signal_appears_in_signals():
    r = detect_route(_FlagStub(15, kills=103, tk=True, pk=True))
    assert any("Toriel killed" in s for s in r["signals"])
    assert any("Papyrus killed" in s for s in r["signals"])


# ── befriend/date flags (True Pacifist requirements) + spare/kill contradiction ──
def _flags(**kv):
    # kv like pd=True, ud=True → {('papyrus','pd'): '1', ...}
    keymap = {"pd": ("papyrus", "pd"), "ud": ("undyne", "ud"), "ad": ("alphys", "ad"),
              "ts": ("toriel", "ts"), "ps": ("papyrus", "ps")}
    return {keymap[k]: "1.000000" for k, v in kv.items() if v}


def test_befriend_flags_extracted():
    from route_detection import extract_befriend_flags
    chars = {f["character"] for f in extract_befriend_flags(_FlagStub(1, flags=_flags(pd=True, ud=True)))}
    assert chars == {"Papyrus", "Undyne"}


def test_pacifist_with_befriend_flags_is_high():
    # No-kill run PLUS date flags (only reachable on a no-kill path) → high, not medium.
    r = detect_route(_FlagStub(1, kills=0, flags=_flags(pd=True, ud=True, ad=True)))
    assert r["route"] == "Pacifist"
    assert r["confidence"] == "high"
    assert any("befriend/date flags" in x.lower() for x in r["reasons"])


def test_pacifist_without_befriend_flags_stays_medium():
    # Early no-kill save: indistinguishable from a no-kill Neutral → honest medium.
    r = detect_route(_FlagStub(1, kills=0))
    assert r["route"] == "Pacifist"
    assert r["confidence"] == "medium"


def test_spare_and_kill_same_character_is_contradiction():
    # Toriel marked BOTH spared and killed → impossible → undetermined.
    r = detect_route(_FlagStub(20, kills=50, flags=_flags(ts=True), tk=True))
    assert r["route"] == "undetermined"
    assert any("mutually exclusive" in x for x in r["reasons"])
    assert any("Toriel" in x for x in r["reasons"])
