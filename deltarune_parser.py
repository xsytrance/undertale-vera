#!/usr/bin/env python3
"""Deltarune Chapter 1 save parser — parser-truth, READ-ONLY.

Deltarune persists per-chapter slots as `filech{chapter}_{slot}` (slot 0-2; slot 3
holds completion data) under %LocalAppData%/DELTARUNE. Like Undertale's file0 it is
a newline-delimited GameMaker text save, read sequentially line-by-line.

THE PARSER-TRUTH LAW (FACTS ARE SACRED) applies unchanged:
  - We only assign *meaning* to lines that are community-documented AND corroborated.
    Public documentation for Chapter 1 is thin, so v1 names very little:
      line 1  → player/file name  (confidence "medium" — consistently documented)
      line 11 → Dark Dollars      (confidence "medium" — multiple sources agree)
  - EVERYTHING else is preserved RAW (line index → value) and semantically `null` —
    never guessed. Promotion happens the same way undertale-vera's file0 map grew:
    corroboration against a real save corpus (see tools/parser_expand.py), evidence,
    not guesses.
  - Out-of-range / missing → None with confidence "unknown". Never writes a save.

PURE module (no DB, no network) — unit-testable in isolation.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Optional

# Named line map (1-based line number → field, confidence). Deliberately tiny; grows
# only with corroborated evidence from real saves.
CH1_LINES: dict[int, tuple[str, str]] = {
    1: ("name", "medium"),
    11: ("dark_dollars", "medium"),
}

_FILENAME_RE = re.compile(r"filech(\d+)_(\d+)$", re.IGNORECASE)


def looks_like_deltarune(filename: Optional[str]) -> bool:
    """True when the uploaded filename is a Deltarune chapter slot (filech1_0 …)."""
    return bool(filename and _FILENAME_RE.search(filename.strip()))


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

    fields: dict[str, Any] = {"name": None, "dark_dollars": None}
    confidence: dict[str, str] = {k: "unknown" for k in fields}

    for lineno, (field, conf) in CH1_LINES.items():
        idx = lineno - 1
        if idx >= len(lines):
            warnings.append(f"line {lineno} ({field}) missing — save shorter than expected")
            continue
        raw = lines[idx].strip()
        if field == "name":
            fields["name"] = raw or None
            confidence["name"] = conf if raw else "unknown"
        else:
            val = _to_int(raw)
            fields[field] = val
            confidence[field] = conf if val is not None else "unknown"
            if val is None and raw:
                warnings.append(f"line {lineno} ({field}) was not a clean integer: {raw!r}")

    digest = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]
    return {
        "game": "deltarune",
        "chapter": chapter,
        "slot": slot,
        "fields": fields,
        "confidence": confidence,
        # the honest remainder: every line preserved raw, meaning unassigned
        "raw_lines": {i + 1: ln for i, ln in enumerate(lines) if ln.strip() != ""},
        "line_count": len(lines),
        "digest": digest,
        "warnings": warnings,
    }
