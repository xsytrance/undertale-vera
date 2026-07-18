#!/usr/bin/env python3
"""Kokoro TTS one-shot synth — runs in the dedicated .venv-tts (python3.11).

The main Ember app (python3.14) can't import kokoro-onnx, so /api/tts shells out
to THIS script with the app's own interpreter path swapped for the TTS venv. Text
comes in on stdin; a WAV comes out on stdout. Grounded-safe by construction: it
speaks exactly the bytes it is given and invents nothing.

  echo "heya."  | .venv-tts/bin/python tools/tts_synth.py --voice am_onyx > out.wav
  .venv-tts/bin/python tools/tts_synth.py --list-voices        # JSON to stdout

Model files (gitignored, ~340MB) live under models/tts/ by default; override with
--model / --voices or the env vars EMBER_TTS_MODEL / EMBER_TTS_VOICES.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_MODEL = os.environ.get("EMBER_TTS_MODEL", os.path.join(HERE, "models/tts/kokoro-v1.0.onnx"))
DEF_VOICES = os.environ.get("EMBER_TTS_VOICES", os.path.join(HERE, "models/tts/voices-v1.0.bin"))


def _load(model: str, voices: str):
    from kokoro_onnx import Kokoro
    return Kokoro(model, voices)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--lang", default="en-us")
    ap.add_argument("--model", default=DEF_MODEL)
    ap.add_argument("--voices", default=DEF_VOICES)
    ap.add_argument("--list-voices", action="store_true")
    args = ap.parse_args()

    if args.list_voices:
        try:
            k = _load(args.model, args.voices)
            print(json.dumps(sorted(k.get_voices())))
            return 0
        except Exception as e:  # noqa: BLE001
            print(json.dumps({"error": str(e)}))
            return 1

    text = sys.stdin.read().strip()
    if not text:
        return 2
    # clamp speed to a sane band; the endpoint also caps text length
    speed = max(0.5, min(2.0, args.speed))
    try:
        import soundfile as sf
        k = _load(args.model, args.voices)
        samples, sr = k.create(text, voice=args.voice, speed=speed, lang=args.lang)
        buf = io.BytesIO()
        sf.write(buf, samples, sr, format="WAV")
        sys.stdout.buffer.write(buf.getvalue())
        return 0
    except Exception as e:  # noqa: BLE001 - surfaced to the endpoint via stderr + non-zero
        sys.stderr.write(str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
