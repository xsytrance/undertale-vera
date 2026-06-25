"""Route-aware CONSCIENCE: demeanor shifts by route, FREE bucket, wall intact."""
from prompt_builder import build_demeanor_block, build_system_prompt


def _truth(route):
    return {
        "play_state": {"name": "Frisk", "love": 1},
        "route": {"route": route, "confidence": "medium", "reasons": []},
        "kills": {"total": 0},
    }


def test_demeanor_shifts_by_route():
    geno = build_system_prompt("sans", _truth("Genocide"))
    paci = build_system_prompt("sans", _truth("Pacifist"))
    assert "DEMEANOR" in geno and "DEMEANOR" in paci
    # The demeanor text genuinely differs between routes.
    assert "cold and clipped" in geno
    assert "almost relieved" in paci
    assert geno != paci


def test_undetermined_route_demeanor_is_honest():
    block = build_demeanor_block(
        {"route_demeanor": {"undetermined": "reserving judgment"}},
        _truth("undetermined"),
    )
    assert "undetermined" in block
    assert "reserving judgment" in block


def test_demeanor_is_tone_only_not_a_new_fact():
    block = build_demeanor_block(
        {"route_demeanor": {"Genocide": "cold and clipped"}},
        _truth("Genocide"),
    )
    # The block frames itself as tone shaped by the save — never a standalone fact.
    assert "tone only" in block
    assert "never state it as a new fact" in block


def test_no_route_demeanor_yields_empty_block_preserving_baseline():
    # A character without route_demeanor adds no demeanor section.
    assert build_demeanor_block({"name": "X"}, _truth("Genocide")) == ""
    assert build_demeanor_block({"route_demeanor": {}}, _truth("Genocide")) == ""
    # And an unknown route key also yields empty (no over-claim).
    assert build_demeanor_block({"route_demeanor": {"Pacifist": "x"}}, _truth("Neutral")) == ""
