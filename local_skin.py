#!/usr/bin/env python3
"""Local skin selector — the private "authentic" look, fenced off from the repo.

undertale-vera ships ONE committed look: the original ember-gem art
(`determination.css` + `undertale.css`). That is the only skin that is ever
built, deployed, or shared.

A second skin exists for the owner's own machine. `tools/extract_undertale_assets.py`
reads the owner's OWN installed copy of the game and writes real sprites, fonts,
and backdrops into `static/assets/local/` — a gitignored directory. Setting

    UNDERTALE_VERA_SKIN=authentic

points the resolvers at that directory and loads `css/authentic.css` on top.

Rules this module exists to enforce:
  * Default is ALWAYS "original". An unset/……unknown value degrades to original,
    never to authentic — a missing env var must not leak the private skin.
  * Anything under `static/assets/local/` is extracted game art. It is
    gitignored and belongs to the game's creators: never commit it, never bundle
    it into a build, never serve it from a shared/hosted deploy.
  * The authentic skin is additive. It never mutates the original CSS, and with
    the art absent the app renders exactly as it does today (every resolver in
    the chain already falls back to "" → the built-in crest).

PURE helpers (no I/O beyond an os.path.isdir existence probe) so the suite can
assert the fence without the art being present.
"""
from __future__ import annotations

import os
from typing import Optional

ORIGINAL = "original"
AUTHENTIC = "authentic"
SKINS = (ORIGINAL, AUTHENTIC)

#: Extracted-art root. Gitignored. Never committed, never deployed.
LOCAL_ASSET_DIR = os.path.join(os.path.dirname(__file__), "static", "assets", "local")
LOCAL_URL_BASE = "/assets/local"

#: The override stylesheet, loaded AFTER the committed skin so it layers on top.
AUTHENTIC_CSS = "/css/authentic.css"


def skin_name(env: Optional[dict[str, str]] = None) -> str:
    """The active skin: "original" (default) or "authentic".

    Anything unrecognised — unset, empty, typo'd, wrong case — degrades to
    "original". Failing closed matters: the private skin must never switch
    itself on by accident on a shared host.
    """
    raw = (env if env is not None else os.environ).get("UNDERTALE_VERA_SKIN", "")
    value = (raw or "").strip().lower()
    return value if value in SKINS else ORIGINAL


def is_authentic(env: Optional[dict[str, str]] = None) -> bool:
    """True only when the authentic local skin is explicitly selected."""
    return skin_name(env) == AUTHENTIC


def local_dir(kind: str, *, root: str = LOCAL_ASSET_DIR) -> str:
    """Path to an extracted-art subdirectory ("portraits", "emblems", …)."""
    return os.path.join(root, kind)


def asset_search_path(kind: str, default_dir: str, *,
                      root: str = LOCAL_ASSET_DIR,
                      env: Optional[dict[str, str]] = None) -> list[str]:
    """Ordered directories a resolver should check for `kind` art.

    Authentic skin → the extracted-art dir first, then the committed default
    (so a slot with no real sprite mapped yet still falls back to our own art,
    and then to the built-in crest). Original skin → the default alone, which
    is byte-for-byte today's behaviour.
    """
    if is_authentic(env):
        return [local_dir(kind, root=root), default_dir]
    return [default_dir]


def head_markup(*, env: Optional[dict[str, str]] = None) -> str:
    """Extra <head> markup for the active skin ("" for the original skin).

    Returned rather than written into index.html so the committed page stays
    the original look — the authentic skin exists only at serve time, on the
    owner's machine.
    """
    if not is_authentic(env):
        return ""
    return f'<link rel="stylesheet" href="{AUTHENTIC_CSS}" />'


def state(*, env: Optional[dict[str, str]] = None) -> dict[str, object]:
    """Skin state for /api/health — what's on, and whether art is actually present."""
    name = skin_name(env)
    has_art = False
    if name == AUTHENTIC:
        try:
            has_art = os.path.isdir(LOCAL_ASSET_DIR)
        except OSError:
            has_art = False
    return {"skin": name, "local_art_present": has_art}
