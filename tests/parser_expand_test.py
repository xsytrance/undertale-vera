"""Parser-expansion engine — promote a file0 index only when the corpus proves it.

`correlate` must point each documented [General] field at the file0 index that
mirrors it, mark a 100%-agreement-over-enough-saves mapping as a confident
PROMOTE, and refuse anything noisier (no guessing). This is the methodology that
justified promoting kills@11 / fun@35 / room@547 against the real 64-save corpus.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import parser_expand  # noqa: E402


def _obs(lines, **ini):
    return {"name": "s", "lines": [float(x) if x is not None else None for x in lines],
            "ini": {f: float(v) for f, v in ini.items()}}


def test_num_is_tolerant():
    assert parser_expand._num('69.000000') == 69.0
    assert parser_expand._num('  13 ') == 13.0
    assert parser_expand._num('"7"') == 7.0
    assert parser_expand._num("ruins") is None
    assert parser_expand._num(None) is None


def test_correlate_promotes_a_corroborated_index():
    # 12 saves; file0[3] always == ini love, file0[5] always == ini kills.
    obs = []
    for i in range(12):
        love = 1 + i
        kills = i * 2
        lines = [0, 0, 0, love, 99, kills, 7]
        obs.append(_obs(lines, love=love, kills=kills))
    rep = parser_expand.correlate(obs, min_saves=10)
    assert rep["proposals"]["love"]["index"] == 3
    assert rep["proposals"]["love"]["confident"] is True
    assert rep["proposals"]["kills"]["index"] == 5
    assert rep["proposals"]["kills"]["ratio"] == 1.0
    assert rep["proposals"]["kills"]["confident"] is True


def test_noisy_index_is_not_promoted():
    # love matches file0[1] in only 6 of 12 saves → reported but NOT confident.
    obs = []
    for i in range(12):
        love = 5
        f0_love = 5 if i < 6 else 99  # half disagree
        obs.append(_obs([0, f0_love], love=love))
    rep = parser_expand.correlate(obs, min_saves=10)
    p = rep["proposals"]["love"]
    assert p["ratio"] < 1.0
    assert p["confident"] is False


def test_below_min_saves_is_not_confident():
    # Only 4 comparable saves, all agree — 100% but under the min_saves bar.
    obs = [_obs([0, 3 + i], love=3 + i) for i in range(4)]
    rep = parser_expand.correlate(obs, min_saves=10)
    p = rep["proposals"]["love"]
    assert p["ratio"] == 1.0
    assert p["confident"] is False  # not enough evidence to promote


def test_build_observations_reads_a_fixture_layout(tmp_path):
    # FIXTURE layout: file0_<name> + undertale_<name>.ini in one dir.
    lines = [""] * 12
    lines[0], lines[1], lines[11] = "Frisk", "1", "0"
    (tmp_path / "file0_x").write_text("\n".join(lines))
    (tmp_path / "undertale_x.ini").write_text('[General]\nLove="1"\nKills="0"\n')
    from corpus_audit import discover_saves
    obs = parser_expand.build_observations(discover_saves(str(tmp_path)))
    assert len(obs) == 1
    assert obs[0]["ini"]["love"] == 1.0
    assert obs[0]["lines"][1] == 1.0
