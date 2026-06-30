"""The Constellation of You — the whole shape of a player across ALL their saves.
SACRED tallies (real recorded routes/LOVE/kills) under a FREE Sans verdict."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from constellation import aggregate, build_verdict, build_divergence, _routes_phrase

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ── pure ─────────────────────────────────────────────────────────────────────

def test_aggregate_counts_routes_and_extremes():
    saves = [
        {"route": "Pacifist", "love": 1},
        {"route": "Genocide", "love": 20, "total_kills": 9},
        {"route": "Pacifist", "love": 3},
    ]
    agg = aggregate(saves)
    assert agg["count"] == 3
    assert agg["routes"] == {"Pacifist": 2, "Genocide": 1}
    assert agg["darkest"]["route"] == "Genocide"
    assert agg["kindest"]["route"] == "Pacifist"
    assert agg["peak_love"] == 20
    assert agg["full_spectrum"] is True


def test_aggregate_empty_and_unread_routes():
    assert aggregate([])["count"] == 0
    # a save whose route was never read isn't counted into any route, nor an extreme
    agg = aggregate([{"route": None, "love": None}])
    assert agg["routes"] == {} and agg["darkest"] is None and agg["kindest"] is None
    assert agg["full_spectrum"] is False


def test_routes_phrase_orders_kind_first():
    assert _routes_phrase({"Genocide": 1, "Pacifist": 2}) == "2 Pacifist and 1 Genocide"
    assert _routes_phrase({"Pacifist": 1, "Neutral": 1, "Genocide": 1}) == "1 Pacifist, 1 Neutral and 1 Genocide"
    assert _routes_phrase({}) == "no run I could read"


def test_verdict_full_spectrum_is_the_hardest_line():
    v = build_verdict(aggregate([
        {"route": "Pacifist", "love": 1},
        {"route": "Genocide", "love": 20, "total_kills": 9},
    ]))
    assert "kindest" in v and "cruelest" in v and "same hands did both" in v


def test_verdict_all_pacifist_and_empty():
    assert build_verdict(aggregate([])) == ""
    v = build_verdict(aggregate([{"route": "Pacifist"}, {"route": "Pacifist"}]))
    assert "walked it kind" in v and "2 Pacifist" in v


def test_divergence_names_the_fork():
    d = build_divergence(
        {"name": "Frisk", "route": "Pacifist", "love": 1},
        {"name": "Chara", "route": "Genocide", "love": 20, "total_kills": 9},
    )
    assert "Pacifist — Frisk, LOVE 1" in d
    assert "Genocide — Chara, LOVE 20, 9 of them dead" in d
    assert "same hands" in d


def test_divergence_empty_when_no_fork():
    # same route → no divergence
    assert build_divergence({"route": "Pacifist"}, {"route": "Pacifist"}) == ""
    # missing side → no divergence
    assert build_divergence(None, {"route": "Genocide"}) == ""
    # honest: an unread name/LOVE is simply not spoken
    d = build_divergence({"route": "Pacifist", "name": None}, {"route": "Genocide", "name": None})
    assert "no name I could read" in d and "LOVE" not in d


# ── endpoint wiring ──────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_constellation_endpoint_sees_the_full_spectrum():
    _upload("file0_pacifist", "undertale_pacifist.ini")
    _upload("file0_genocide", "undertale_genocide.ini")
    con = client.get("/api/constellation").json()
    assert con["count"] >= 2
    assert con["aggregate"]["full_spectrum"] is True
    assert "same hands did both" in con["verdict"]
    # SACRED: the route tally reflects real saves
    assert con["aggregate"]["routes"].get("Genocide", 0) >= 1
    # the Divergence names the fork between the kindest and cruelest runs
    assert "same hands" in con["divergence"]
    assert "Pacifist" in con["divergence"] and "Genocide" in con["divergence"]
