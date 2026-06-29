"""The corpus-audit tool — discovery + the coverage report (fixture layout)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import corpus_audit  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def test_discovers_flat_fixtures():
    saves = corpus_audit.discover_saves(FIX)
    names = {s["name"] for s in saves}
    assert {"pacifist", "genocide", "neutral", "ambiguous"} <= names
    # the ambiguous fixture has no paired ini
    amb = next(s for s in saves if s["name"] == "ambiguous")
    assert amb["ini"] is None


def test_audit_report_shape_and_routes():
    rep = corpus_audit.audit(corpus_audit.discover_saves(FIX))
    assert rep["total"] >= 4
    assert rep["parsed_clean"] == rep["total"]      # nothing crashes
    # The synthetic fixtures are deliberately short (~12 lines vs a real save's
    # ~549), so the "file0 looks short" heuristic flags them — that's the heuristic
    # working, not a parse failure. Real saves (549 lines) produce no such flag.
    totals = rep["route_totals"]
    assert totals.get("Pacifist", 0) >= 1
    assert totals.get("Genocide", 0) >= 1
    assert totals.get("undetermined", 0) >= 1       # the ambiguous fixture
    assert rep["love_min"] == 1 and rep["love_max"] == 20


def test_format_report_is_text():
    rep = corpus_audit.audit(corpus_audit.discover_saves(FIX))
    text = corpus_audit.format_report(rep)
    assert "Saves found:" in text and "Route totals:" in text
