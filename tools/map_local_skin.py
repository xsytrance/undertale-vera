#!/usr/bin/env python3
"""Map extracted game sprites into the app's asset slots (authentic local skin).

Second half of the local-skin pipeline:

    tools/extract_undertale_assets.py   data.win  → static/assets/local/sprites/…
    tools/map_local_skin.py             sprites/… → static/assets/local/{emblems,portraits,scenes}/

The resolvers (`avatar_resolver`, `scene_resolver`) already look in those three
directories first when ``UNDERTALE_VERA_SKIN=authentic`` — so this script needs
no app changes. Its whole job is picking WHICH sprite fills each slot.

**The output is gitignored and stays local.** Only this mapping is committed.
See ``docs/LOCAL_SKIN_MANIFEST.md`` for the rationale behind each pick.

    python3 tools/map_local_skin.py            # fill every slot
    python3 tools/map_local_skin.py --preview  # + a contact sheet to eyeball
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover - environment guard
    sys.exit("Pillow is required:  pip install Pillow")


# ── the slot map ─────────────────────────────────────────────────────────────
# app character slug → (sprite folder, frame index)
#
# Three naming conventions coexist in the archive, which is why these look
# inconsistent: the main cast uses `spr_face_<name>`, several others use
# `spr_<name>face_N`, and a couple have no dialogue portrait at all (Flowey,
# Napstablook) so their overworld sprite stands in.
CHARACTER_SLOTS: dict[str, tuple[str, int]] = {
    "sans":        ("spr_face_sans",       0),
    "papyrus":     ("spr_face_papyrus",    0),
    "toriel":      ("spr_face_torieltalk", 0),   # no plain `spr_face_toriel`
    "undyne":      ("spr_face_undyne0",    0),
    "alphys":      ("spr_alphysface_0",    0),
    "asgore":      ("spr_asgore_face0",    0),
    "mettaton":    ("spr_mettface_general", 0),
    "flowey":      ("spr_flowey",          0),   # overworld — no face sprite
    "napstablook": ("spr_napstablook_d",   0),   # overworld — no face sprite
}

# UI furniture → a stable filename `css/authentic.css` can reference. These get
# no black-keying and no upscaling: they're tiny and the CSS scales them with
# `image-rendering: pixelated`, which keeps the pixel grid exact at any size.
UI_SLOTS: dict[str, tuple[str, int]] = {
    "soul":        ("spr_heart",      0),   # the real SOUL, replacing our sigil
    "soul_broken": ("spr_heartbreak", 0),
    "savepoint":   ("spr_savepoint",  0),
}

# route → background. Chosen for MOOD, matching docs/ART_DIRECTION.md's brief:
# atmospheric, no text, no UI. Easy to re-point — that's why this is a table.
SCENE_SLOTS: dict[str, str] = {
    "pacifist":     "bg_endingview",       # the surface — warm, hopeful
    "neutral":      "bg_firstroom",        # where every run begins — unresolved
    "genocide":     "bg_core_distance",    # dim, industrial, still, wrong
    "undetermined": "bg_tb",               # murk — unknowable
}

#: Slots also get a portrait copy, so the chat bubble and the relic frame agree.
PORTRAIT_SIZE = 256
EMBLEM_SIZE = 128


def key_black(img: Image.Image, threshold: int = 24) -> Image.Image:
    """Make the near-black backing transparent.

    Dialogue portraits are drawn as light line-art on a solid black plate —
    correct in-game, where the dialogue box is black, but a hard rectangle
    against our obsidian UI. Dropping the plate leaves the linework floating,
    which is how it reads in the game anyway.
    """
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a and r <= threshold and g <= threshold and b <= threshold:
                px[x, y] = (r, g, b, 0)
    return img


def fit(img: Image.Image, size: int) -> Image.Image:
    """Scale onto a square canvas with NEAREST, preserving the pixel grid."""
    img = img.convert("RGBA")
    if img.width == 0 or img.height == 0:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    scale = max(1, min(size // max(img.width, 1), size // max(img.height, 1)))
    scaled = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    if scaled.width > size or scaled.height > size:
        scaled.thumbnail((size, size), Image.NEAREST)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(scaled, ((size - scaled.width) // 2,
                          (size - scaled.height) // 2), scaled)
    return canvas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="local asset root")
    ap.add_argument("--keep-plate", action="store_true",
                    help="keep the black dialogue plate behind portraits")
    ap.add_argument("--preview", action="store_true",
                    help="also write a contact sheet of every filled slot")
    args = ap.parse_args()

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = args.root or os.path.join(repo, "static", "assets", "local")
    src = os.path.join(root, "sprites")
    if not os.path.isdir(src):
        sys.exit(f"no extracted sprites at {src}\n"
                 f"run: python3 tools/extract_undertale_assets.py")

    emblem_dir = os.path.join(root, "emblems")
    portrait_dir = os.path.join(root, "portraits")
    scene_dir = os.path.join(root, "scenes")
    for d in (emblem_dir, portrait_dir, scene_dir):
        os.makedirs(d, exist_ok=True)

    filled: list[tuple[str, Image.Image]] = []
    missing: list[str] = []

    for slug, (sprite, frame) in sorted(CHARACTER_SLOTS.items()):
        path = os.path.join(src, sprite, f"{frame:02d}.png")
        if not os.path.isfile(path):
            missing.append(f"{slug}: {sprite}/{frame:02d}.png")
            continue
        img = Image.open(path).convert("RGBA")
        if not args.keep_plate:
            img = key_black(img)
        fit(img, EMBLEM_SIZE).save(os.path.join(emblem_dir, f"{slug}.png"))
        portrait = fit(img, PORTRAIT_SIZE)
        portrait.save(os.path.join(portrait_dir, f"{slug}.png"))
        filled.append((slug, portrait))
        print(f"  {slug:<12} ← {sprite}")

    print()
    ui_dir = os.path.join(root, "ui")
    os.makedirs(ui_dir, exist_ok=True)
    for name, (sprite, frame) in sorted(UI_SLOTS.items()):
        path = os.path.join(src, sprite, f"{frame:02d}.png")
        if not os.path.isfile(path):
            missing.append(f"ui/{name}: {sprite}/{frame:02d}.png")
            continue
        Image.open(path).convert("RGBA").save(os.path.join(ui_dir, f"{name}.png"))
        print(f"  ui/{name:<9} ← {sprite}")

    print()
    for route, bg in sorted(SCENE_SLOTS.items()):
        path = os.path.join(root, "backgrounds", f"{bg}.png")
        if not os.path.isfile(path):
            missing.append(f"{route}: backgrounds/{bg}.png")
            continue
        Image.open(path).convert("RGBA").save(os.path.join(scene_dir, f"{route}.png"))
        print(f"  {route:<12} ← {bg}")

    if missing:
        print("\nUNFILLED (slot keeps its committed original art):")
        for m in missing:
            print(f"  {m}")

    if args.preview and filled:
        pad = 12
        w = sum(i.width + pad for _, i in filled) + pad
        h = max(i.height for _, i in filled) + pad * 2
        sheet = Image.new("RGBA", (w, h), (12, 11, 16, 255))
        x = pad
        for _, img in filled:
            sheet.paste(img, (x, pad), img)
            x += img.width + pad
        out = os.path.join(root, "_preview_slots.png")
        sheet.save(out)
        print(f"\npreview → {out}")

    print(f"\n{len(filled)} character slots, "
          f"{len(SCENE_SLOTS) - sum(1 for m in missing if not m.startswith(tuple(CHARACTER_SLOTS)))} "
          f"scene slots filled under {root}")
    print("REMINDER: gitignored — never commit or deploy this art.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
