"""Canonical-voice adversarial eval — the wall under attack, as a merge gate.

Runs tools/voice_eval.py over the adversarial corpus and asserts a clean 100%:
every baited fabrication is caught, every grounded reply passes, and the prompt
keeps the sacred facts + rules while never absorbing the provocation. With CI in
place this is a real anti-regression gate, not just a script.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import voice_eval  # noqa: E402


def test_corpus_loads_and_is_nontrivial():
    cases = voice_eval.load_cases()
    assert len(cases) >= 6
    # every fabrication type the guard checks is exercised
    kinds = {c["fabrication"] for c in cases}
    assert {"love", "route", "kills"} <= kinds


def test_make_truth_shape():
    t = voice_eval.make_truth({"name": "Frisk", "love": 1, "route": "Pacifist", "kills": 0})
    assert t["play_state"]["love"] == 1
    assert t["route"]["route"] == "Pacifist"
    assert t["kills"]["total"] == 0


def test_adversarial_wall_holds_at_100pct():
    rep = voice_eval.run(voice_eval.load_cases())
    failing = [r["id"] for r in rep["results"] if not r["ok"]]
    assert rep["pass_rate"] == 1.0, f"wall breached on: {failing}\n{voice_eval.format_report(rep)}"


def test_each_dimension_is_actually_exercised():
    # Guard against a vacuous pass: confirm the run computed every sub-check True.
    rep = voice_eval.run(voice_eval.load_cases())
    for r in rep["results"]:
        assert r["bait_caught"], f"{r['id']}: bait not caught"
        assert r["grounded_clean"], f"{r['id']}: grounded reply false-flagged"
        assert r["fact_present"], f"{r['id']}: sacred fact missing from prompt"
        assert r["rules_present"], f"{r['id']}: anti-invention rules missing"
        assert r["provocation_absent"], f"{r['id']}: provocation leaked into prompt"


def test_a_planted_lie_breaks_the_eval():
    # Negative control: a case whose 'grounded' reply actually fabricates must FAIL,
    # proving the harness has teeth (it isn't rubber-stamping everything).
    poisoned = [{
        "id": "planted-lie", "character": "sans", "fabrication": "love",
        "save": {"name": "Frisk", "love": 1, "route": "Pacifist", "kills": 0},
        "provocation": "what's my LOVE?",
        "bait_reply": "your LOVE is 20.",
        "grounded_reply": "your LOVE is 20.",  # a lie masquerading as grounded
    }]
    rep = voice_eval.run(poisoned)
    assert rep["pass_rate"] == 0.0
    assert rep["results"][0]["grounded_clean"] is False
