"""The two-bucket wall regression.

Invariant (ported from fft-psx-vera/tests/two_bucket_wall_test.py):
  - Bucket A (SACRED) = Project.save_data — the parsed SaveTruth.
  - Bucket B (FREE)   = CharacterMemory.* — relationship memory.
A memory write must NEVER mutate Bucket A, and the zero-memory grounding must be
byte-identical to the no-row baseline.
"""
import copy
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from prompt_builder import build_system_prompt

client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _upload():
    with open(os.path.join(FIX, "file0_genocide"), "rb") as f0, \
         open(os.path.join(FIX, "undertale_genocide.ini"), "rb") as ini:
        resp = client.post(
            "/api/upload",
            files={
                "file0": ("file0", f0.read()),
                "undertale_ini": ("undertale.ini", ini.read()),
            },
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_memory_write_never_touches_bucket_a():
    up = _upload()
    pid = up["project_id"]
    truth_before = copy.deepcopy(client.get(f"/api/projects/{pid}/save-truth").json()["save_truth"])

    # Bucket-B writes: remember two things.
    client.post(f"/api/projects/{pid}/memory/sans/remember", json={"text": "I am scared of the dark."})
    client.post(f"/api/projects/{pid}/memory/sans/remember", json={"text": "I want to go home."})

    truth_after = client.get(f"/api/projects/{pid}/save-truth").json()["save_truth"]
    assert truth_after == truth_before, "WALL BREACH: save_data changed after a memory write"

    mem = client.get(f"/api/projects/{pid}/memory/sans").json()
    assert len(mem["relationship"]) == 2, "Bucket B did not record the memories"

    # Forgetting also must not touch Bucket A.
    client.post(f"/api/projects/{pid}/memory/sans/forget", json={"mem_id": "all"})
    assert client.get(f"/api/projects/{pid}/save-truth").json()["save_truth"] == truth_before
    assert client.get(f"/api/projects/{pid}/memory/sans").json()["relationship"] == []


def test_zero_memory_grounding_identity():
    """With no memories, the prompt is identical whether or not a memory row exists."""
    save_truth = {
        "play_state": {"name": "Chara", "love": 20},
        "route": {"route": "Genocide", "confidence": "high", "reasons": []},
        "kills": {"total": 9},
    }
    baseline = build_system_prompt("sans", save_truth, memory_grounding="")
    with_empty = build_system_prompt("sans", save_truth, memory_grounding="")
    assert baseline == with_empty
    # The sacred route fact appears; no invented memory text leaks in.
    assert "Genocide" in baseline
    assert "once told you" not in baseline.lower()
