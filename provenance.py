#!/usr/bin/env python3
"""Provenance — make the two-bucket wall VISIBLE per reply.

For each grounded reply we can say exactly what anchored it: which SACRED save
facts were in play, and which FREE sources (voice, retrieved lore, memory,
remembrance) coloured it. The UI renders this as a provenance overlay, turning
"facts are sacred, feelings are free" from a slogan into something the user can
see and audit.

PURE: given the SaveTruth + the free-bucket inputs + the guard result, returns a
structured provenance dict. No DB/network.
"""
from __future__ import annotations

from typing import Any, Optional


def build_provenance(
    save_truth: dict[str, Any],
    *,
    character: Optional[str] = None,
    lore_docs: Optional[list[dict[str, Any]]] = None,
    memory_used: bool = False,
    remembrance_used: bool = False,
    guard: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    st = save_truth or {}
    play = st.get("play_state") or {}
    route = st.get("route") or {}
    kills = st.get("kills") or {}
    # Definite per-character outcomes only (killed/spared/befriended) — SACRED.
    dispositions = {
        c: (d or {}).get("status")
        for c, d in (st.get("dispositions") or {}).items()
        if (d or {}).get("status") in ("killed", "spared", "befriended")
    }

    return {
        "sacred": {
            "name": play.get("name"),
            "love": play.get("love"),
            "route": route.get("route"),
            "route_confidence": route.get("confidence"),
            "kills": kills.get("total"),
            "dispositions": dispositions,
        },
        "free": {
            "voice": character,
            "lore": [d.get("title") for d in (lore_docs or []) if d.get("title")],
            "memory_used": bool(memory_used),
            "remembrance_used": bool(remembrance_used),
        },
        "guard": guard or {"clean": True, "issues": [], "checked": []},
    }
