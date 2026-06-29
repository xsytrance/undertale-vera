#!/usr/bin/env python3
"""SaveTruth for undertale-vera — the normalized boundary between parser bytes,
storage, prompts, and QA.

Ported pattern from fft-psx-vera/save_truth.py: a single versioned schema with a
`prompt_contract` block that the prompt builder and chat guardrails enforce. The
LLM may never override anything in here.

The FFT spine carried party/equipment/inventory/gold; undertale-vera carries
play-state + the morally-loaded ROUTE block instead. That is the only structural
difference — the discipline (confidence tags, unknown→null, save_truth_wins) is
identical.
"""
from __future__ import annotations

from typing import Any, Optional

from character_disposition import derive_dispositions
from route_detection import detect_route
from save_parser import CONFIDENCE_VALUES, ParsedUndertaleSave

SCHEMA_VERSION = "undertale-savetruth-v1"

# Fields the LLM is forbidden from inventing or overriding. Mirrors FFT's
# high_risk_fields but for Undertale's morally-loaded state.
HIGH_RISK_FIELDS = [
    "route.route",
    "play_state.love",
    "play_state.name",
    "kills.total",
]


def _confidence(value: Any, default: str = "unknown") -> str:
    return str(value) if value in CONFIDENCE_VALUES else default


def build_save_truth(
    parsed: Optional[ParsedUndertaleSave],
    source_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Normalize a ParsedUndertaleSave into the SaveTruth dict.

    `parsed` may be None (e.g. nothing uploaded yet) — we still return a
    well-formed, all-null truth so downstream code never has to special-case it.
    """
    if parsed is None:
        parsed = ParsedUndertaleSave()
        parsed.warnings.append("build_save_truth called with no parsed save.")

    route = detect_route(parsed)

    play_state = {
        "name": parsed.name,
        "love": parsed.love,            # LV — the "LOVE" stat
        "lv": parsed.love,              # alias; same value, common Undertale term
        "max_hp": parsed.max_hp,
        # Documented [General] keys, read by name; None when absent (never guessed).
        "room": _ini_int(parsed, "general", "room"),
        "room_name": parsed.ini_get("general", "roomname"),
        "play_time_frames": _ini_int(parsed, "general", "time"),
        "gold": _ini_int(parsed, "general", "gold"),
        "fun": _ini_int(parsed, "general", "fun"),
    }

    parser_confidence = {
        "name": _confidence(parsed.confidence.get("name")),
        "love": _confidence(parsed.confidence.get("love")),
        "max_hp": _confidence(parsed.confidence.get("max_hp")),
        "kills": _confidence(parsed.confidence.get("kills")),
        "fun": _confidence(parsed.confidence.get("fun")),
        "room": _confidence(parsed.confidence.get("room")),
        "route": _confidence(route.get("confidence")),
    }

    truth = {
        "schema_version": SCHEMA_VERSION,
        "source": {**(parsed.source or {}), **(source_meta or {})},
        "play_state": play_state,
        "kills": {
            "total": route.get("total_kills"),
            # Per-area breakdown is not parsed in Spine 0; explicitly null, not 0.
            "by_area": None,
        },
        "route": {
            "route": route["route"],
            "confidence": route["confidence"],
            "signals": route["signals"],
            "reasons": route["reasons"],
        },
        # Major-character spare/kill choices: determinable ones only; the rest are
        # honestly null. Spine 0 ships none as confirmed — never guessed.
        "choices": {
            "spared_everyone_so_far": (route["route"] == "Pacifist") or None,
        },
        # Per-character disposition (killed / spared / befriended / unknown), derived
        # from documented, corpus-corroborated ini flags. SACRED — never invented.
        "dispositions": derive_dispositions(parsed),
        "parser_confidence": parser_confidence,
        # Cross-source agreement (file0 vs undertale.ini) for overlapping fields.
        # Empty when only one source was provided. Two independent recordings that
        # AGREE are our strongest evidence; a DISAGREE flags a likely edited save.
        "corroboration": dict(parsed.corroboration),
        "warnings": list(parsed.warnings),
        "prompt_contract": {
            "save_truth_wins": True,
            "never_invent_route": True,
            "never_invent_kill_counts": True,
            "undetermined_means_undetermined": True,
            "high_risk_fields": HIGH_RISK_FIELDS,
        },
    }
    return truth


def _ini_int(parsed: ParsedUndertaleSave, section: str, key: str) -> Optional[int]:
    raw = parsed.ini_get(section, key)
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def validate_save_truth(save_truth: dict[str, Any]) -> dict[str, Any]:
    """Collect schema problems without ever throwing (FFT pattern).

    Returns {"valid": bool, "errors": [...], "warnings": [...]}.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if save_truth.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version mismatch: {save_truth.get('schema_version')!r} "
            f"!= {SCHEMA_VERSION!r}"
        )

    route = (save_truth.get("route") or {}).get("route")
    if route not in ("Pacifist", "Neutral", "Genocide", "undetermined"):
        errors.append(f"route {route!r} is not a recognized route value")

    contract = save_truth.get("prompt_contract") or {}
    if not contract.get("save_truth_wins"):
        errors.append("prompt_contract.save_truth_wins must be True")

    # A determined route with no signals would be an over-claim — flag it.
    if route in ("Pacifist", "Neutral", "Genocide"):
        if not (save_truth.get("route") or {}).get("signals"):
            warnings.append(
                f"route is {route!r} but no supporting signals were recorded; "
                "verify the derivation did not over-claim."
            )

    return {"valid": not errors, "errors": errors, "warnings": warnings}
