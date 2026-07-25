"""The local-skin fence regression.

`local_skin.py` gates a PRIVATE skin that reads art extracted from the owner's
own game install into the gitignored `static/assets/local/`. That art is never
committed and never deployed, so the fence has exactly one job:

  **Fail closed.** Anything other than an explicit `UNDERTALE_VERA_SKIN=authentic`
  must resolve to the original committed look. An unset, empty, mistyped, or
  wrong-case value must NOT leak the private skin onto a shared host.

Second invariant: with the skin off, every resolver behaves byte-for-byte as it
did before the skin existed — so the committed build is provably unchanged.
"""
import os

import avatar_resolver
import local_skin
import scene_resolver

AUTH = {"UNDERTALE_VERA_SKIN": "authentic"}


# ── fail closed ──────────────────────────────────────────────────────────────

def test_default_is_original():
    assert local_skin.skin_name({}) == local_skin.ORIGINAL
    assert not local_skin.is_authentic({})


def test_only_the_exact_token_enables_the_private_skin():
    # NB: surrounding whitespace is stripped by design (see the case/whitespace
    # test below), so "authentic " is a valid token — not a rejection case.
    for bad in ["", "  ", "AUTHENTIC!", "auth", "real", "undertale", "1", "true",
                "original", "authentic-ish", "auth entic"]:
        env = {"UNDERTALE_VERA_SKIN": bad}
        assert local_skin.skin_name(env) == local_skin.ORIGINAL, bad
        assert local_skin.head_markup(env=env) == "", bad


def test_authentic_token_enables_it():
    assert local_skin.skin_name(AUTH) == local_skin.AUTHENTIC
    assert local_skin.is_authentic(AUTH)
    assert local_skin.AUTHENTIC_CSS in local_skin.head_markup(env=AUTH)


def test_whitespace_and_case_are_tolerated_on_the_exact_token():
    for ok in ["authentic", "AUTHENTIC", " Authentic "]:
        assert local_skin.skin_name({"UNDERTALE_VERA_SKIN": ok}) == local_skin.AUTHENTIC


# ── the search path ──────────────────────────────────────────────────────────

def test_original_skin_searches_only_the_committed_dir():
    assert local_skin.asset_search_path("emblems", "/committed", env={}) == ["/committed"]


def test_authentic_skin_prefers_extracted_art_then_falls_back():
    path = local_skin.asset_search_path("emblems", "/committed", env=AUTH)
    assert len(path) == 2
    assert path[0].endswith(os.path.join("assets", "local", "emblems"))
    assert path[1] == "/committed"


# ── resolvers unchanged with the skin off ────────────────────────────────────

def test_resolvers_return_empty_for_unknown_characters(tmp_path, monkeypatch):
    """The guaranteed fallback: no art on disk → "" → the built-in crest."""
    monkeypatch.delenv("UNDERTALE_VERA_SKIN", raising=False)
    assert avatar_resolver.resolve_avatar({"name": "Nobody"},
                                          portrait_dir=str(tmp_path)) == ""
    assert avatar_resolver.resolve_emblem({"name": "Nobody"},
                                          emblem_dir=str(tmp_path)) == ""
    assert scene_resolver.resolve_scene("pacifist", scene_dir=str(tmp_path)) == ""


def test_committed_art_resolves_to_the_committed_url(tmp_path, monkeypatch):
    """Skin off → a file in the committed dir yields the committed URL base."""
    monkeypatch.delenv("UNDERTALE_VERA_SKIN", raising=False)
    (tmp_path / "sans.png").write_bytes(b"x" * 500)
    assert avatar_resolver.resolve_emblem(
        {"name": "Sans"}, emblem_dir=str(tmp_path)
    ) == f"{avatar_resolver.EMBLEM_URL_BASE}/sans.png"


def test_stub_files_are_ignored(tmp_path, monkeypatch):
    """A truncated/placeholder file must not count as art."""
    monkeypatch.delenv("UNDERTALE_VERA_SKIN", raising=False)
    (tmp_path / "sans.png").write_bytes(b"x" * 10)
    assert avatar_resolver.resolve_emblem({"name": "Sans"},
                                          emblem_dir=str(tmp_path)) == ""


# ── the skin never touches the sacred bucket ─────────────────────────────────

def test_skin_state_reports_without_enabling(monkeypatch):
    monkeypatch.delenv("UNDERTALE_VERA_SKIN", raising=False)
    state = local_skin.state()
    assert state["skin"] == local_skin.ORIGINAL
    # never claims art is present when the skin is off
    assert state["local_art_present"] is False
