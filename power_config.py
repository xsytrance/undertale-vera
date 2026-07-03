#!/usr/bin/env python3
"""The power source — which brain (if any) Ember runs on, chosen by the player.

One app, a capability ladder:
  🕯 "none"       — Spark mode: no LLM at all; every feature serves its grounded
                    deterministic response. Zero setup, honest, instant.
  🔑 "openrouter" — bring-your-own-key (OpenRouter's OpenAI-compatible API), with
                    curated free/cheap model suggestions.
  🖥 "ollama"     — a local model server (the full-fat default). Host + model are
                    GUI-configurable; the config wins over OLLAMA_HOST/OLLAMA_MODEL.
  🔌 "custom"     — any OpenAI-compatible server (vLLM, LM Studio, llama.cpp):
                    a base URL + model name, plus an optional key.
  ☁ "anthropic"  — Anthropic's Claude (needs ANTHROPIC_API_KEY in the env).

The choice persists in a small gitignored JSON config next to the DB (chmod 600 —
it can hold an API key). The config, when present, WINS over the legacy
UNDERTALE_VERA_BACKEND env var; with no config, env behaviour is unchanged, so
existing installs keep working untouched.

PURE-ish module (filesystem only; no network).
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

CONFIG_PATH = os.environ.get("UNDERTALE_VERA_POWER_CONFIG", "./ember_power.json")

SOURCES = ("none", "openrouter", "ollama", "anthropic", "custom")

OLLAMA_DEFAULT_HOST = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_MODEL = "llama3.1:8b"

# Curated OpenRouter suggestions — honest notes, editable in the UI (any model id
# works). Prices drift; these are safe, well-known picks rather than promises.
OPENROUTER_SUGGESTIONS = [
    {"id": "meta-llama/llama-3.1-8b-instruct:free", "label": "Llama 3.1 8B (free tier)",
     "note": "free — rate-limited, fine for chat"},
    {"id": "deepseek/deepseek-chat", "label": "DeepSeek Chat",
     "note": "very cheap, strong quality"},
    {"id": "google/gemini-flash-1.5", "label": "Gemini Flash",
     "note": "cheap and fast"},
    {"id": "anthropic/claude-haiku-4.5", "label": "Claude Haiku 4.5",
     "note": "inexpensive, excellent voice"},
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load() -> dict[str, Any]:
    """The saved power config; {} when none exists (env behaviour then applies)."""
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(cfg: dict[str, Any]) -> None:
    """Persist the power choice (key material included → owner-only file mode)."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def edition() -> str:
    """lite = the zero-setup public edition (Spark-locked, trimmed nav)."""
    e = os.environ.get("EMBER_EDITION", "pro").strip().lower()
    return e if e in ("lite", "pro") else "pro"


def locked() -> bool:
    """Shared deployments fix the power source server-side: a visitor's key
    would otherwise power every other visitor's chats."""
    return os.environ.get("EMBER_POWER_LOCK", "").strip() in ("1", "true", "yes")


def visitor_scope() -> bool:
    """EMBER_VISITOR_SCOPE=1 — the multi-visitor scoping flag for shared sites."""
    return os.environ.get("EMBER_VISITOR_SCOPE", "").strip() in ("1", "true", "yes")


def shared() -> bool:
    """True when visitors share this deployment, so the power source must never
    be steerable from a browser: a visitor's key would power strangers' chats,
    and a visitor's host URL would aim server-side requests. The lite edition
    and visitor-scoped sites are shared by construction (no flag to forget);
    EMBER_POWER_LOCK declares any other deployment shared. A self-hosted
    single-player install (none of the three set) is unaffected."""
    return locked() or visitor_scope() or edition() == "lite"


def pro_url() -> str:
    """Where the lite edition points the curious ("want the full thing?")."""
    return os.environ.get("EMBER_PRO_URL", "").strip()


def source() -> str:
    """The active source: the config wins; else the legacy env var; else ollama.
    The lite edition is Spark by construction — no model, no picker."""
    if edition() == "lite":
        return "none"
    cfg = load()
    s = (cfg.get("source") or "").strip().lower()
    if s in SOURCES:
        return s
    return os.environ.get("UNDERTALE_VERA_BACKEND", "ollama").strip().lower()


def openrouter_key() -> Optional[str]:
    return load().get("openrouter_key") or os.environ.get("OPENROUTER_API_KEY") or None


def openrouter_model() -> str:
    return load().get("openrouter_model") or OPENROUTER_SUGGESTIONS[0]["id"]


def ollama_host() -> str:
    h = load().get("ollama_host") or os.environ.get("OLLAMA_HOST") or OLLAMA_DEFAULT_HOST
    return h.strip().rstrip("/")


def ollama_model() -> str:
    return load().get("ollama_model") or os.environ.get("OLLAMA_MODEL") or OLLAMA_DEFAULT_MODEL


def custom_base_url() -> Optional[str]:
    u = load().get("custom_base_url") or os.environ.get("EMBER_CUSTOM_BASE_URL") or ""
    return u.strip().rstrip("/") or None


def custom_model() -> Optional[str]:
    return load().get("custom_model") or os.environ.get("EMBER_CUSTOM_MODEL") or None


def custom_key() -> Optional[str]:
    return load().get("custom_key") or os.environ.get("EMBER_CUSTOM_API_KEY") or None


def _mask(k: Optional[str]) -> Optional[str]:
    if not k:
        return None
    return (k[:7] + "…" + k[-4:]) if len(k) > 14 else "set"


def masked_key() -> Optional[str]:
    return _mask(openrouter_key())


def masked_custom_key() -> Optional[str]:
    return _mask(custom_key())


def public_state() -> dict[str, Any]:
    """What the UI may see — keys are never returned, only masked; on a shared
    site no config details at all (visitors get the source, not the wiring)."""
    state: dict[str, Any] = {
        "source": source(),
        "edition": edition(),
        "locked": shared(),
        "pro_url": pro_url(),
        "configured": bool(load()),
        "suggestions": OPENROUTER_SUGGESTIONS,
    }
    if shared():
        state.update({k: None for k in (
            "openrouter_model", "openrouter_key", "ollama_host", "ollama_model",
            "custom_base_url", "custom_model", "custom_key")})
    else:
        state.update({
            "openrouter_model": openrouter_model(),
            "openrouter_key": masked_key(),
            "ollama_host": ollama_host(),
            "ollama_model": ollama_model(),
            "custom_base_url": custom_base_url(),
            "custom_model": custom_model(),
            "custom_key": masked_custom_key(),
        })
    return state
