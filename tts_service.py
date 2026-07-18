"""Server-side neural TTS (Kokoro) — the local voice for Guided Mode read-aloud.

Why server-side: Linux browsers have no built-in speech voices (Chrome's Web Speech
API needs a system speech-dispatcher backend), so Ember synthesizes audio itself and
plays it in ANY browser/OS — Prime, a phone over Tailscale, the same everywhere. On
Windows (built-in SAPI voices) the frontend can still fall back to the browser engine
if this service isn't present.

Kokoro-onnx runs in a DEDICATED python3.11 venv (.venv-tts) because the main app is
python3.14; we shell out to tools/tts_synth.py with that interpreter. ~1s cold per
short line on CPU (RTF ~0.12), no GPU or root required.

Grounded-safe: this reads exactly the text it's handed (already-grounded reactions,
hints, stories). It is presentation only — it never invents or changes a word.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Optional

HERE = os.path.dirname(os.path.abspath(__file__))
TTS_PY = os.environ.get("EMBER_TTS_PY", os.path.join(HERE, ".venv-tts/bin/python"))
MODEL = os.environ.get("EMBER_TTS_MODEL", os.path.join(HERE, "models/tts/kokoro-v1.0.onnx"))
VOICES = os.environ.get("EMBER_TTS_VOICES", os.path.join(HERE, "models/tts/voices-v1.0.bin"))
SCRIPT = os.path.join(HERE, "tools/tts_synth.py")

MAX_CHARS = 1200          # a hard cap: reactions/hints are short; nobody narrates a novel
SYNTH_TIMEOUT = 30        # seconds

# A voice per character, so the cast sounds like itself. Kokoro's English voices:
# af_/am_ = American female/male, bf_/bm_ = British female/male. These are chosen
# for flavour (Sans low and dry, Papyrus bright, Asgore a deep king…); the user can
# override with a single voice in the panel. Unknown speakers fall to the default.
CHARACTER_VOICES = {
    "Sans": "am_onyx", "Papyrus": "am_puck", "Toriel": "af_heart",
    "Undyne": "af_bella", "Alphys": "af_nicole", "Flowey": "am_echo",
    "Asgore": "bm_george", "Mettaton": "bm_fable", "Napstablook": "am_liam",
    # Deltarune
    "Susie": "af_alloy", "Ralsei": "bf_lily", "Kris": "am_adam",
    "Noelle": "af_jessica", "Lancer": "am_fenrir",
}
DEFAULT_VOICE = "af_heart"

_voices_cache: Optional[list] = None


def available() -> bool:
    """True when the TTS venv interpreter and both model files are present."""
    return os.path.isfile(TTS_PY) and os.path.isfile(MODEL) and os.path.isfile(VOICES)


def list_voices() -> list:
    """Voice ids the installed model exposes (cached). [] if unavailable."""
    global _voices_cache
    if _voices_cache is not None:
        return _voices_cache
    if not available():
        _voices_cache = []
        return _voices_cache
    try:
        out = subprocess.run(
            [TTS_PY, SCRIPT, "--list-voices", "--model", MODEL, "--voices", VOICES],
            capture_output=True, timeout=SYNTH_TIMEOUT,
        )
        data = json.loads(out.stdout.decode("utf-8", "replace") or "[]")
        _voices_cache = data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        _voices_cache = []
    return _voices_cache


def voice_for(character: Optional[str], override: Optional[str]) -> str:
    """Resolve the voice: an explicit override wins; else the character's; else default."""
    if override and override in set(list_voices()):
        return override
    if character and character in CHARACTER_VOICES:
        return CHARACTER_VOICES[character]
    return DEFAULT_VOICE


class TTSUnavailable(RuntimeError):
    pass


def synth(text: str, voice: Optional[str] = None, speed: float = 1.0) -> bytes:
    """Synthesize `text` to WAV bytes. Raises TTSUnavailable on any failure."""
    if not available():
        raise TTSUnavailable("TTS engine not installed")
    t = (text or "").strip()
    if not t:
        raise TTSUnavailable("empty text")
    t = t[:MAX_CHARS]
    v = voice if (voice and voice in set(list_voices())) else DEFAULT_VOICE
    try:
        speed = max(0.5, min(2.0, float(speed)))
    except (TypeError, ValueError):
        speed = 1.0
    try:
        proc = subprocess.run(
            [TTS_PY, SCRIPT, "--voice", v, "--speed", str(speed),
             "--model", MODEL, "--voices", VOICES],
            input=t.encode("utf-8"), capture_output=True, timeout=SYNTH_TIMEOUT,
        )
    except subprocess.TimeoutExpired as e:
        raise TTSUnavailable("synth timed out") from e
    except Exception as e:  # noqa: BLE001
        raise TTSUnavailable(str(e)) from e
    if proc.returncode != 0 or not proc.stdout:
        raise TTSUnavailable(proc.stderr.decode("utf-8", "replace")[:200] or "synth failed")
    return proc.stdout


def health() -> dict:
    """A small status object for the frontend to decide server-vs-browser voice."""
    ok = available()
    return {
        "available": ok,
        "engine": "kokoro" if ok else None,
        "voices": list_voices() if ok else [],
        "character_voices": CHARACTER_VOICES,
        "default_voice": DEFAULT_VOICE,
    }
