"""Cross-source corroboration — file0 vs undertale.ini, the wall at parse time.

The corpus-corroborated file0 indices (kills@11, fun@35, room@547) are decoded,
and where a field appears in BOTH sources the two reads are checked against each
other: agreement is the strongest evidence (→ confirmed), disagreement exposes a
likely edited save (→ warning + low confidence), and we never silently pick.
"""
from save_parser import parse_undertale_save


def _file0(name="Frisk", love=1, max_hp=20, kills=0, fun=42, room=12):
    """Build a file0 long enough to reach the documented indices (1/2/11/35/547)."""
    lines = [""] * 548
    lines[0] = name
    lines[1] = str(love)
    lines[2] = str(max_hp)
    lines[11] = str(kills)
    lines[35] = str(fun)
    lines[547] = str(room)
    return "\n".join(lines)


def _ini(love=1, kills=0, fun=42, room=12):
    return (
        "[General]\n"
        f'Name="Frisk"\n'
        f'Love="{love}"\n'
        f'Kills="{kills}"\n'
        f'Fun="{fun}"\n'
        f'Room="{room}"\n'
    )


def test_new_indices_decode():
    s = parse_undertale_save(file0_text=_file0(kills=7, fun=55, room=101), ini_text=_ini(kills=7, fun=55, room=101))
    assert s.kills == 7
    assert s.fun == 55
    assert s.room == 101


def test_agreement_promotes_to_confirmed():
    s = parse_undertale_save(file0_text=_file0(love=14, kills=14, fun=13, room=145),
                             ini_text=_ini(love=14, kills=14, fun=13, room=145))
    assert s.warnings == []
    for fld in ("love", "kills", "fun", "room"):
        assert s.corroboration[fld]["agree"] is True
        assert s.confidence[fld] == "confirmed"


def test_disagreement_flags_edited_save():
    # file0 says 0 kills, the ini says 50 — internally inconsistent (edited save).
    s = parse_undertale_save(file0_text=_file0(kills=0), ini_text=_ini(kills=50))
    assert s.corroboration["kills"]["agree"] is False
    assert s.corroboration["kills"] == {"file0": 0, "ini": 50, "agree": False}
    assert s.confidence["kills"] == "low"
    assert any("kills disagrees across sources" in w for w in s.warnings)
    # The save-slot (file0) value is kept, never the ini and never an average.
    assert s.kills == 0


def test_no_corroboration_without_both_sources():
    # file0 only — nothing to cross-check, so no corroboration entries, no promotion.
    s = parse_undertale_save(file0_text=_file0(kills=5))
    assert s.corroboration == {}
    assert s.confidence["kills"] == "high"  # base corpus confidence, un-promoted


def test_implausible_new_field_is_nulled_not_guessed():
    s = parse_undertale_save(file0_text=_file0(fun=9999), ini_text=_ini(fun=9999))
    # Fun is documented 1–100; 9999 is out of range → None, and so uncorroborated.
    assert s.fun is None
    assert "fun" not in s.corroboration
