#!/usr/bin/env python3
"""Undertale save parser — parser-truth, READ-ONLY.

Ported pattern (not content) from fft-psx-vera/save_parser.py: every field read is
null-guarded, unexpected structure produces *warnings*, never a crash, and anything
unrecognized is surfaced honestly rather than guessed.

Undertale persists two files we read:
  - file0      : newline-delimited values (the main save slot).
  - undertale.ini : an INI file of [sections] with key=value flags.

THE PARSER-TRUTH LAW (north star: FACTS ARE SACRED):
  - We only assign *meaning* to fields that are community-documented and stable
    across game versions. Everything else is preserved RAW (file0 line index /
    ini key) but left semantically `null` — never guessed.
  - Out-of-range / missing → `None`, with a `confidence` of "unknown".
  - This module never writes a save. There are no mutation helpers here by design.

This module is PURE (no DB, no network) so it is unit-testable in isolation.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Optional

# Confidence vocabulary shared with save_truth.py. Mirrors the FFT spine so the
# Inspector / regression tests speak one language across both games.
CONFIDENCE_VALUES = {"confirmed", "high", "medium", "low", "estimated", "unknown"}

# ── file0 layout ─────────────────────────────────────────────────────────────
# Only indices we are confident are documented and version-stable get a name.
# Index → (field_name, confidence). HP/level can shift slightly between editor
# tools, so they carry a lower confidence and are range-validated below.
#
# Indices 11/35/547 were promoted from "unknown" by tools/parser_expand.py, which
# corroborated each against a documented undertale.ini [General] key across a real
# 64-save corpus (Pacifist + Genocide) at 100% agreement — evidence, not a guess.
# They carry "high" (strong corpus corroboration; cross-source agreement at parse
# time promotes them to "confirmed"). file0[1]↔Love also reconfirmed 64/64.
FILE0_KNOWN_FIELDS: dict[int, tuple[str, str]] = {
    0: ("name", "confirmed"),   # the fallen human's name (the player-entered name)
    1: ("love", "confirmed"),   # LV — the "LOVE" stat (Level Of ViolencE)
    2: ("max_hp", "medium"),    # max HP; default 20 at LV 1, grows with LOVE
    11: ("kills", "high"),      # kill counter; mirrors [General].Kills (per-room in canon)
    35: ("fun", "high"),        # the "Fun value" RNG flag; mirrors [General].Fun (1–100)
    547: ("room", "high"),      # current room id; mirrors [General].Room
}

# Plausible ranges used purely to reject obviously-wrong reads (→ None), never to
# invent a value. LOVE caps at 20 in canon; HP can climb but stays modest.
LOVE_RANGE = (1, 99)
HP_RANGE = (1, 999)
KILLS_RANGE = (0, 999999)
FUN_RANGE = (0, 100)
ROOM_RANGE = (0, 100000)

# file0 fields that ALSO appear in undertale.ini [General] — checked against each
# other at parse time (cross-source corroboration). (parser_attr, ini_key).
CORROBORATED_FIELDS: tuple[tuple[str, str], ...] = (
    ("love", "love"),
    ("kills", "kills"),
    ("room", "room"),
    ("fun", "fun"),
)


@dataclass
class ParsedUndertaleSave:
    """The raw, honest read of an Undertale save. SaveTruth is built from this."""

    # Decoded, version-stable fields (any may be None when absent/implausible).
    name: Optional[str] = None
    love: Optional[int] = None
    max_hp: Optional[int] = None
    kills: Optional[int] = None
    fun: Optional[int] = None
    room: Optional[int] = None

    # Raw preserved structures — meaning NOT assigned, available for audit.
    file0_lines: list[str] = field(default_factory=list)
    ini_sections: dict[str, dict[str, str]] = field(default_factory=dict)

    # Per-field confidence so downstream code knows what it can trust.
    confidence: dict[str, str] = field(default_factory=dict)

    # Cross-source agreement: {field: {file0, ini, agree}} for fields recorded in
    # BOTH file0 and undertale.ini. The wall at the parser level — two independent
    # recordings either confirm each other or expose an edited save.
    corroboration: dict[str, Any] = field(default_factory=dict)

    # Non-fatal observations ("structure unexpected" → report, don't crash).
    warnings: list[str] = field(default_factory=list)

    # Source provenance (filenames, sizes, sha256) for the truth-audit trail.
    source: dict[str, Any] = field(default_factory=dict)

    def ini_get(self, section: str, key: str) -> Optional[str]:
        """Case-insensitive INI lookup; returns None when absent (never guessed)."""
        sec = self.ini_sections.get(section.lower())
        if not sec:
            return None
        return sec.get(key.lower())


def _coerce_int(raw: Optional[str], lo: int, hi: int) -> Optional[int]:
    """Parse an int in [lo, hi]; anything else → None (honest unknown, no guess)."""
    if raw is None:
        return None
    try:
        v = int(float(raw.strip()))
    except (TypeError, ValueError):
        return None
    return v if lo <= v <= hi else None


def parse_file0(text: str, save: ParsedUndertaleSave) -> None:
    """Decode the newline-delimited file0 into `save`, in place.

    Stores every line raw, then assigns meaning ONLY to documented indices.
    """
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    # Trailing blank line from a final newline is normal; drop a single one.
    if lines and lines[-1] == "":
        lines = lines[:-1]
    save.file0_lines = lines

    if len(lines) < 3:
        save.warnings.append(
            f"file0 has only {len(lines)} line(s); expected the documented save "
            "to be much longer. Reading what is present; rest left unknown."
        )

    for idx, (fieldname, conf) in FILE0_KNOWN_FIELDS.items():
        if idx >= len(lines):
            save.confidence[fieldname] = "unknown"
            continue
        raw = lines[idx]
        if fieldname == "name":
            name = (raw or "").strip()
            save.name = name or None
            save.confidence["name"] = conf if name else "unknown"
        elif fieldname == "love":
            v = _coerce_int(raw, *LOVE_RANGE)
            save.love = v
            save.confidence["love"] = conf if v is not None else "unknown"
            if v is None:
                save.warnings.append(
                    f"file0 line 1 (LOVE) was {raw!r}; not a plausible LV — left null."
                )
        elif fieldname == "max_hp":
            v = _coerce_int(raw, *HP_RANGE)
            save.max_hp = v
            save.confidence["max_hp"] = conf if v is not None else "unknown"
        elif fieldname in ("kills", "fun", "room"):
            # Corpus-corroborated mirrors of [General] keys. Absent/implausible →
            # None with no warning (same honest-silence policy as max_hp).
            ranges = {"kills": KILLS_RANGE, "fun": FUN_RANGE, "room": ROOM_RANGE}
            v = _coerce_int(raw, *ranges[fieldname])
            setattr(save, fieldname, v)
            save.confidence[fieldname] = conf if v is not None else "unknown"


def parse_undertale_ini(text: str, save: ParsedUndertaleSave) -> None:
    """Parse undertale.ini into lowercased {section: {key: value}} dicts.

    Tolerant by design: blank lines and comments are skipped, malformed lines are
    recorded as warnings rather than aborting the parse.
    """
    current: Optional[str] = None
    for lineno, raw in enumerate(text.split("\n"), start=1):
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().lower()
            save.ini_sections.setdefault(current, {})
            continue
        if "=" not in line:
            save.warnings.append(f"undertale.ini line {lineno}: no '=' — skipped ({line!r}).")
            continue
        if current is None:
            # Key/value before any [section] header — unusual but preserved.
            current = "_global"
            save.ini_sections.setdefault(current, {})
        key, _, value = line.partition("=")
        # Undertale stores INI values wrapped in double quotes.
        save.ini_sections[current][key.strip().lower()] = value.strip().strip('"')


def corroborate(save: ParsedUndertaleSave) -> None:
    """Cross-check file0-decoded fields against undertale.ini, in place.

    For every field recorded in BOTH sources, compare the two independent reads:
      - AGREE   → the strongest evidence we can have; promote confidence to
        "confirmed" and record the agreement.
      - DISAGREE→ the save is internally inconsistent (commonly an edited save).
        Keep the file0 (save-slot) value, downgrade confidence to "low", and emit
        a warning. We never silently pick a winner or average the two.
    Fields present in only one source are left as-is (nothing to corroborate).
    """
    for attr, ini_key in CORROBORATED_FIELDS:
        f0_val = getattr(save, attr, None)
        ini_raw = save.ini_get("general", ini_key)
        ini_val = _coerce_int(ini_raw, -(10 ** 9), 10 ** 9) if ini_raw is not None else None
        if f0_val is None or ini_val is None:
            continue
        agree = f0_val == ini_val
        save.corroboration[attr] = {"file0": f0_val, "ini": ini_val, "agree": agree}
        if agree:
            save.confidence[attr] = "confirmed"
        else:
            save.confidence[attr] = "low"
            save.warnings.append(
                f"{attr} disagrees across sources: file0={f0_val} vs "
                f"undertale.ini={ini_val}. Keeping the file0 (save-slot) value and "
                "flagging the conflict (often an edited save)."
            )


def _hash_and_size(path: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    if not path or not os.path.isfile(path):
        return None, None
    try:
        data = open(path, "rb").read()
        return len(data), hashlib.sha256(data).hexdigest()
    except OSError:
        return None, None


def parse_undertale_save(
    file0_path: Optional[str] = None,
    ini_path: Optional[str] = None,
    *,
    file0_text: Optional[str] = None,
    ini_text: Optional[str] = None,
) -> ParsedUndertaleSave:
    """Parse an Undertale save from file paths or in-memory text.

    At least one of (file0, undertale.ini) must be provided. Missing inputs are
    fine — the parser reports what it can and leaves the rest null.

    STOP+REPORT contract: if BOTH inputs are absent, that is an unexpected call
    and we surface it as a loud warning on an otherwise-empty parse rather than
    raising — callers (and the Inspector) can branch on `warnings`.
    """
    save = ParsedUndertaleSave()

    if file0_text is None and file0_path and os.path.isfile(file0_path):
        try:
            file0_text = open(file0_path, "r", encoding="utf-8", errors="replace").read()
        except OSError as e:
            save.warnings.append(f"could not read file0 at {file0_path}: {e}")
    if ini_text is None and ini_path and os.path.isfile(ini_path):
        try:
            ini_text = open(ini_path, "r", encoding="utf-8", errors="replace").read()
        except OSError as e:
            save.warnings.append(f"could not read undertale.ini at {ini_path}: {e}")

    if file0_text is not None:
        parse_file0(file0_text, save)
    if ini_text is not None:
        parse_undertale_ini(ini_text, save)

    # With both sources present, corroborate the overlapping fields against each
    # other (parser-level wall: confirm agreement / expose edited saves).
    if file0_text is not None and ini_text is not None:
        corroborate(save)

    if file0_text is None and ini_text is None:
        save.warnings.append(
            "STOP+REPORT: no file0 and no undertale.ini provided — nothing to parse. "
            "Structure is unexpected; refusing to invent any save facts."
        )

    f0_size, f0_hash = _hash_and_size(file0_path)
    ini_size, ini_hash = _hash_and_size(ini_path)
    save.source = {
        "game": "Undertale",
        "platform": "PC",
        "container": "undertale_save_dir",
        "file0_filename": os.path.basename(file0_path) if file0_path else None,
        "ini_filename": os.path.basename(ini_path) if ini_path else None,
        "file0_size_bytes": f0_size,
        "file0_sha256": f0_hash,
        "ini_size_bytes": ini_size,
        "ini_sha256": ini_hash,
    }
    return save
