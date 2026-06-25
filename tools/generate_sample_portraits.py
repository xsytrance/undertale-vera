#!/usr/bin/env python3
"""Generate 2-3 SAMPLE relic-framed portraits for the Determination Chronicle.

Two modes:

  --comfy   Drive the real ComfyUI pixel-portrait pipeline
            (comfy_workflows/portrait_undertale.json) against a running ComfyUI
            at $COMFY_URL. Produces the actual pixel portraits with the new
            Undertale style LoRA. Use this when a ComfyUI box is available.

  (default) Render local PLACEHOLDER relic frames with Pillow — a quick proof
            that the "museum-lit relic frame + reinterpreted soul-sigil" framing
            renders, for Egi's review. These are NOT the final pixel portraits;
            they stand in until a ComfyUI run produces the real ones.

All outputs land in static/assets/portraits/ which is GITIGNORED — we never
batch-commit generated art (only the pipeline + this script are committed).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(HERE, "static", "assets", "portraits")
WORKFLOW = os.path.join(HERE, "comfy_workflows", "portrait_undertale.json")

SAMPLE_CHARACTERS = ["sans", "toriel", "flowey"]


def render_placeholder(slug: str) -> str:
    """Render a placeholder relic-framed portrait (obsidian + brass + soul sigil)."""
    from PIL import Image, ImageDraw

    size = 512
    obsidian = (12, 11, 16)
    plate_inner = (34, 29, 24)
    brass = (185, 147, 63)
    brass_edge = (216, 183, 101)
    ember = (232, 162, 76)

    img = Image.new("RGBA", (size, size), obsidian + (255,))
    d = ImageDraw.Draw(img)

    # museum-lit vignette warmth at the top
    for y in range(size):
        t = max(0.0, 1.0 - (y / (size * 0.7)))
        warm = (
            int(obsidian[0] + (plate_inner[0] - obsidian[0]) * t),
            int(obsidian[1] + (plate_inner[1] - obsidian[1]) * t),
            int(obsidian[2] + (plate_inner[2] - obsidian[2]) * t),
        )
        d.line([(0, y), (size, y)], fill=warm + (255,))

    # relic frame
    margin = 36
    d.rectangle([margin, margin, size - margin, size - margin], outline=brass, width=6)
    d.rectangle([margin + 10, margin + 10, size - margin - 10, size - margin - 10],
                outline=brass_edge, width=2)

    # reinterpreted soul = faceted ember-gem lozenge (NOT a heart), museum-lit center
    cx, cy, r = size // 2, size // 2 - 10, 70
    gem = [(cx, cy - r), (cx + int(r * 0.78), cy - int(r * 0.12)),
           (cx, cy + r), (cx - int(r * 0.78), cy - int(r * 0.12))]
    d.polygon(gem, fill=ember + (235,), outline=brass_edge + (255,))

    # engraved name plate
    name = slug.capitalize()
    d.rectangle([margin, size - margin - 56, size - margin, size - margin - 18],
                fill=plate_inner + (255,), outline=brass + (255,), width=1)
    d.text((cx - 4 * len(name), size - margin - 46), name.upper(), fill=brass_edge + (255,))
    d.text((margin + 14, margin + 8), "PLACEHOLDER · DETERMINATION CHRONICLE", fill=(120, 110, 92, 255))

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{slug}.png")
    img.save(path)
    return path


def render_via_comfy(slug: str) -> str:  # pragma: no cover - needs a live ComfyUI
    """POST the workflow to ComfyUI. Requires a running ComfyUI at $COMFY_URL."""
    import urllib.request

    comfy_url = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
    with open(WORKFLOW) as f:
        graph = json.load(f)
    graph = {k: v for k, v in graph.items() if not k.startswith("_")}
    # Inject the character into the positive prompt.
    graph["3"]["inputs"]["text"] = (
        f"determination_chronicle_style, pixel art character portrait, {slug} of the "
        "Underground, bust framing, museum-lit, warm ember and brass rim light, deep "
        "obsidian background, expressive face, looking at viewer"
    )
    payload = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{comfy_url}/prompt", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read())
    print(f"  queued {slug}: {out.get('prompt_id')}")
    return f"(queued in ComfyUI as {out.get('prompt_id')})"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate sample relic portraits")
    ap.add_argument("--comfy", action="store_true", help="drive a live ComfyUI instead of placeholders")
    args = ap.parse_args()

    for slug in SAMPLE_CHARACTERS:
        if args.comfy:
            print(render_via_comfy(slug))
        else:
            print("rendered placeholder:", render_placeholder(slug))
    return 0


if __name__ == "__main__":
    sys.exit(main())
