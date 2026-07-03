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
# Import-time fallbacks only: the live values come from _ollama_host()/_ollama_model()
# per call (GUI config wins over env) — tests should patch power_config or those.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

DEFAULT_MAX_TOKENS = 1024


def _backend() -> str:
    """Selected backend, read per-call so config/env changes (and tests) apply.

    The player's saved power choice (power_config) wins; the legacy env var is the
    fallback, so installs without a config behave exactly as before. "none" is the
    Spark rung: no model at all — every call degrades to the grounded fallback.
    """
    try:
        import power_config
        return power_config.source()
    except Exception:
        return os.environ.get("UNDERTALE_VERA_BACKEND", "ollama").strip().lower()


class LLMUnavailable(RuntimeError):
    """Raised when no model backend is reachable. Callers degrade gracefully."""


# ── Ollama (local) ───────────────────────────────────────────────────────────

def _ollama_host() -> str:
    """The Ollama host, read per-call: GUI config → env → default."""
    try:
        import power_config
        return power_config.ollama_host()
    except Exception:
        return OLLAMA_HOST


def _ollama_model() -> str:
    """The Ollama model, read per-call: GUI config → env → default."""
    try:
        import power_config
        return power_config.ollama_model()
    except Exception:
        return OLLAMA_MODEL


def list_ollama_models(host: str) -> list[str]:
    """The model tags installed on an Ollama server (GET {host}/api/tags).

    Powers the power picker's "Detect installed" button. Any failure — server
    down, wrong host, non-Ollama endpoint — raises LLMUnavailable so the caller
    reports honestly instead of 500ing.
    """
    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        raise LLMUnavailable("httpx not installed (needed for the Ollama backend)") from e
    timeout = httpx.Timeout(connect=3.0, read=6.0, write=6.0, pool=3.0)
    try:
        with httpx.Client(timeout=timeout) as http:
            resp = http.get(f"{host.rstrip('/')}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # noqa: BLE001 - transport/HTTP/JSON → honest error
        raise LLMUnavailable(f"Ollama not reachable at {host}: {e}") from e
    models = (data or {}).get("models") or []
    return [m["name"] for m in models if isinstance(m, dict) and m.get("name")]


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
        resp = http.post(f"{_ollama_host()}/api/chat", json=payload)
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
        "model": model or _ollama_model(),
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.6, "top_p": 0.85, "num_predict": max_tokens},
    }
    try:
        data = _ollama_chat(payload)
    except LLMUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - connection/HTTP/missing-model → degrade
        raise LLMUnavailable(f"Ollama unreachable at {_ollama_host()}: {e}") from e

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


# ── OpenRouter (bring-your-own-key; OpenAI-compatible) ───────────────────────

def _openrouter_chat(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """POST one chat completion to OpenRouter. Isolated for tests to monkeypatch."""
    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        raise LLMUnavailable("httpx not installed (needed for OpenRouter)") from e
    import power_config
    timeout = httpx.Timeout(connect=6.0, read=120.0, write=10.0, pool=6.0)
    with httpx.Client(timeout=timeout) as http:
        resp = http.post(
            power_config.OPENROUTER_URL,
            headers={"Authorization": f"Bearer {key}",
                     "HTTP-Referer": "https://github.com/xsytrance/undertale-vera",
                     "X-Title": "Ember"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


def _openrouter_reply(
    system_prompt: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, str]]],
    model: Optional[str],
    max_tokens: int,
) -> dict[str, Any]:
    import power_config
    key = power_config.openrouter_key()
    if not key:
        raise LLMUnavailable("no OpenRouter key configured")
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for turn in history or []:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})
    payload = {
        "model": model or power_config.openrouter_model(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }
    try:
        data = _openrouter_chat(payload, key)
    except LLMUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - auth/limits/transport → degrade
        raise LLMUnavailable(f"OpenRouter request failed: {e}") from e
    choices = (data or {}).get("choices") or []
    text = (choices[0].get("message") or {}).get("content", "") if choices else ""
    return {
        "text": text or "",
        "model": (data or {}).get("model", payload["model"]),
        "stop_reason": choices[0].get("finish_reason") if choices else None,
    }


# ── Custom (any OpenAI-compatible server: vLLM, LM Studio, llama.cpp) ────────

def _custom_chat(payload: dict[str, Any], base_url: str, key: Optional[str]) -> dict[str, Any]:
    """POST one chat completion to an OpenAI-compatible server. Isolated for tests."""
    try:
        import httpx
    except ImportError as e:  # pragma: no cover
        raise LLMUnavailable("httpx not installed (needed for the custom backend)") from e
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    timeout = httpx.Timeout(connect=6.0, read=120.0, write=10.0, pool=6.0)
    with httpx.Client(timeout=timeout) as http:
        resp = http.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def _custom_reply(
    system_prompt: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, str]]],
    model: Optional[str],
    max_tokens: int,
) -> dict[str, Any]:
    import power_config
    base_url = power_config.custom_base_url()
    if not base_url:
        raise LLMUnavailable("no custom backend URL configured")
    use_model = model or power_config.custom_model()
    if not use_model:
        raise LLMUnavailable("no model configured for the custom backend")
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for turn in history or []:
        role = turn.get("role")
        if role in ("user", "assistant") and turn.get("content"):
            messages.append({"role": role, "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})
    payload = {
        "model": use_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }
    try:
        data = _custom_chat(payload, base_url, power_config.custom_key())
    except LLMUnavailable:
        raise
    except Exception as e:  # noqa: BLE001 - auth/transport/wrong-endpoint → degrade
        raise LLMUnavailable(f"custom backend request failed: {e}") from e
    choices = (data or {}).get("choices") or []
    text = (choices[0].get("message") or {}).get("content", "") if choices else ""
    return {
        "text": text or "",
        "model": (data or {}).get("model", payload["model"]),
        "stop_reason": choices[0].get("finish_reason") if choices else None,
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
    if _backend() == "openrouter":
        return _openrouter_reply(
            system_prompt, user_message,
            history=history, model=model, max_tokens=max_tokens,
        )
    if _backend() == "custom":
        return _custom_reply(
            system_prompt, user_message,
            history=history, model=model, max_tokens=max_tokens,
        )
    if _backend() == "none":
        # Spark mode: deliberately model-less — the grounded fallback IS the voice.
        raise LLMUnavailable("power source is 'none' (Spark mode)")
    raise LLMUnavailable(f"unknown backend {_backend()!r}")
