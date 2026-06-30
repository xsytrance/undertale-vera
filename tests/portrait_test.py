"""Bring-your-own portrait: a user-supplied image becomes a character's avatar,
served from the gitignored portraits folder; clearing reverts to the crest."""
import undertale_vera_app as appmod
from fastapi.testclient import TestClient

client = TestClient(appmod.app)

# a small (>100 byte) PNG-ish blob; the resolver only checks isfile + size.
_IMG = b"\x89PNG\r\n\x1a\n" + b"uvera-test-portrait-bytes" * 8


def test_set_and_clear_portrait_round_trip():
    # default: no supplied portrait → empty avatar_url (frontend draws the crest)
    chars = {c["name"]: c for c in client.get("/api/characters").json()["characters"]}
    assert chars["Sans"]["avatar_url"] == ""

    # upload → avatar_url now points at the served portraits path
    r = client.post("/api/characters/sans/portrait",
                    files={"image": ("sans.png", _IMG, "image/png")})
    assert r.status_code == 200
    assert r.json()["avatar_url"] == "/assets/portraits/sans.png"
    chars = {c["name"]: c for c in client.get("/api/characters").json()["characters"]}
    assert chars["Sans"]["avatar_url"] == "/assets/portraits/sans.png"

    # clear → back to the default crest
    r = client.delete("/api/characters/sans/portrait")
    assert r.status_code == 200 and r.json()["avatar_url"] == ""
    chars = {c["name"]: c for c in client.get("/api/characters").json()["characters"]}
    assert chars["Sans"]["avatar_url"] == ""


def test_portrait_rejects_unknown_character():
    assert client.post("/api/characters/nobody/portrait",
                       files={"image": ("x.png", _IMG, "image/png")}).status_code == 404
    assert client.delete("/api/characters/nobody/portrait").status_code == 404


def test_portrait_rejects_tiny_image():
    assert client.post("/api/characters/toriel/portrait",
                       files={"image": ("t.png", b"tiny", "image/png")}).status_code == 400
