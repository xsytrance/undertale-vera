"""RAG lore layer: retrieval works (keyword backend), and stays behind the wall."""
import os

from fastapi.testclient import TestClient

import rag_engine
import undertale_vera_app as appmod
from prompt_builder import build_system_prompt

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


# ── retrieval (keyword backend — deterministic, no heavy deps) ───────────────

def test_collections_load():
    docs = rag_engine.load_documents()
    ids = {d["id"] for d in docs}
    assert "char-sans" in ids and "loc-waterfall" in ids and "evt-love" in ids
    # expanded collections: items + supporting-cast NPCs
    assert "item-butterscotch-pie" in ids and "npc-temmie" in ids
    assert len(docs) >= 30


def test_keyword_retrieve_finds_relevant_lore():
    hits = rag_engine.keyword_retrieve("tell me about waterfall and the echo flowers")
    titles = [h["title"] for h in hits]
    assert "Waterfall" in titles


def test_character_boost():
    hits = rag_engine.keyword_retrieve("what do you know?", character="Sans", k=3)
    assert hits[0]["character"] == "Sans"  # the character's own lore is boosted first


def test_retrieve_works_on_whatever_backend_is_available():
    # Backend is "vector" when an index + deps exist, else "keyword". Either way
    # retrieval must return relevant lore — the test stays environment-agnostic.
    assert rag_engine.backend_in_use() in ("keyword", "vector")
    assert rag_engine.retrieve("the barrier and human souls")


# ── the wall: lore is FREE world-knowledge, never a save-fact ────────────────

def test_lore_grounding_is_labeled_and_walled():
    block = rag_engine.format_lore_grounding(rag_engine.keyword_retrieve("LOVE and EXP"))
    assert "WORLD KNOWLEDGE" in block
    assert "NOT this player's save" in block
    assert "never establish or contradict" in block.lower()


def test_empty_lore_preserves_baseline():
    assert rag_engine.format_lore_grounding([]) == ""
    truth = {"play_state": {"name": "Frisk", "love": 1},
             "route": {"route": "Pacifist", "confidence": "medium", "reasons": []},
             "kills": {"total": 0}}
    base = build_system_prompt("sans", truth, lore_grounding="")
    assert "WORLD KNOWLEDGE" not in base   # no lore section when empty


# ── app: chat injects lore; lore never overrides the sacred route ────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        r = client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())})
    return r.json()["project_id"]


def test_chat_injects_lore_grounding(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        appmod, "generate_reply",
        lambda sp, um, **k: (captured.__setitem__("sp", sp), {"text": "hi", "model": "m"})[1],
    )
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    client.post(f"/api/projects/{pid}/chat", json={"character": "sans", "message": "tell me about waterfall"})
    sp = captured["sp"]
    assert "WORLD KNOWLEDGE" in sp          # lore injected
    assert "Pacifist" in sp                  # sacred route still present
    # The sacred SaveTruth block precedes the world-knowledge block.
    assert sp.index("SAVE FILE") < sp.index("WORLD KNOWLEDGE")


def test_lore_endpoint_is_auditable():
    r = client.get("/api/lore", params={"q": "undyne royal guard", "character": "undyne"}).json()
    assert r["backend"] in ("keyword", "vector")
    assert any(d["title"] == "Undyne" for d in r["results"])


# ── route gating (#1): world-knowledge visibility by route, NOT a save-fact ──

def test_doc_allowed_route_gating():
    paci_only = {"routes": ["Pacifist"], "spoiler": True}
    universal = {"routes": None, "spoiler": False}
    assert rag_engine.doc_allowed(paci_only, "Pacifist") is True
    assert rag_engine.doc_allowed(paci_only, "Genocide") is False
    assert rag_engine.doc_allowed(paci_only, "undetermined") is False  # don't presume
    assert rag_engine.doc_allowed(paci_only, None) is False
    assert rag_engine.doc_allowed(universal, None) is True             # universal always


def test_true_lab_lore_is_pacifist_gated():
    q = "the hidden true lab and the amalgamates"
    on_paci = [d["id"] for d in rag_engine.keyword_retrieve(q, route="Pacifist")]
    on_geno = [d["id"] for d in rag_engine.keyword_retrieve(q, route="Genocide")]
    on_unknown = [d["id"] for d in rag_engine.keyword_retrieve(q, route=None)]
    assert "evt-true-lab" in on_paci          # visible on its route
    assert "evt-true-lab" not in on_geno      # gated out on the wrong route
    assert "evt-true-lab" not in on_unknown   # hidden while route is unknown


def test_genocide_lore_is_genocide_gated():
    q = "the empty dusty path and final resolve"
    assert "evt-genocide-resolve" in [d["id"] for d in rag_engine.keyword_retrieve(q, route="Genocide")]
    assert "evt-genocide-resolve" not in [d["id"] for d in rag_engine.keyword_retrieve(q, route="Pacifist")]
