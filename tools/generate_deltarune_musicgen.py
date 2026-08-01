#!/usr/bin/env python3
"""Generate Deltarune-adjacent instrumental loop beds with MusicGen via Transformers.

Outputs exact MP3 filenames under static/audio. Designed to resume: skips files that
already have a corresponding .musicgen.done marker unless --force is used.
"""
from __future__ import annotations

import argparse
import gc
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

TRACKS = [
    ("dark-world.mp3", "Mysterious wondrous dark-fantasy chiptune instrumental loop, deep velvet synth pads in violet minor, delicate music-box arpeggios echoing in a vast dark hall, soft choir pad swells, falling into a storybook world, slow 76 BPM, B minor, majestic strange inviting, seamless video game background music, no vocals"),
    ("char-susie.mp3", "Grungy swaggering chiptune rock instrumental loop, crunchy distorted synth riff over stomping drums, cocky strutting bassline, rough edge softening into unexpectedly warm bridge, mid-tempo 112 BPM, D minor, tough-kid energy with hidden heart, seamless video game character theme, no vocals"),
    ("char-ralsei.mp3", "Tender storybook chiptune waltz instrumental loop, soft music box and warm felt piano in 3/4, gentle fluffy pads, shy hopeful melody like friendship, 90 BPM waltz, F major, cozy and a little lonely, seamless video game character theme, no vocals"),
    ("char-lancer.mp3", "Mischievous bouncy villain chiptune instrumental loop, jaunty circus-adjacent bassline, cheeky staccato square-wave melody that trips over itself, kazoo-like synth honks, playful 132 BPM, G major, kid playing at being evil, seamless video game character theme, no vocals"),
    ("char-noelle.mp3", "Soft wintry chiptune lullaby instrumental loop, glassy bell tones and warm pads like snowfall, shy tender melody with tiny hesitations, faint sleigh-bell shimmer, slow 80 BPM, A major with wistful minor turns, gentle nervous kind, seamless video game character theme, no vocals"),
    ("char-king.mp3", "Ominous regal dark chiptune instrumental loop, heavy slow brass-like synth stabs over doom-laden bass pulse, grieving minor melody beneath menace, distant thunder drum hits, slow 66 BPM, C minor, betrayed king on a high throne, seamless video game boss ambience, no vocals"),
    ("char-rouxls-kaard.mp3", "Pompous baroque-flavored chiptune instrumental loop, harpsichord-style synth flourishes and overwrought fanfares, strutting bassline, melody far too pleased with itself with comic stumbles, 120 BPM, D major, magnificently self-important, seamless video game character theme, no vocals"),
    ("char-jevil.mp3", "Manic carousel waltz chiptune instrumental loop, demented calliope and circus organ spinning in accelerating 3/4, cackling high synth runs, off-kilter accents changing the downbeat, fast unstable 150 BPM, D minor, gleeful unhinged freedom, seamless video game character theme, no vocals"),
    ("char-seam.mp3", "Dusty melancholic curiosity-shop chiptune instrumental loop, detuned music box and creaking slow waltz, threadbare warm pads with vinyl crackle, tired knowing melody that has seen endings, slow 70 BPM, E minor, cozy dread, seamless video game shop theme, no vocals"),
]


def equal_power_loop_crossfade(x: np.ndarray, sr: int, fade_s: float = 1.5) -> np.ndarray:
    """Fold the tail into the head with equal-power crossfade for cleaner looping."""
    if x.ndim == 1:
        x = x[:, None]
    n = len(x)
    fade = min(int(sr * fade_s), max(1, n // 6))
    if fade <= 1:
        return x.squeeze()
    head = x[:fade].copy()
    tail = x[-fade:].copy()
    t = np.linspace(0, 1, fade, endpoint=False)[:, None]
    a = np.cos(t * np.pi / 2)
    b = np.sin(t * np.pi / 2)
    y = x[:-fade].copy()
    y[:fade] = tail * a + head * b
    return y.squeeze()


def normalize(x: np.ndarray, peak: float = 0.92) -> np.ndarray:
    m = float(np.max(np.abs(x))) if x.size else 0.0
    if m > 1e-8:
        x = x * (peak / m)
    return np.clip(x, -0.99, 0.99)


def encode_mp3(wav: Path, mp3: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(wav),
        "-codec:a", "libmp3lame", "-b:a", "192k",
        str(mp3),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="/home/xsyprime/undertale-vera/static/audio")
    ap.add_argument("--model", default="facebook/musicgen-small")
    ap.add_argument("--duration", type=float, default=24.0)
    ap.add_argument("--max-tracks", type=int, default=0, help="0 = all")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    workdir = outdir / ".musicgen_work"
    workdir.mkdir(exist_ok=True)

    print(f"Loading {args.model} on {args.device}...")
    processor = AutoProcessor.from_pretrained(args.model)
    dtype = torch.float16 if args.device.startswith("cuda") else torch.float32
    model = MusicgenForConditionalGeneration.from_pretrained(args.model, torch_dtype=dtype)
    model.to(args.device)
    model.eval()

    sr = int(model.config.audio_encoder.sampling_rate)
    # MusicGen EnCodec is ~50 tokens/sec.
    max_new_tokens = int(args.duration * 50)
    tracks = TRACKS if args.max_tracks <= 0 else TRACKS[: args.max_tracks]

    for idx, (fname, prompt) in enumerate(tracks, 1):
        mp3 = outdir / fname
        marker = outdir / f".{fname}.musicgen.done"
        if marker.exists() and mp3.exists() and not args.force:
            print(f"[{idx}/{len(tracks)}] skip existing {fname}")
            continue
        print(f"[{idx}/{len(tracks)}] generating {fname}: {prompt[:90]}...")
        inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(args.device)
        with torch.inference_mode():
            audio_values = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                guidance_scale=3.0,
                temperature=1.0,
                top_k=250,
            )
        audio = audio_values[0, 0].detach().float().cpu().numpy()
        audio = normalize(equal_power_loop_crossfade(audio, sr, fade_s=1.25))
        wav = workdir / fname.replace(".mp3", ".wav")
        sf.write(wav, audio, sr)
        encode_mp3(wav, mp3)
        marker.write_text(f"model={args.model}\nduration={args.duration}\nprompt={prompt}\n", encoding="utf-8")
        print(f"saved {mp3}")
        del inputs, audio_values, audio
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print("done")


if __name__ == "__main__":
    main()
