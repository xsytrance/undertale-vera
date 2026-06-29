#!/usr/bin/env python3
"""Route detection — the moral spine of undertale-vera.

NORTH STAR: Undertale's save is morally-loaded state. The route a player is on
(Pacifist / Neutral / Genocide) is the single most consequential fact downstream,
because characters' grounding hinges on it. So this module is held to the strictest
parser-truth standard:

  - The route is DERIVED from real, observed save signals (LOVE, EXP, kill counts,
    documented flags) — never assumed.
  - When the available signals are absent or contradictory, the route is
    "undetermined". We NEVER guess a route to fill a blank. A wrong route breaks
    immersion (and trust) faster than an honest "I can't tell yet".

This is a PURE function module (no DB, no network) so the logic is unit-testable
and the Inspector can replay it deterministically.

A note on honesty / scope (documented in docs/SAVE_FORMAT.md): fully *canonical*
route certainty — especially confirming a completed Genocide run — depends on
area-clear flags whose exact undertale.ini indices vary across game versions. This
detector uses a conservative, documented subset (LOVE, total kills, and named ini
keys when present) and is explicit about its confidence. It will say "Neutral"
or "undetermined" rather than over-claim "Genocide".
"""
from __future__ import annotations

from typing import Any, Optional

ROUTES = ("Pacifist", "Neutral", "Genocide", "undetermined")

# LOVE thresholds. LV 1 means zero EXP gained (no kills). LV 20 is only reachable
# by killing essentially everything — the Genocide ceiling.
LOVE_NO_KILLS = 1
LOVE_GENOCIDE_CEILING = 20

# Documented major-character KILL flags from undertale.ini. Each is a hard,
# binary record that a specific boss was killed — community-documented (TK =
# "Toriel killed", PK = "Papyrus killed") AND corpus-corroborated: across a real
# 64-save corpus these were set in 0/49 no-kill (Pacifist) runs and only ever in
# Genocide saves. Their presence is therefore an UNAMBIGUOUS "violence occurred"
# signal — it cannot coexist with a true no-kill run. (section, key, character).
# Allow-list is intentionally conservative + extensible; only corpus-confirmed
# kill flags belong here, never a guessed one.
KILL_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("toriel", "tk", "Toriel"),
    ("papyrus", "pk", "Papyrus"),
)

# Documented BEFRIEND / DATE flags — the canonical True Pacifist requirements
# (date Papyrus, date Undyne, date Alphys). Corpus-corroborated: set in 37/49
# Pacifist saves and 0/15 Genocide (the Undyne date is gated behind a no-kill run,
# so these literally cannot occur on a kill route). Their presence is what
# distinguishes an ACTIVE Pacifist/befriend path from a passive no-kill Neutral —
# the exact signal whose absence forced the old medium cap. (section, key, character).
BEFRIEND_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("papyrus", "pd", "Papyrus"),
    ("undyne", "ud", "Undyne"),
    ("alphys", "ad", "Alphys"),
)

# Mutually-exclusive (spare, kill) flag pairs per character. A real run cannot both
# spare AND kill the same monster, so both set at once is an edited/contradictory
# save. (section, spare_key, kill_key, character).
SPARE_KILL_PAIRS: tuple[tuple[str, str, str, str], ...] = (
    ("toriel", "ts", "tk", "Toriel"),
    ("papyrus", "ps", "pk", "Papyrus"),
)


def _maybe_int(v: Any) -> Optional[int]:
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError, AttributeError):
        return None


def extract_kill_signals(parsed) -> dict[str, Any]:
    """Pull kill-related signals out of a ParsedUndertaleSave, honestly.

    Returns total kills (or None) plus the raw ini keys we consulted, so the
    grounding can show its work. Never fabricates a count.
    """
    total = None
    consulted: list[str] = []
    # The [General] Kills counter resets per-room in canon, but its presence and
    # a non-zero value is still a real, observed signal. We read it if present.
    for section, key in (("general", "kills"), ("general", "kill"), ("flags", "kills")):
        raw = parsed.ini_get(section, key) if hasattr(parsed, "ini_get") else None
        if raw is not None:
            consulted.append(f"[{section}] {key}={raw}")
            v = _maybe_int(raw)
            if v is not None:
                total = v if total is None else total + v
    return {"total_kills": total, "consulted": consulted}


