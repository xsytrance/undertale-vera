"""Flag-mining engine — surface route-discriminative ini flags from a corpus.

`mine` must tag a flag as discriminative for a route only when it's set in enough
of that route's saves and ~absent in the others — the evidence that justified the
KILL_FLAGS allow-list (TK/PK set in Genocide, 0/49 Pacifist).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import flag_mine  # noqa: E402


def _rows(spec):
    # spec: list of (label, set_of_flags)
    return [{"label": l, "flags": set(f)} for l, f in spec]


def test_is_set():
    assert flag_mine._is_set("1.000000") is True
    assert flag_mine._is_set('"2"') is True
    assert flag_mine._is_set("0.000000") is False
    assert flag_mine._is_set("ruins") is True   # non-numeric text counts as present


def test_clean_kill_flag_is_discriminative_for_genocide():
    rows = _rows(
        [("Genocide", [("toriel", "tk"), ("papyrus", "pk")])] * 8 +
        [("Pacifist", [("toriel", "ts")])] * 20
    )
    rep = flag_mine.mine(rows, min_present=0.5, max_other=0.0)
    tk = next(f for f in rep["flags"] if (f["section"], f["key"]) == ("toriel", "tk"))
    assert tk["discriminative_for"] == "Genocide"
    ts = next(f for f in rep["flags"] if (f["section"], f["key"]) == ("toriel", "ts"))
    assert ts["discriminative_for"] == "Pacifist"


def test_flag_present_in_both_is_not_discriminative():
    rows = _rows(
        [("Genocide", [("flowey", "met1")])] * 8 +
        [("Pacifist", [("flowey", "met1")])] * 8    # met happens on both routes
    )
    rep = flag_mine.mine(rows, min_present=0.5, max_other=0.0)
    met = next(f for f in rep["flags"] if f["key"] == "met1")
    assert met["discriminative_for"] is None


def test_max_other_threshold_tolerates_small_leakage():
    # 1 of 20 Pacifist saves has the flag (5%). With max_other=0 it's NOT clean;
    # with max_other=0.1 it passes.
    rows = _rows(
        [("Genocide", [("papyrus", "pk")])] * 10 +
        [("Pacifist", [("papyrus", "pk")])] * 1 +
        [("Pacifist", [])] * 19
    )
    strict = flag_mine.mine(rows, min_present=0.5, max_other=0.0)
    loose = flag_mine.mine(rows, min_present=0.5, max_other=0.1)
    pk_strict = next(f for f in strict["flags"] if f["key"] == "pk")
    pk_loose = next(f for f in loose["flags"] if f["key"] == "pk")
    assert pk_strict["discriminative_for"] is None
    assert pk_loose["discriminative_for"] == "Genocide"


def test_build_rows_reads_flags_from_fixtures(tmp_path):
    (tmp_path / "file0_x").write_text("Frisk\n20\n99\n")
    (tmp_path / "undertale_x.ini").write_text(
        '[General]\nLove="20"\nKills="50"\n[Toriel]\nTK="1.000000"\nTS="0.000000"\n')
    from corpus_audit import discover_saves
    rows = flag_mine.build_rows(discover_saves(str(tmp_path)))
    assert len(rows) == 1
    assert ("toriel", "tk") in rows[0]["flags"]      # set
    assert ("toriel", "ts") not in rows[0]["flags"]  # zero → not set
    assert ("general", "kills") not in rows[0]["flags"]  # bookkeeping key skipped
