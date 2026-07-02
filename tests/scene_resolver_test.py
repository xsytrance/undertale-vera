"""Route-reactive scene resolver — generated backdrop when present, "" otherwise."""
import os

from fastapi.testclient import TestClient

import undertale_vera_app as appmod
from scene_resolver import resolve_scene, available_scenes, SCENE_ROUTES

client = TestClient(appmod.app)


def test_empty_when_no_art(tmp_path):
    assert resolve_scene("Genocide", scene_dir=str(tmp_path)) == ""
    assert available_scenes(scene_dir=str(tmp_path)) == {}


def test_resolves_existing_scene(tmp_path):
    (tmp_path / "genocide.png").write_bytes(b"\x89PNG" + b"\0" * 200)
    assert resolve_scene("Genocide", scene_dir=str(tmp_path)) == "/assets/scenes/genocide.png"
    assert resolve_scene("genocide", scene_dir=str(tmp_path)) == "/assets/scenes/genocide.png"
    assert available_scenes(scene_dir=str(tmp_path)) == {"genocide": "/assets/scenes/genocide.png"}


def test_unknown_route_normalizes_to_undetermined(tmp_path):
    (tmp_path / "undetermined.png").write_bytes(b"\x89PNG" + b"\0" * 200)
    assert resolve_scene("???", scene_dir=str(tmp_path)) == "/assets/scenes/undetermined.png"
    assert resolve_scene(None, scene_dir=str(tmp_path)) == "/assets/scenes/undetermined.png"


def test_tiny_file_is_ignored(tmp_path):
    # A truncated/placeholder file (< 100 bytes) is not served.
    (tmp_path / "pacifist.png").write_bytes(b"x")
    assert resolve_scene("Pacifist", scene_dir=str(tmp_path)) == ""


def test_scene_routes_match_route_vocabulary():
    assert set(SCENE_ROUTES) == {"pacifist", "neutral", "genocide", "undetermined"}


def test_scenes_endpoint_shape():
    # No generated art committed (gitignored), so the map is empty but well-formed.
    body = client.get("/api/scenes").json()
    assert "scenes" in body and isinstance(body["scenes"], dict)
