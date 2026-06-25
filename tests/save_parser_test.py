"""Parser-truth tests: documented fields decoded, unknowns → null, no crashes."""
import os

from save_parser import parse_undertale_save

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _paths(stem, ini=None):
    f0 = os.path.join(FIX, stem)
    ini_path = os.path.join(FIX, ini) if ini else None
    return f0, ini_path


def test_pacifist_decodes_known_fields():
    f0, ini = _paths("file0_pacifist", "undertale_pacifist.ini")
    s = parse_undertale_save(f0, ini)
    assert s.name == "Frisk"
    assert s.love == 1
    assert s.max_hp == 20
    assert s.confidence["name"] == "confirmed"
    assert s.confidence["love"] == "confirmed"
    # INI parsed case-insensitively.
    assert s.ini_get("General", "Kills") == "0"
    assert s.ini_get("general", "roomname") == "ruins_entrance"
    assert s.warnings == []


def test_genocide_love_ceiling():
    f0, ini = _paths("file0_genocide", "undertale_genocide.ini")
    s = parse_undertale_save(f0, ini)
    assert s.love == 20


def test_unreadable_love_becomes_null_not_guessed():
    f0, _ = _paths("file0_ambiguous")
    s = parse_undertale_save(f0)
    assert s.name == "Frisk"
    assert s.love is None                      # never guessed
    assert s.confidence["love"] == "unknown"
    assert any("LOVE" in w for w in s.warnings)  # reported, not crashed


def test_no_inputs_stops_and_reports():
    s = parse_undertale_save()  # nothing provided
    assert s.love is None
    assert any("STOP+REPORT" in w for w in s.warnings)


def test_raw_lines_preserved_for_audit():
    f0, _ = _paths("file0_pacifist")
    s = parse_undertale_save(f0)
    assert len(s.file0_lines) >= 3
    assert s.file0_lines[0] == "Frisk"
