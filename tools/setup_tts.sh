#!/usr/bin/env bash
# Set up Ember's local neural TTS (Kokoro) — the voice for Guided Mode read-aloud.
#
# Fully userspace: a dedicated python3.11 venv (.venv-tts, kept apart from the app's
# python3.14 venv) + the Kokoro-onnx model files under models/tts/. No root, no GPU
# required (CPU RTF ~0.12 on short lines). Re-run any time; it's idempotent.
#
# Windows note: this is the LINUX voice. On Windows the browser's built-in SAPI voices
# are used automatically (the frontend falls back), so no setup is needed there.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

PY="${TTS_PYTHON:-python3.11}"
command -v "$PY" >/dev/null || { echo "need $PY on PATH (set TTS_PYTHON=...)"; exit 1; }

echo "→ creating .venv-tts ($($PY --version 2>&1))"
[ -d .venv-tts ] || "$PY" -m venv .venv-tts
.venv-tts/bin/pip install --upgrade pip -q
echo "→ installing kokoro-onnx (CPU onnxruntime) + soundfile"
.venv-tts/bin/pip install -q kokoro-onnx soundfile onnxruntime

mkdir -p models/tts
BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
[ -f models/tts/kokoro-v1.0.onnx ] || { echo "→ downloading model (~310MB)"; curl -fSL -o models/tts/kokoro-v1.0.onnx "$BASE/kokoro-v1.0.onnx"; }
[ -f models/tts/voices-v1.0.bin ]  || { echo "→ downloading voices (~27MB)";  curl -fSL -o models/tts/voices-v1.0.bin  "$BASE/voices-v1.0.bin"; }

echo "→ smoke test"
echo "Read aloud is ready." | .venv-tts/bin/python tools/tts_synth.py --voice af_heart > /tmp/ember_tts_setup.wav
echo "✓ TTS installed. WAV: /tmp/ember_tts_setup.wav ($(du -h /tmp/ember_tts_setup.wav | cut -f1))"
echo "  Restart the app (systemctl --user restart ember-dev) and toggle 🔊 Read aloud in Guided Mode."
