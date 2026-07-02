"""Report Cards — each character's after-action report, and emailing it."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
import agentmail_client
import reports as reports_mod
from llm_client import LLMUnavailable


client = TestClient(appmod.app)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _truth(route="Neutral"):
    return {"play_state": {"name": "Frisk", "love": 5},
            "route": {"route": route, "confidence": "medium"}, "kills": {"total": 5}}


def _upload(stem, ini):
    with open(os.path.join(FIX, stem), "rb") as f0, open(os.path.join(FIX, ini), "rb") as inif:
        return client.post("/api/upload", files={
            "file0": ("file0", f0.read()), "undertale_ini": ("undertale.ini", inif.read())
        }).json()["project_id"]


# ── pure module ──────────────────────────────────────────────────────────────

def test_report_instruction_carries_route():
    assert "Genocide" in reports_mod.report_instruction(_truth("Genocide"))
    assert "not yet clear" in reports_mod.report_instruction(_truth("undetermined"))


def test_fallback_report_is_grounded_and_never_invented():
    f = reports_mod.fallback_report("Sans", _truth("Genocide"))
    assert "Sans" in f and "Genocide" in f and f.lower().startswith("verdict:")


def test_split_verdict():
    v, body = reports_mod.split_verdict("Verdict: blood on the snow.\n\nYou did the thing.")
    assert v == "blood on the snow." and body == "You did the thing."
    v2, body2 = reports_mod.split_verdict("A short headline\n\nthe body")
    assert v2 == "A short headline" and body2 == "the body"
    v3, body3 = reports_mod.split_verdict("just one long line with no verdict marker at all here friend")
    assert v3 == "" and body3.startswith("just one long line")


def test_build_report_markdown():
    md = reports_mod.build_report_markdown(
        [{"author": "Toriel", "verdict": "kind", "text": "Verdict: kind\n\nwell done."}], "Frisk")
    assert "# Report Cards — Frisk" in md and "## Toriel — *kind*" in md and "well done." in md


# ── endpoint ─────────────────────────────────────────────────────────────────

def test_single_report_returns_verdict_and_body(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: careful soul.\n\nyou spared everyone.", "model": "m"})
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/report", json={"character": "toriel"}).json()["report"]
    assert r["author"] == "Toriel"
    assert r["verdict"] == "careful soul."
    assert "spared everyone" in r["body"]
    assert r["grounding_source"] == "llm"


def test_report_to_journal_inscribes(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: ok.\n\nfine run.", "model": "m"})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    before = len(client.get(f"/api/projects/{pid}/journal").json()["entries"])
    r = client.post(f"/api/projects/{pid}/report", json={"character": "sans", "to_journal": True}).json()
    assert r["report"]["inscribed"] is True
    entries = client.get(f"/api/projects/{pid}/journal").json()["entries"]
    assert len(entries) == before + 1
    assert any(e["kind"] == "report" and e["author"] == "Sans" for e in entries)


def test_report_falls_back_without_model(monkeypatch):
    def boom(*a, **k):
        raise LLMUnavailable("no model")
    monkeypatch.setattr(appmod, "generate_reply", boom)
    pid = _upload("file0_genocide", "undertale_genocide.ini")
    r = client.post(f"/api/projects/{pid}/report", json={"character": "flowey"}).json()["report"]
    assert r["grounding_source"] == "deterministic_fallback"
    assert r["text"] and "Genocide" in r["text"]


def test_full_report_covers_the_cast(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: noted.\n\na run.", "model": "m"})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    res = client.post(f"/api/projects/{pid}/report/full").json()
    assert len(res["reports"]) >= 8
    assert "# Report Cards" in res["markdown"]


def test_reports_persist_to_history_and_filter(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: noted.\n\na run.", "model": "m"})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    client.post(f"/api/projects/{pid}/report", json={"character": "sans"})
    client.post(f"/api/projects/{pid}/report", json={"character": "toriel"})
    client.post(f"/api/projects/{pid}/report", json={"character": "sans"})
    listing = client.get(f"/api/projects/{pid}/reports").json()
    assert len(listing["reports"]) == 3
    # newest first
    assert listing["reports"][0]["created_at"] >= listing["reports"][-1]["created_at"]
    assert listing["counts"]["active"] == 3
    assert listing["counts"]["by_author"]["Sans"] == 2
    # filter by character
    sans_only = client.get(f"/api/projects/{pid}/reports", params={"character": "sans"}).json()
    assert len(sans_only["reports"]) == 2 and all(r["author"] == "Sans" for r in sans_only["reports"])


def test_report_archive_and_restore(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: ok.\n\nrun.", "model": "m"})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    rid = client.post(f"/api/projects/{pid}/report", json={"character": "sans"}).json()["report"]["id"]
    # archive → drops out of the default (active) listing, shows under archived
    client.patch(f"/api/projects/{pid}/reports/{rid}", json={"status": "archived"})
    assert all(r["id"] != rid for r in client.get(f"/api/projects/{pid}/reports").json()["reports"])
    arch = client.get(f"/api/projects/{pid}/reports", params={"status": "archived"}).json()["reports"]
    assert any(r["id"] == rid and r["status"] == "archived" for r in arch)
    # restore
    client.patch(f"/api/projects/{pid}/reports/{rid}", json={"status": "active"})
    assert any(r["id"] == rid for r in client.get(f"/api/projects/{pid}/reports").json()["reports"])


def test_report_delete(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: ok.\n\nrun.", "model": "m"})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    rid = client.post(f"/api/projects/{pid}/report", json={"character": "sans"}).json()["report"]["id"]
    assert client.delete(f"/api/projects/{pid}/reports/{rid}").json()["ok"] is True
    assert all(r["id"] != rid for r in client.get(f"/api/projects/{pid}/reports", params={"status": "all"}).json()["reports"])
    assert client.delete(f"/api/projects/{pid}/reports/{rid}").status_code == 404


def test_report_unknown_character_404(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply", lambda sp, um, **k: {"text": "x", "model": "m"})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    assert client.post(f"/api/projects/{pid}/report", json={"character": "nobody"}).status_code == 404


# ── email (AgentMail) ────────────────────────────────────────────────────────

def test_email_status_unconfigured(monkeypatch):
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)
    s = client.get("/api/email/status").json()
    assert s["configured"] is False


def test_email_report_unconfigured_degrades(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: ok.\n\nrun.", "model": "m"})
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    r = client.post(f"/api/projects/{pid}/report/email", json={"character": "sans"}).json()
    assert r["email"]["sent"] is False and "configured" in r["email"]["reason"].lower()
    assert r["report"]["text"]   # the report is still generated/returned


def test_email_report_sends_when_configured(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: careful.\n\nkind run.", "model": "m"})
    sent = {}

    def fake_send(subject, text, to=None, **k):
        sent.update(subject=subject, text=text, to=to)
        return {"sent": True, "to": to or "player@example.com", "id": "msg_1"}

    monkeypatch.setattr(agentmail_client, "send", fake_send)
    pid = _upload("file0_pacifist", "undertale_pacifist.ini")
    r = client.post(f"/api/projects/{pid}/report/email", json={"character": "toriel"}).json()
    assert r["email"]["sent"] is True
    assert "A report from Toriel" in sent["subject"]
    assert "kind run" in sent["text"]


def test_email_report_uses_given_text_verbatim(monkeypatch):
    # when text is supplied, the shown report is emailed as-is — no regeneration
    def boom(*a, **k):
        raise AssertionError("generate_reply should not be called when text is provided")
    monkeypatch.setattr(appmod, "generate_reply", boom)
    captured = {}
    monkeypatch.setattr(agentmail_client, "send",
                        lambda subject, text, to=None, **k: captured.update(subject=subject, text=text) or {"sent": True})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    r = client.post(f"/api/projects/{pid}/report/email",
                    json={"character": "sans", "text": "Verdict: x\n\nthe exact shown report",
                          "verdict": "x"}).json()
    assert r["email"]["sent"] is True
    assert captured["text"] == "Verdict: x\n\nthe exact shown report"


def test_journal_add_inscribes_verbatim():
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    before = len(client.get(f"/api/projects/{pid}/journal").json()["entries"])
    client.post(f"/api/projects/{pid}/journal/add",
                json={"author": "Undyne", "text": "Verdict: fought well\n\nyou never gave up."})
    entries = client.get(f"/api/projects/{pid}/journal").json()["entries"]
    assert len(entries) == before + 1
    added = [e for e in entries if e["author"] == "Undyne"][-1]
    assert added["kind"] == "report" and "never gave up" in added["text"]


def test_email_digest_sends_collected_reports(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: noted.\n\na run.", "model": "m"})
    sent = {}
    monkeypatch.setattr(agentmail_client, "send",
                        lambda subject, text, to=None, **k: sent.update(subject=subject, text=text) or {"sent": True})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    client.post(f"/api/projects/{pid}/report", json={"character": "sans"})
    client.post(f"/api/projects/{pid}/report", json={"character": "toriel"})
    r = client.post(f"/api/projects/{pid}/report/digest/email", json={}).json()
    assert r["count"] == 2 and r["email"]["sent"] is True
    assert "2 voices" in sent["subject"]
    assert "## Sans" in sent["text"] and "## Toriel" in sent["text"]


def test_email_digest_empty_is_graceful(monkeypatch):
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    r = client.post(f"/api/projects/{pid}/report/digest/email", json={}).json()
    assert r["count"] == 0 and r["email"]["sent"] is False and "request some" in r["email"]["reason"]


def test_email_digest_excludes_archived(monkeypatch):
    monkeypatch.setattr(appmod, "generate_reply",
                        lambda sp, um, **k: {"text": "Verdict: ok.\n\nrun.", "model": "m"})
    captured = {}
    monkeypatch.setattr(agentmail_client, "send",
                        lambda subject, text, to=None, **k: captured.update(text=text) or {"sent": True})
    pid = _upload("file0_neutral", "undertale_neutral.ini")
    rid = client.post(f"/api/projects/{pid}/report", json={"character": "sans"}).json()["report"]["id"]
    client.post(f"/api/projects/{pid}/report", json={"character": "undyne"})
    client.patch(f"/api/projects/{pid}/reports/{rid}", json={"status": "archived"})   # hide Sans
    r = client.post(f"/api/projects/{pid}/report/digest/email", json={}).json()
    assert r["count"] == 1 and "## Undyne" in captured["text"] and "## Sans" not in captured["text"]


def test_agentmail_send_raises_when_unconfigured(monkeypatch):
    monkeypatch.delenv("AGENTMAIL_API_KEY", raising=False)
    monkeypatch.delenv("AGENTMAIL_INBOX_ID", raising=False)
    try:
        agentmail_client.send("subj", "body", to="x@example.com")
        assert False, "expected EmailUnavailable"
    except agentmail_client.EmailUnavailable:
        pass
