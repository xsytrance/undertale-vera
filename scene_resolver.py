#!/usr/bin/env python3
"""Scene resolver — route-reactive backdrop art, the avatar_resolver pattern for scenes.

The companion app sits over a save whose ROUTE is morally-loaded. The backdrop
should answer that: a warm Pacifist dawn, an ashen Genocide aftermath, an uncertain
murk for `undetermined`. This resolves a route to a generated scene image when one
exists on disk, and "" otherwise — the frontend always has a CSS route-tinted
gradient as the guaranteed fallback, so the feature works before Prime delivers art.

Scenes are produced by the ComfyUI pipeline (see docs/PRIME_BRIEF.md) at
static/assets/scenes/<route>.png and are GITIGNORED — we never batch-commit
generated art; only the resolver + the contract are committed.

PURE pattern (no DB/network): route string + scene dir → URL path or "".
"""
from __future__ import annotations

import os
from typing import Optional

SCENE_DIR = os.environ.get(
    "UNDERTALE_VERA_SCENE_DIR",
    os.path.join(os.path.dirname(__file__), "static", "assets", "scenes"),
)
SCENE_URL_BASE = "/assets/scenes"

# The routes we ship a backdrop slot for. Matches route_detection.ROUTES.
SCENE_ROUTES = ("pacifist", "neutral", "genocide", "undetermined")


def _norm_route(route: Optional[str]) -> str:
    r = (route or "").strip().lower()
    return r if r in SCENE_ROUTES else "undetermined"


def resolve_scene(route: Optional[str], *, scene_dir: str = SCENE_DIR) -> str:
    """Resolve a route to a backdrop URL, or "" when no generated scene exists.

    Unknown/empty routes normalize to 'undetermined' (never an error). "" tells the
    frontend to keep its CSS gradient fallback.
    """
    key = _norm_route(route)
    candidate = os.path.join(scene_dir, f"{key}.png")
    try:
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 100:
            return f"{SCENE_URL_BASE}/{key}.png"
    except OSError:
        pass
    return ""


def available_scenes(*, scene_dir: str = SCENE_DIR) -> dict[str, str]:
    """{route: url} for every route that currently has a generated backdrop on disk."""
    out: dict[str, str] = {}
    for route in SCENE_ROUTES:
        url = resolve_scene(route, scene_dir=scene_dir)
        if url:
            out[route] = url
    return out
