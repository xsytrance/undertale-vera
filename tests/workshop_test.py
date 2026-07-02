"""The Prompt Workshop — live-true content, never documentation-by-copy."""
from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import workshop


client = TestClient(appmod.app)


def test_workshop_endpoint_serves_live_content():
    w = client.get("/api/workshop").json()
    # the example prompt is the real assembler's output for the demo truth
    assert "HARD FACTS" in w["example_prompt"]
    assert "DEMO" in w["example_prompt"]          # the labelled demo save, no real player
    assert "Sans" in w["example_prompt"]
    assert len(w["anatomy"]) >= 5
    feats = [i["feature"] for i in w["instructions"]]
    assert "Report Cards" in feats and "Judgment" in feats and "Session Stories" in feats
    for i in w["instructions"]:
        assert i["text"].strip(), i["feature"]


def test_instructions_come_from_the_real_modules():
    import journal, reports, proactive, divergence, session_story
    by = {i["feature"]: i["text"] for i in workshop.instructions()}
    assert by["Keepsake Journal"] == journal.inscription_instruction(workshop.DEMO_TRUTH)
    assert by["Report Cards"] == reports.report_instruction(workshop.DEMO_TRUTH)
    assert by["Reach-outs"] == proactive.reach_out_instruction(workshop.DEMO_TRUTH)
    assert by["Two-Save Divergence"] == divergence.instruction()
    assert by["Session Stories"] == session_story.instruction(3)


def test_verbatim_copies_do_not_drift():
    """The two instructions that live inline in the app must match our copies."""
    import re
    squash = lambda t: re.sub(r'[\s"]+', "", t)   # ignore indentation/quote-joins
    src = squash(open("undertale_vera_app.py").read())
    for text in (workshop.JUDGMENT_INSTRUCTION, workshop.GUIDED_REACT_INSTRUCTION):
        assert squash(text) in src, text[:60]