def extract_kill_flags(parsed) -> list[dict[str, Any]]:
    """Documented boss-kill flags that are SET (present and non-zero) in the save.

    Each returned flag is a hard, version-stable record that a major character was
    killed. Reads undertale.ini by name; never inferred, never guessed.
    """
    found: list[dict[str, Any]] = []
    if not hasattr(parsed, "ini_get"):
        return found
    for section, key, character in KILL_FLAGS:
        raw = parsed.ini_get(section, key)
        if raw is None:
            continue
        val = _maybe_int(raw)
        if val not in (None, 0):
            found.append({"section": section, "key": key, "character": character, "raw": raw})
    return found


def extract_befriend_flags(parsed) -> list[dict[str, Any]]:
    """Documented befriend/date flags that are SET — the True Pacifist requirements.

    Each is a hard record that the protagonist dated/befriended a character, which
    is only reachable on a no-kill path. Read by name; never inferred.
    """
    found: list[dict[str, Any]] = []
    if not hasattr(parsed, "ini_get"):
        return found
    for section, key, character in BEFRIEND_FLAGS:
        raw = parsed.ini_get(section, key)
        if raw is None:
            continue
        if _maybe_int(raw) not in (None, 0):
            found.append({"section": section, "key": key, "character": character, "raw": raw})
    return found


def find_spare_kill_conflicts(parsed) -> list[str]:
    """Characters whose SPARE and KILL flags are both set — an impossible pair."""
    conflicts: list[str] = []
    if not hasattr(parsed, "ini_get"):
        return conflicts
    for section, spare_key, kill_key, character in SPARE_KILL_PAIRS:
        sp, kl = parsed.ini_get(section, spare_key), parsed.ini_get(section, kill_key)
        if sp is not None and kl is not None and \
                _maybe_int(sp) not in (None, 0) and _maybe_int(kl) not in (None, 0):
            conflicts.append(character)
    return conflicts


