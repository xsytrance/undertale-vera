"""The Commons — music downloads (list + zip), honest about what's on disk."""
import io
import os
import zipfile

from fastapi.testclient import TestClient

import undertale_vera_app as appmod


client = TestClient(appmod.app)


def test_music_list_and_zip(tmp_path, monkeypatch):
    (tmp_path / "a-new-save-file.mp3").write_bytes(b"x" * 100)
    (tmp_path / "char-jevil.mp3").write_bytes(b"y" * 200)
    (tmp_path / "notes.txt").write_text("not music")
    monkeypatch.setattr(appmod, "AUDIO_DIR", str(tmp_path))
    r = client.get("/api/community/music").json()
    assert r["count"] == 2 and "CC BY 4.0" in r["license"]
    titles = {f["file"]: f["title"] for f in r["files"]}
    assert titles["a-new-save-file.mp3"].startswith("A New Save File")
    assert titles["char-jevil.mp3"] == "Jevil (character theme)"

    z = client.get("/api/community/music.zip")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(z.content))
    names = zf.namelist()
    assert "LICENSE.txt" in names and "ember-soundtrack/char-jevil.mp3" in names
    assert "CC BY 4.0" in zf.read("LICENSE.txt").decode()


def test_music_zip_404_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "AUDIO_DIR", str(tmp_path))
    assert client.get("/api/community/music.zip").status_code == 404
    assert client.get("/api/community/music").json()["count"] == 0
