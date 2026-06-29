#!/usr/bin/env python3
"""LLM client for grounded character chat — Anthropic Claude.

The FFT spine talked to a local Ollama model over httpx. We port the *pattern*
(one mockable call, graceful degradation) but target Anthropic's Claude per the
project's "default to the latest, most capable Claude models" guidance.

Design rules carried from the FFT spine:
  - ONE public function the endpoint calls.
  - Fully mockable in tests — the `anthropic` package is imported lazily so the
    module imports even when the SDK isn't installed, and tests patch
    `generate_reply` (or the client) rather than hitting the network.

Model defaults to claude-opus-4-8. Uses the Messages API with adaptive thinking
and the `effort` control (NOT the removed `budget_tokens` parameter).
"""
from __future__ import annotations

import os
from typing import Any, Optional

DEFAULT_MODEL = os.environ.get("UNDERTALE_VERA_MODEL", "claude-opus-4-8")
DEFAULT_MAX_TOKENS = 1024


class LLMUnavailable(RuntimeError):
    """Raised when no model backend is reachable. Callers degrade gracefully."""


def _make_client():
    """Lazily construct an Anthropic client. Import errors → LLMUnavailable."""
    try:
        import anthropic  # imported lazily so the module loads without the SDK
    except ImportError as e:  # pragma: no cover - exercised only without the dep
        raise LLMUnavailable("anthropic SDK not installed") from e
    return anthropic.Anthropic()


def generate_reply(
    system_prompt: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, str]]] = None,
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    client: Any = None,
) -> dict[str, Any]:
    """Generate one in-character reply.

    Returns {"text": str, "model": str, "stop_reason": str|None}. The `client`
    argument lets tests inject a stub; production passes None and we build one.

    The system_prompt carries the two-bucket wall (sacred SaveTruth + free voice);
    this function does not re-ground — it only relays.
    """
    model = model or DEFAULT_MODEL
    messages: list[dict[str, Any]] = []
    for turn in history or []:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    cli = client or _make_client()
    resp = cli.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
        # Adaptive thinking + effort is the current API surface for Opus 4.8.
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
    )

    text = ""
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            text += getattr(block, "text", "")

    return {
        "text": text,
        "model": getattr(resp, "model", model),
        "stop_reason": getattr(resp, "stop_reason", None),
    }