def detect_route(parsed) -> dict[str, Any]:
    """Derive the route block for SaveTruth from a ParsedUndertaleSave.

    Output shape:
      {
        "route": one of ROUTES,
        "confidence": confidence string,
        "love": int|None,        # the real LOVE that drove the call
        "total_kills": int|None,
        "signals": [...],        # the real fields/flags we used
        "reasons": [...],        # plain-language justification (auditable)
      }
    """
    love = getattr(parsed, "love", None)
    kills = extract_kill_signals(parsed)
    total_kills = kills["total_kills"]
    kill_flags = extract_kill_flags(parsed)
    flag_chars = [f["character"] for f in kill_flags]
    has_kill_flag = bool(kill_flags)
    befriend_flags = extract_befriend_flags(parsed)
    befriend_chars = [f["character"] for f in befriend_flags]
    spare_kill_conflicts = find_spare_kill_conflicts(parsed)
    signals: list[str] = []
    reasons: list[str] = []

    if love is not None:
        signals.append(f"LOVE={love}")
    signals.extend(kills["consulted"])
    for f in kill_flags:
        signals.append(f"[{f['section']}] {f['key']}={f['raw']} ({f['character']} killed)")
    for f in befriend_flags:
        signals.append(f"[{f['section']}] {f['key']}={f['raw']} ({f['character']} befriended/dated)")

    # CONTRADICTION: a character marked BOTH spared and killed — impossible in a real
    # run. Refuse to derive a route over self-contradicting facts (an edited save).
    if spare_kill_conflicts:
        who = ", ".join(spare_kill_conflicts)
        return {
            "route": "undetermined", "confidence": "low", "love": love,
            "total_kills": total_kills, "signals": signals,
            "reasons": [
                f"{who} is recorded as BOTH spared and killed — these flags are "
                "mutually exclusive in a real run (an edited save). Refusing to guess "
                "a route over contradictory facts; left undetermined."
            ],
        }

    # No usable signal at all → undetermined. This is the honest default.
    if love is None and total_kills is None:
        return {
            "route": "undetermined",
            "confidence": "unknown",
            "love": None,
            "total_kills": None,
            "signals": signals,
            "reasons": [
                "No LOVE value and no kill counter could be read from the save; "
                "the route cannot be derived and is left undetermined."
            ],
        }

    # CONTRADICTION GUARD (verified against a real save-editor corpus): when LOVE
    # and the recorded kill count point in OPPOSITE directions, the save is
    # internally inconsistent (often an edited save). The honest answer is
    # "undetermined" — we refuse to pick a route over self-contradicting facts.
    if love == LOVE_GENOCIDE_CEILING and total_kills == 0:
        reasons.append(
            "LOVE is maxed at 20 (only reachable by near-total killing), yet the "
            "recorded kill count is 0 — these signals contradict (often an edited "
            "save). Refusing to guess a route; left undetermined."
        )
        return _result("undetermined", "low", love, total_kills, signals, reasons)
    if love == LOVE_NO_KILLS and isinstance(total_kills, int) and total_kills > 0:
        reasons.append(
            f"LOVE is 1 (no EXP ever gained), yet {total_kills} kills are recorded — "
            "these signals contradict (often an edited save or a per-area counter). "
            "Refusing to guess a route; left undetermined."
        )
        return _result("undetermined", "low", love, total_kills, signals, reasons)
    if has_kill_flag and love == LOVE_NO_KILLS:
        reasons.append(
            f"LOVE is 1 (no EXP ever gained), yet a documented boss-kill flag is set "
            f"({', '.join(flag_chars)} killed) — killing a boss raises LOVE, so these "
            "cannot both hold honestly (an edited save). Left undetermined, not guessed."
        )
        return _result("undetermined", "low", love, total_kills, signals, reasons)

    # LV 20 is the Genocide ceiling — only reachable by near-total killing. (Kills
    # here is >0 or unknown; the contradictory Kills==0 case was handled above.)
    if love == LOVE_GENOCIDE_CEILING:
        reasons.append(
            "LOVE is at the maximum of 20, which is only reachable by killing "
            "nearly every monster — consistent with a Genocide route."
        )
        if has_kill_flag:
            # Maxed LOVE *and* documented boss kills — two independent records of
            # total slaughter. This is the one case we'll call Genocide "confirmed".
            reasons.append(
                f"Documented boss-kill flags are also set ({', '.join(flag_chars)} "
                "killed), independently corroborating the maxed LOVE — Genocide, confirmed."
            )
            return _result("Genocide", "confirmed", love, total_kills, signals, reasons)
        return _result("Genocide", "high", love, total_kills, signals, reasons)

    # LV 1 with no kills observed → a confirmed no-kill run. This is necessary
    # (but not by itself sufficient) for True Pacifist, so we cap confidence at
    # medium and say so, rather than over-claiming the befriend/date flags.
    if love == LOVE_NO_KILLS and (total_kills in (0, None)):
        reasons.append(
            "LOVE is 1 (no EXP ever gained) and no kills are recorded — a no-kill "
            "run, consistent with a Pacifist route."
        )
        if befriend_flags:
            # Documented date/befriend flags are present — these are reachable ONLY
            # on a no-kill path, so they distinguish an active TRUE Pacifist route
            # from a passive no-kill Neutral. That resolves the old ambiguity → high.
            reasons.append(
                f"Befriend/date flags are recorded ({', '.join(befriend_chars)}) — "
                "these are only reachable on a no-kill path and separate a TRUE "
                "Pacifist route from a no-kill Neutral run, so confidence is high."
            )
            return _result("Pacifist", "high", love, total_kills, signals, reasons)
        reasons.append(
            "Note: a no-kill NEUTRAL run also matches this; confirming TRUE Pacifist "
            "additionally requires befriend/date flags, none of which are recorded "
            "yet, so confidence is held at medium."
        )
        return _result("Pacifist", "medium", love, total_kills, signals, reasons)

    # Any LOVE above 1 (and below the ceiling), or recorded kills, means the run
    # has spilled blood but is not a confirmed full Genocide — that is Neutral.
    if (love is not None and love > LOVE_NO_KILLS) or (total_kills not in (0, None)) or has_kill_flag:
        reasons.append(
            "Some killing has occurred (LOVE above 1, recorded kills, and/or a boss-"
            "kill flag) but not the total clearance that defines Genocide — consistent "
            "with a Neutral route."
        )
        if has_kill_flag:
            reasons.append(
                f"Boss-kill flags are set ({', '.join(flag_chars)} killed) — this "
                "removes any doubt that killing occurred, but is not by itself the "
                "full clearance Genocide requires, so the route is held at Neutral."
            )
        if love is not None and love >= 15:
            reasons.append(
                "LOVE is unusually high; this leans toward Genocide but is not "
                "confirmed without area-clear flags — kept as Neutral, not guessed up."
            )
        return _result("Neutral", "medium", love, total_kills, signals, reasons)

    # Signals exist but don't fit a clear pattern → be honest.
    return {
        "route": "undetermined",
        "confidence": "low",
        "love": love,
        "total_kills": total_kills,
        "signals": signals,
        "reasons": [
            "Observed signals do not match a clear route pattern; left undetermined "
            "rather than guessed."
        ],
    }


def _result(route, confidence, love, total_kills, signals, reasons) -> dict[str, Any]:
    return {
        "route": route,
        "confidence": confidence,
        "love": love,
        "total_kills": total_kills,
        "signals": signals,
        "reasons": reasons,
    }
