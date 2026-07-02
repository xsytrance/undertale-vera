"""Per-character disposition — SACRED who-was-killed/spared/befriended grounding."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from character_disposition import (
    derive_dispositions, known_dispositions, build_disposition_grounding,
    grounding_from_truth,
)

client = TestClient(appmod.app)


class _Stub:
    """Stand-in carrying undertale.ini character flags."""
    def __init__(self, flags):
        # flags: {(section, key): "value"}
        self._flags = dict(flags)

    def ini_get(self, section, key):
        return self._flags.get((section, key))


# ── pure derivation ──────────────────────────────────────────────────────────

def test_killed_spared_befriended_unknown():
    s = _Stub({
        ("toriel", "tk"): "1.000000",     # Toriel killed
        ("papyrus", "ps"): "1.000000",    # Papyrus spared
        ("undyne", "ud"): "1.000000",     # Undyne befriended
        # Alphys: no flag → unknown
    })
    d = derive_dispositions(s)
    assert d["Toriel"]["status"] == "killed"
    assert d["Papyrus"]["status"] == "spared"
    assert d["Undyne"]["status"] == "befriended"
    assert d["Alphys"]["status"] == "unknown"


def test_befriended_outranks_spared():
    # Papyrus dated (befriended) implies spared; befriended is the stronger truth.
    s = _Stub({("papyrus", "ps"): "1", ("papyrus", "pd"): "1"})
    assert derive_dispositions(s)["Papyrus"]["status"] == "befriended"


def test_killed_and_spared_is_contradicted_not_asserted():
    s = _Stub({("toriel", "tk"): "1", ("toriel", "ts"): "1"})
    d = derive_dispositions(s)
    assert d["Toriel"]["status"] == "contradicted"
    # contradicted is excluded from the definite outcomes
    assert "Toriel" not in known_dispositions(s)


def test_zero_value_flag_is_not_set():
    assert derive_dispositions(_Stub({("toriel", "tk"): "0.000000"}))["Toriel"]["status"] == "unknown"


# ── grounding text ───────────────────────────────────────────────────────────

def test_grounding_empty_when_nothing_known():
    assert build_disposition_grounding(_Stub({})) == ""


def test_grounding_lists_known_outcomes():
    g = build_disposition_grounding(_Stub({("toriel", "tk"): "1", ("papyrus", "pd"): "1"}))
    assert "Toriel: killed" in g
    assert "Papyrus: befriended" in g
    assert "WHO YOU'VE MET" in g


def test_grounding_from_truth_reads_dispositions_block():
    truth = {"dispositions": {
        "Toriel": {"character": "Toriel", "status": "killed", "flags": ["tk"]},
        "Alphys": {"character": "Alphys", "status": "unknown", "flags": []},
    }}
    g = grounding_from_truth(truth)
    assert "Toriel: killed" in g
    assert "Alphys" not in g          # unknown is not asserted
    assert grounding_from_truth({}) == ""


# ── app wiring: chat prompt carries SACRED dispositions ──────────────────────

def _file0_with(love, lines_extra=None):
    lines = [""] * 548
    lines[0], lines[1], lines[2] = "Frisk", str(love), "20"
    for idx, val in (lines_extra or {}).items():
        lines[idx] = val
    return "\n".join(lines).encode()


def _upload(file0_bytes, ini_text):
    return client.post("/api/upload", files={
        "file0": ("file0", file0_bytes),
        "undertale_ini": ("undertale.ini", ini_text.encode()),
    }).json()["project_id"]


def test_chat_prompt_includes_disposition_block(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "...", "model": "m"})
    ini = ('[General]\nName="Frisk"\nLove="13"\nKills="69"\n'
           '[Toriel]\nTK="1.000000"\n[Papyrus]\nPK="1.000000"\n')
    pid = _upload(_file0_with(13, {11: "69"}), ini)
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "sans", "message": "what did I do?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "WHO YOU'VE MET" in sp
    assert "Toriel: killed" in sp
    assert "Papyrus: killed" in sp


def test_provenance_surfaces_definite_dispositions():
    from provenance import build_provenance
    truth = {"dispositions": {
        "Toriel": {"status": "killed"}, "Papyrus": {"status": "befriended"},
        "Alphys": {"status": "unknown"},
    }}
    p = build_provenance(truth, character="Sans")
    assert p["sacred"]["dispositions"] == {"Toriel": "killed", "Papyrus": "befriended"}


def test_chat_prompt_has_no_disposition_block_when_no_flags(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "...", "model": "m"})
    ini = '[General]\nName="Frisk"\nLove="1"\nKills="0"\n'
    pid = _upload(_file0_with(1), ini)
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "toriel", "message": "hi"}).json()
    assert "WHO YOU'VE MET" not in r["grounding"]["system_prompt"]
