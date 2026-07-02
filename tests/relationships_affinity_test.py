"""The Underground reacts to you — expanded cast, relational awareness, affinity."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from character_config import get_character, list_characters
import relationships
import affinity as affinity_mod

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(route="Neutral", dispositions=None):
    return {
        "play_state": {"name": "Frisk", "love": 5},
        "route": {"route": route, "confidence": "medium"},
        "kills": {"total": 5},
        "dispositions": dispositions or {},
    }


def _disp(**kv):
    return {name: {"character": name, "status": status, "flags": []} for name, status in kv.items()}


# ── expanded cast (ADD-only) ─────────────────────────────────────────────────

def test_new_cast_registered():
    names = {c["name"] for c in list_characters()}
    assert {"Alphys", "Asgore", "Mettaton", "Napstablook"} <= names
    assert len(list_characters()) == 9


def test_every_character_has_cares_about_and_demeanor():
    for c in list_characters():
        assert "cares_about" in c and isinstance(c["cares_about"], list)
        assert set(c["route_demeanor"]) == {"Pacifist", "Neutral", "Genocide", "undetermined"}


# ── relational awareness ─────────────────────────────────────────────────────

def test_relevant_fates_follows_cares_about():
    # Sans cares about Papyrus.
    t = _truth(dispositions=_disp(Papyrus="killed", Toriel="spared"))
    fates = relationships.relevant_fates("Sans", t)
    assert fates == [{"who": "Papyrus", "status": "killed"}]


def test_relational_grounding_text():
    t = _truth(route="Genocide", dispositions=_disp(Papyrus="killed"))
    g = relationships.build_relational_grounding("Sans", t)
    assert "Papyrus" in g and "killed" in g
    assert "SANS CARES ABOUT" in g


def test_relational_grounding_empty_when_no_loved_one_recorded():
    assert relationships.build_relational_grounding("Sans", _truth()) == ""
    # Flowey cares about no one → always empty.
    assert relationships.build_relational_grounding(
        "Flowey", _truth(dispositions=_disp(Papyrus="killed"))) == ""


# ── affinity ─────────────────────────────────────────────────────────────────

def test_affinity_by_route():
    assert affinity_mod.character_affinity("Toriel", _truth(route="Pacifist"))["stance"] == "warm"
    assert affinity_mod.character_affinity("Toriel", _truth(route="Neutral"))["stance"] == "wary"
    assert affinity_mod.character_affinity("Toriel", _truth(route="Genocide"))["stance"] == "hostile"
    assert affinity_mod.character_affinity("Toriel", _truth(route="undetermined"))["stance"] == "unreadable"


def test_affinity_escalates_when_a_loved_one_was_killed():
    # Sans cares about Papyrus. Papyrus killed on a Neutral run → grief, not mere wary.
    a = affinity_mod.character_affinity("Sans", _truth(route="Neutral", dispositions=_disp(Papyrus="killed")))
    assert a["stance"] == "grieving"
    assert "Papyrus" in a["basis"]
    # On Genocide it hardens to hostile.
    a2 = affinity_mod.character_affinity("Sans", _truth(route="Genocide", dispositions=_disp(Papyrus="killed")))
    assert a2["stance"] == "hostile"


def test_affinity_self_killed():
    # Toriel herself killed → she regards you with grief (or hostility on Genocide).
    a = affinity_mod.character_affinity("Toriel", _truth(route="Neutral", dispositions=_disp(Toriel="killed")))
    assert a["stance"] == "grieving"


def test_all_affinities_covers_cast():
    a = affinity_mod.all_affinities(_truth(route="Pacifist"))
    assert len(a) == 9 and a["Sans"]["stance"] == "warm"


# ── app wiring ───────────────────────────────────────────────────────────────

def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


def test_affinities_endpoint():
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.get(f"/api/projects/{pid}/affinities").json()
    assert r["project_id"] == pid
    assert r["affinities"]["Sans"]["stance"] == "warm"      # pacifist save
    assert client.get("/api/projects/999999/affinities").status_code == 404


def test_chat_includes_relational_grounding(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "...", "model": "m"})
    # a save where Papyrus is killed
    ini = ('[General]\nName="Frisk"\nLove="13"\nKills="69"\n[Toriel]\nTK="1"\n[Papyrus]\nPK="1"\n')
    lines = [""] * 548
    lines[0], lines[1], lines[2], lines[11] = "Frisk", "13", "68", "69"
    pid = client.post("/api/upload", files={
        "file0": ("file0", "\n".join(lines).encode()),
        "undertale_ini": ("undertale.ini", ini.encode()),
    }).json()["project_id"]
    r = client.post(f"/api/projects/{pid}/chat",
                    json={"character": "sans", "message": "where's your brother?"}).json()
    sp = r["grounding"]["system_prompt"]
    assert "SANS CARES ABOUT" in sp
    assert "Papyrus" in sp
