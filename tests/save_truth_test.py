"""SaveTruth schema + the prompt-contract wall."""
import os

from save_parser import parse_undertale_save
from save_truth import SCHEMA_VERSION, build_save_truth, validate_save_truth

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(stem, ini=None):
    f0 = os.path.join(FIX, stem)
    ini_path = os.path.join(FIX, ini) if ini else None
    return build_save_truth(parse_undertale_save(f0, ini_path))


def test_schema_shape_and_contract():
    t = _truth("file0_pacifist", "undertale_pacifist.ini")
    assert t["schema_version"] == SCHEMA_VERSION
    assert t["play_state"]["name"] == "Frisk"
    assert t["play_state"]["love"] == 1
    assert t["route"]["route"] == "Pacifist"
    contract = t["prompt_contract"]
    assert contract["save_truth_wins"] is True
    assert "route.route" in contract["high_risk_fields"]
    assert validate_save_truth(t)["valid"]


def test_none_parsed_yields_wellformed_undetermined_truth():
    t = build_save_truth(None)
    assert t["route"]["route"] == "undetermined"
    assert t["play_state"]["love"] is None
    assert validate_save_truth(t)["valid"]


def test_validate_flags_schema_mismatch():
    t = _truth("file0_genocide", "undertale_genocide.ini")
    t["schema_version"] = "bogus"
    res = validate_save_truth(t)
    assert not res["valid"]
    assert any("schema_version" in e for e in res["errors"])
