#!/usr/bin/env python3
"""Avatar resolver — the portable resolver PATTERN from fft-psx-vera.

The FFT resolver chose: hand-curated portrait → generated portrait → custom
upload → job-class fallback → empty. We port the *pattern* (an ordered fallback
chain over a generic character) and drop the FFT-specific job/name maps. For
undertale-vera the chain is:

  1. relic-framed sample portrait on disk (static/assets/portraits/<slug>.png)
  2. a generated portrait URL recorded on the character
  3. empty string → the frontend renders a default SOUL-sigil crest

PURE pattern: takes a character dict + a portrait directory, returns a URL path or
"". Generated/sample portraits themselves are gitignored (see .gitignore).
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

PORTRAIT_DIR = os.environ.get(
    "UNDERTALE_VERA_PORTRAIT_DIR",
    os.path.join(os.path.dirname(__file__), "static", "assets", "portraits"),
)
PORTRAIT_URL_BASE = "/assets/portraits"

# Character emblem crests (our own original art; gitignored like portraits). These
# are the designed default crest per character — distinct from a user-supplied
# portrait. Resolved separately so the frontend can layer: photo > emblem > SVG.
EMBLEM_DIR = os.environ.get(
    "UNDERTALE_VERA_EMBLEM_DIR",
    os.path.join(os.path.dirname(__file__), "static", "assets", "emblems"),
)
EMBLEM_URL_BASE = "/assets/emblems"


def _slug(name: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").strip().lower()).strip("_")


def resolve_avatar(
    character: dict[str, Any],
    *,
    portrait_dir: str = PORTRAIT_DIR,
) -> str:
    """Resolve a character to an avatar URL via the fallback chain.

    `character` may carry a "generated_avatar_url". Returns "" when nothing is
    available — the frontend falls back to the SOUL-sigil crest (never an error).
    """
    name = character.get("name") or character.get("key")
    slug = _slug(name)

    # 1. Hand-framed sample portrait on disk.
    if slug:
        candidate = os.path.join(portrait_dir, f"{slug}.png")
        try:
            if os.path.isfile(candidate) and os.path.getsize(candidate) > 100:
                return f"{PORTRAIT_URL_BASE}/{slug}.png"
        except OSError:
            pass

    # 2. A generated portrait recorded on the character.
    gen = character.get("generated_avatar_url")
    if gen:
        return str(gen)

    # 3. Default crest.
    return ""


def resolve_emblem(character: dict[str, Any], *, emblem_dir: str = EMBLEM_DIR) -> str:
    """Resolve a character to its designed emblem-crest URL, or "".

    Checks static/assets/emblems/<slug>.png. Independent of resolve_avatar so the
    frontend can prefer a user-supplied portrait, fall back to this emblem, then to
    the inline SVG crest. Returns "" when no emblem file is present.
    """
    slug = _slug(character.get("name") or character.get("key"))
    if not slug:
        return ""
    candidate = os.path.join(emblem_dir, f"{slug}.png")
    try:
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 100:
            return f"{EMBLEM_URL_BASE}/{slug}.png"
    except OSError:
        pass
    return ""
