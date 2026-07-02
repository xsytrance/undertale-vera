#!/usr/bin/env python3
"""Deltarune Chapter 1 save parser — parser-truth, READ-ONLY.

Deltarune persists per-chapter slots as `filech{chapter}_{slot}` (slots 0-2; slot 3
holds completion data; slot 9 is an auto/backup twin) under %LocalAppData%/DELTARUNE,
plus `dr.ini` — a completion-time summary INI ([G0] Name/Room/Time/Love/Level, and
UraBoss once the secret boss is resolved).

THE PARSER-TRUTH LAW (FACTS ARE SACRED): meaning is only assigned to lines that are
corroborated by EVIDENCE. The v1 map named two thin publicly-documented lines; this
v2 map was promoted against a real 41-save labelled Chapter 1 corpus (v1.07-era,
every save exactly 10318 fields) via tools/deltarune_expand.py:

  line 1     name           dr.ini Name agreed 41/41                       → high
  line 2     name_alt       dr.ini Name agreed 41/41 (duplicate of line 1) → high
  lines 8-10 party slots    documented IDs (1 Kris, 2 Susie, 3 Ralsei,
                            4 Noelle); the corpus replays Ch1's actual
                            story beats (Ralsei joins, Susie leaves in the
                            Forest, rejoins at the Prison)                 → high
  line 11    dark_dollars   public docs + currency behaviour across the
                            corpus (drops exactly at the shopping saves)   → high
  line 559   jevil_state    the ONLY clean corpus-wide partition flag for
                            "Jevil defeated" (0 → 2), and dr.ini UraBoss
                            agrees 7/7 wherever the key exists             → high
  line 10317 room           dr.ini Room agreed 41/41                       → high
  line 10318 time           dr.ini Time agreed 41/41 (frames)              → high

Everything else stays RAW and semantically null — never guessed. The tail/flag
indices are layout-dependent, so when a save's field count differs from the
corroborated 10318 they are honestly demoted to unknown; the head fields (1-11)
keep "medium" (documented as stable across early layouts).

PURE module (no DB, no network) — unit-testable in isolation.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

EXPECTED_FIELDS = 10318   # the corroborated v1.07-era Chapter 1 layout

# 1-based line → (field, confidence-at-expected-layout, safe-at-other-layouts)
CH1_LINES: dict[int, tuple[str, str, bool]] = {
    1: ("name", "high", True),
    8: ("party_1", "high", True),
    9: ("party_2", "high", True),
    10: ("party_3", "high", True),
    11: ("dark_dollars", "high", True),
    559: ("jevil_state", "high", False),
    10317: ("room", "high", False),
    10318: ("time", "high", False),
}

# Documented party encoding (community-stable).
PARTY_IDS: dict[int, Optional[str]] = {0: None, 1: "Kris", 2: "Susie", 3: "Ralsei", 4: "Noelle"}

_FILENAME_RE = re.compile(r"filech(\d+)_(\d+)$", re.IGNORECASE)


def looks_like_deltarune(filename: Optional[str]) -> bool:
    """True when the uploaded filename is a Deltarune chapter slot (filech1_0 …)."""
    return bool(filename and _FILENAME_RE.search(filename.strip()))


def looks_like_dr_ini(filename: Optional[str], content: Optional[str] = None) -> bool:
    """True for Deltarune's dr.ini (by name, or by its [G0] section)."""
    if filename and filename.strip().lower().endswith("dr.ini"):
        return True
    return bool(content and "[G0]" in content[:200])


def chapter_slot_from_filename(filename: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """(chapter, slot) from a filech{A}_{B} name; (None, None) when unrecognisable."""
    m = _FILENAME_RE.search((filename or "").strip())
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _to_int(raw: str) -> Optional[int]:
    """GameMaker numbers are often '42.000000'; parse honestly, None when not a number."""
    s = (raw or "").strip()
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    i = int(f)
    return i if f == i else None


def parse_deltarune_save(content: bytes | str, filename: Optional[str] = None) -> dict[str, Any]:
    """Parse a filech{N}_{slot} save. Never raises on malformed content — warnings only."""
    if isinstance(content, bytes):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        text = content
    lines = text.replace("\r\n", "\n").split("\n")
    warnings: list[str] = []
    chapter, slot = chapter_slot_from_filename(filename)
    if chapter is None:
        warnings.append("filename did not match filech{chapter}_{slot}; chapter unknown")
    expected_layout = len(lines) == EXPECTED_FIELDS
    if not expected_layout:
        warnings.append(
            f"save has {len(lines)} fields (corroborated layout is {EXPECTED_FIELDS}) — "
            "layout-dependent fields demoted to unknown"
        )

    fields: dict[str, Any] = {}
    confidence: dict[str, str] = {}
    for lineno, (field, conf, head_safe) in CH1_LINES.items():
        idx = lineno - 1
        if idx >= len(lines) or (not expected_layout and not head_safe):
            fields[field] = None
            confidence[field] = "unknown"
            continue
        raw = lines[idx].strip()
        if field == "name":
            fields[field] = raw or None
            confidence[field] = ("high" if expected_layout else "medium") if raw else "unknown"
        else:
            val = _to_int(raw)
            fields[field] = val
            confidence[field] = (conf if expected_layout else "medium") if val is not None else "unknown"
            if val is None and raw:
                warnings.append(f"line {lineno} ({field}) was not a clean integer: {raw!r}")

    # party: documented IDs → names (unknown ids preserved honestly as "#<id>")
    party: list[str] = []
    for slot_field in ("party_1", "party_2", "party_3"):
        pid = fields.get(slot_field)
        if pid:
            party.append(PARTY_IDS.get(pid) or f"#{pid}")
    fields["party"] = party or None
    confidence["party"] = confidence.get("party_1", "unknown")

    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]
    return {
        "game": "deltarune",
        "chapter": chapter,
        "slot": slot,
        "fields": fields,
        "confidence": confidence,
        # the honest remainder: every non-empty line preserved raw, meaning unassigned
        "raw_lines": {i + 1: ln for i, ln in enumerate(lines) if ln.strip() != ""},
        "line_count": len(lines),
        "expected_layout": expected_layout,
        "digest": digest,
        "warnings": warnings,
    }


def parse_dr_ini(content: bytes | str) -> dict[str, Any]:
    """Parse dr.ini's [G0] summary (written at chapter completion). Honest + tiny."""
    if isinstance(content, bytes):
        text = content.decode("utf-8", "replace")
    else:
        text = content
    out: dict[str, Any] = {"name": None, "room": None, "time": None,
                           "love": None, "level": None, "uraboss": None}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section != "G0" or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip().lower()
        v = v.strip().strip('"')
        if k == "name":
            out["name"] = v or None
        elif k in ("room", "time", "love", "level", "uraboss"):
            out[k] = _to_int(v)
    return out
