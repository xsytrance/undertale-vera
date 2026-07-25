#!/usr/bin/env python3
"""Generate the installable-app icons — OUR OWN art, drawn from geometry.

The app installs as a real desktop app (see static/manifest.webmanifest), which
needs icons. These are drawn programmatically from the ember-gem sigil in
docs/ART_DIRECTION.md — a faceted lozenge in the MultiVera palette.

Deliberately NOT the game's SOUL sprite: icons are committed, and extracted
game art never enters the repo. The sigil is our own mark, which is exactly
what an app icon should be. It also stays correct under the authentic skin,
where the in-app SOUL swaps to the real sprite but the *application's* identity
shouldn't change out from under the user.

    python3 tools/make_app_icons.py

Writes static/icons/. Small, deterministic, and committed — rerunning produces
identical bytes, so it never shows up as spurious diff noise.
"""
from __future__ import annotations

import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - environment guard
    sys.exit("Pillow is required:  pip install Pillow")

OBSIDIAN = (12, 11, 16, 255)
EMBER = (232, 162, 76)
EMBER_SOFT = (214, 138, 62)
BRASS = (184, 147, 63)

#: (size, filename, padding fraction). "Maskable" icons must keep their art
#: inside a safe circle, because Windows and Android crop them to a platform
#: shape — so that one gets extra padding rather than a different drawing.
TARGETS = (
    (192, "icon-192.png", 0.18),
    (512, "icon-512.png", 0.18),
    (512, "icon-512-maskable.png", 0.30),
)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_icon(size: int, pad: float) -> Image.Image:
    """The ember-gem sigil: a faceted lozenge, lit from upper-left."""
    # supersample, then downscale — cheap, reliable antialiasing on the facets
    ss = 4
    n = size * ss
    img = Image.new("RGBA", (n, n), OBSIDIAN)
    d = ImageDraw.Draw(img)

    # a warm floor glow so the gem sits in a field rather than on a flat plate
    cx, cy = n / 2, n * 0.46
    for i in range(28, 0, -1):
        t = i / 28
        r = n * 0.52 * t
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=lerp(OBSIDIAN[:3], (46, 32, 18), (1 - t) * 0.5) + (255,))

    inset = n * pad
    w = n - inset * 2
    # the lozenge from ART_DIRECTION.md: 50% 0, 88% 38, 50% 100, 12% 38
    top = (inset + w * 0.50, inset)
    right = (inset + w * 0.88, inset + w * 0.38)
    bottom = (inset + w * 0.50, inset + w)
    left = (inset + w * 0.12, inset + w * 0.38)

    # two facets, split down the vertical axis, so the gem reads as faceted
    # rather than as a flat diamond
    d.polygon([top, right, bottom], fill=lerp(EMBER_SOFT, BRASS, 0.55) + (255,))
    d.polygon([top, left, bottom], fill=lerp(EMBER, EMBER_SOFT, 0.25) + (255,))

    # a bright edge along the lit side
    d.line([left, top], fill=lerp(EMBER, (255, 255, 255), 0.45) + (255,),
           width=max(2, n // 128))
    d.line([top, right], fill=BRASS + (255,), width=max(2, n // 160))

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(repo, "static", "icons")
    os.makedirs(out, exist_ok=True)
    for size, name, pad in TARGETS:
        path = os.path.join(out, name)
        draw_icon(size, pad).save(path, optimize=True)
        print(f"  {name:<24} {size}x{size}  {os.path.getsize(path):>6}B")
    print(f"\nwrote {len(TARGETS)} icons to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
