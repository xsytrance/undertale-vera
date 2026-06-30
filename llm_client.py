#!/usr/bin/env python3
"""LLM client for grounded character chat — local Ollama or Anthropic Claude.

Ported from the FFT spine's pattern (one mockable call, graceful degradation).
Two backends, chosen by `UNDERTALE_VERA_BACKEND`:

  - "ollama"   (default) — a local Ollama server, exactly as fft-psx-vera uses it:
                POST {OLLAMA_HOST}/api/chat, model {OLLAMA_MODEL}. No API key.
  - "anthropic"          — Anthropic's Claude Messages API (needs ANTHROPIC_API_KEY).

Design rules carried from the FFT spine:
  - ONE public function the endpoint calls (`generate_reply`).
  - Fully mockable: SDK/httpx imported lazily so the module loads without them;
    tests patch `generate_reply` (or the small `_ollama_chat` / `client` seams)
    rather than hitting the network.
  - Any backend failure (no key, no model, no connection) raises LLMUnavailable so
    the caller degrades to a grounded deterministic reply — never a 500.
"""
from __future__ import annotations

import os
from typing import Any, Optional

# Anthropic (cloud) — default model per the project's "latest Claude" guidance.
ANTHROPIC_MODEL = os.environ.get("UNDERTALE_VERA_MODEL", "claude-opus-4-8")

# Ollama (local) — same defaults as the sibling app fft-psx-vera, so a machine
# already running that stack works with no extra configuration.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://100.110.224.126:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

DEFAULT_MAX_TOKENS = 1024


def _backend() -> str:
    """Selected backend, read per-call so env changes (and tests) take effect."""
    return os.environ.get("UNDERTALE_VERA_BACKEND", "ollama").strip().lower()


class LLMUnavailable(RuntimeError):
    """Raised when no model backend is reachable. Callers degrade gracefully."""


# ── Ollama (local) ───────────────────────────────────────────────────────────

def _ollama_chat(payload: dict[str, Any]) -> dict[str, Any]:
    """POST one /api/chat request to Ollama and return parsed JSON.

    Isolated so tests can monkeypatch it without touching the network. Raises on a
    missing httpx, transport error, or non-2xx response.
    """
    try:
        import httpx  # lazy: the module imports even without httpx installed
    except ImportError as e:  # pragma: no cover - exercised only without the dep
        raise LLMUnavailable("httpx not installed (needed for the Ollama backend)") from e
    # Short connect timeout (fail fast when the server is down) but a generous read
    # timeout (local models can be slow to generate).
    timeout = httpx.Timeout(connect=4.0, read=120.0, write=10.0, pool=4.0)
    with httpx.Client(timeout=timeout) as http:
        resp = http.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


def _ollama_reply(
    system_prompt: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, str]]],
    model: Optional[str],
    max_tokens: int,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for turn in history or []:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.6, "top_p": 0.85, "num_predict": max_tokens},
    }
    try:
        data = _ollama_chat(payload)
    except LLMUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - connection/HTTP/missing-model → degrade
        raise LLMUnavailable(f"Ollama unreachable at {OLLAMA_HOST}: {e}") from e

    text = ((data or {}).get("message") or {}).get("content", "") or ""
    return {
        "text": text,
        "model": (data or {}).get("model", payload["model"]),
        "stop_reason": (data or {}).get("done_reason"),
    }


# ── Anthropic (cloud) ────────────────────────────────────────────────────────

def _make_client():
    """Lazily construct an Anthropic client.

    A missing SDK *or* unset/invalid credentials both surface as LLMUnavailable so
    the caller degrades gracefully — running with no ANTHROPIC_API_KEY must yield a
    grounded deterministic reply, never a 500.
    """
    try:
        import anthropic  # imported lazily so the module loads without the SDK
    except ImportError as e:  # pragma: no cover - exercised only without the dep
        raise LLMUnavailable("anthropic SDK not installed") from e
    try:
        # Raises (e.g. AnthropicError) when ANTHROPIC_API_KEY is not set.
        return anthropic.Anthropic()
    except Exception as e:  # noqa: BLE001 - any construction failure → degrade
        raise LLMUnavailable(f"Anthropic client unavailable: {e}") from e


def _anthropic_reply(
    system_prompt: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, str]]],
    model: Optional[str],
    max_tokens: int,
    client: Any,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    for turn in history or []:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    cli = client or _make_client()
    try:
        resp = cli.messages.create(
            model=model or ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
            # Adaptive thinking + effort is the current API surface for Opus 4.8.
            thinking={"type": "adaptive"},
            output_config={"effort": "low"},
        )
    except LLMUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - auth/connection/rate-limit → degrade
        raise LLMUnavailable(f"Anthropic request failed: {e}") from e

    text = ""
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            text += getattr(block, "text", "")
    return {
        "text": text,
        "model": getattr(resp, "model", model or ANTHROPIC_MODEL),
        "stop_reason": getattr(resp, "stop_reason", None),
    }


# ── public entry point ───────────────────────────────────────────────────────

def generate_reply(
    system_prompt: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, str]]] = None,
    model: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    client: Any = None,
) -> dict[str, Any]:
    """Generate one in-character reply via the selected backend.

    Returns {"text": str, "model": str, "stop_reason": str|None}. An injected
    `client` forces the Anthropic path (tests pass a stub there). Production passes
    None and dispatches on UNDERTALE_VERA_BACKEND (default "ollama").

    The system_prompt carries the two-bucket wall (sacred SaveTruth + free voice);
    this function does not re-ground — it only relays.
    """
    if client is not None or _backend() == "anthropic":
        return _anthropic_reply(
            system_prompt, user_message,
            history=history, model=model, max_tokens=max_tokens, client=client,
        )
    if _backend() == "ollama":
        return _ollama_reply(
            system_prompt, user_message,
            history=history, model=model, max_tokens=max_tokens,
        )
    raise LLMUnavailable(f"unknown UNDERTALE_VERA_BACKEND {_backend()!r}")
