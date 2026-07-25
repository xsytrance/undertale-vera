#!/usr/bin/env python3
"""Extract sprites, backgrounds and fonts from a GameMaker ``data.win``.

Reads the OWNER'S OWN installed copy of the game and writes the art into
``static/assets/local/`` for the private "authentic" skin
(``UNDERTALE_VERA_SKIN=authentic`` — see ``local_skin.py``).

**The output of this script is never committed and never deployed.**
``static/assets/local/`` is gitignored. The game's art belongs to its creators;
this is a local re-skin of a personal tool, on a machine that owns the game.
Re-run it per machine instead of copying the output around.

Pure stdlib + Pillow. No .NET, no UndertaleModTool, no network.

    # what's in there (writes nothing)
    python3 tools/extract_undertale_assets.py --list

    # extract everything
    python3 tools/extract_undertale_assets.py

    # iterate on one slot
    python3 tools/extract_undertale_assets.py --only 'spr_sans*'

Container format (IFF-style, GameMaker Studio 1.4):

    FORM <len>
      GEN8 …   header: game name, version
      SPRT …   sprite defs — name + frames, each frame → a TPAG index
      BGND …   backgrounds — name + one TPAG index
      FONT …   fonts — name + glyph metrics + one TPAG index
      TPAG …   texture-page entries: source rect + target offset + bounds
      TXTR …   the texture atlases, as embedded PNG blobs
      STRG …   the string table every name resolves through

Each chunk that holds a list is: ``count:u32`` then ``count`` absolute u32 file
offsets. Sprite frames index into TPAG; TPAG entries index into TXTR.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import struct
import sys
from typing import Any, Optional

try:
    from PIL import Image
except ImportError:  # pragma: no cover - environment guard
    sys.exit("Pillow is required:  pip install Pillow")


# ── candidate install locations ──────────────────────────────────────────────
# Ordered; first hit with a data.win wins. Covers Linux Steam (native + snap)
# and Windows Steam, so the same command works on Prime and on the ROG Ally.
GAME_DIR_CANDIDATES = (
    "~/.local/share/Steam/steamapps/common/Undertale",
    "~/.steam/steam/steamapps/common/Undertale",
    "~/snap/steam/common/.local/share/Steam/steamapps/common/Undertale",
    "~/.local/share/Steam/steamapps/common/DELTARUNE",
    "~/.steam/steam/steamapps/common/DELTARUNE",
    r"C:\Program Files (x86)\Steam\steamapps\common\Undertale",
    r"C:\Program Files (x86)\Steam\steamapps\common\DELTARUNE",
    r"D:\SteamLibrary\steamapps\common\Undertale",
    r"D:\SteamLibrary\steamapps\common\DELTARUNE",
)

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# Steam's own record of every library root, including secondary drives. Reading
# it matters on the handheld, where games usually live on a microSD rather than
# any path we could hardcode.
STEAM_ROOTS = (
    "~/.local/share/Steam", "~/.steam/steam",
    "~/snap/steam/common/.local/share/Steam",
    r"C:\Program Files (x86)\Steam",
)
GAME_FOLDERS = ("Undertale", "UNDERTALE", "DELTARUNE", "Deltarune")


def steam_library_dirs() -> list[str]:
    """Every Steam library root listed in libraryfolders.vdf."""
    out: list[str] = []
    for root in STEAM_ROOTS:
        vdf = os.path.join(os.path.expanduser(root), "steamapps", "libraryfolders.vdf")
        if not os.path.isfile(vdf):
            continue
        try:
            with open(vdf, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        # entries look like:   "path"    "/media/sdcard/SteamLibrary"
        for m in re.finditer(r'"path"\s+"([^"]+)"', text):
            path = m.group(1).replace("\\\\", "\\")
            if path not in out:
                out.append(path)
    return out


def find_game_dir(explicit: Optional[str] = None) -> str:
    """Locate the game install, or exit with the list of places we looked."""
    if explicit:
        path = os.path.abspath(os.path.expanduser(explicit))
        if not os.path.isfile(os.path.join(path, "data.win")):
            sys.exit(f"no data.win in {path}")
        return path

    tried: list[str] = []
    for cand in GAME_DIR_CANDIDATES:
        path = os.path.expanduser(cand)
        tried.append(path)
        if os.path.isfile(os.path.join(path, "data.win")):
            return path

    # secondary libraries (microSD on the handheld, second drive on a desktop)
    for lib in steam_library_dirs():
        for folder in GAME_FOLDERS:
            path = os.path.join(lib, "steamapps", "common", folder)
            tried.append(path)
            if os.path.isfile(os.path.join(path, "data.win")):
                return path

    sys.exit(
        "could not find a game install. Pass --game-dir /path/to/game.\nLooked in:\n  "
        + "\n  ".join(tried)
    )


# ── the reader ───────────────────────────────────────────────────────────────

class DataWin:
    """A parsed ``data.win``: chunk table, string table, texture pages, sprites."""

    def __init__(self, path: str) -> None:
        with open(path, "rb") as fh:
            self.buf = fh.read()
        self.path = path
        self.chunks: dict[str, tuple[int, int]] = {}   # name -> (offset, length)
        self.strings: dict[int, str] = {}              # char-data offset -> text
        self._read_form()
        self._read_strings()

    # -- primitives --
    def u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.buf, off)[0]

    def u16(self, off: int) -> int:
        return struct.unpack_from("<H", self.buf, off)[0]

    def i16(self, off: int) -> int:
        return struct.unpack_from("<h", self.buf, off)[0]

    def pointer_list(self, chunk: str) -> list[int]:
        """The ``count`` + ``count×u32 offsets`` list every chunk here starts with."""
        if chunk not in self.chunks:
            return []
        off, _ = self.chunks[chunk]
        count = self.u32(off)
        return [self.u32(off + 4 + 4 * i) for i in range(count)]

    def string_at(self, ptr: int) -> str:
        """Resolve a string reference (points at char data; length precedes it)."""
        if ptr in self.strings:
            return self.strings[ptr]
        if ptr <= 4 or ptr >= len(self.buf):
            return ""
        length = self.u32(ptr - 4)
        if length > 4096:
            return ""
        return self.buf[ptr:ptr + length].decode("utf-8", "replace")

    # -- chunk walk --
    def _read_form(self) -> None:
        if self.buf[:4] != b"FORM":
            sys.exit(f"{self.path} is not a GameMaker FORM archive")
        end = 8 + self.u32(4)
        pos = 8
        while pos < end and pos + 8 <= len(self.buf):
            name = self.buf[pos:pos + 4].decode("latin1")
            length = self.u32(pos + 4)
            self.chunks[name] = (pos + 8, length)
            pos += 8 + length

    def _read_strings(self) -> None:
        for ptr in self.pointer_list("STRG"):
            # the pointer addresses the length field; chars start 4 bytes in
            length = self.u32(ptr)
            if length > 4096:
                continue
            data = self.buf[ptr + 4:ptr + 4 + length]
            self.strings[ptr + 4] = data.decode("utf-8", "replace")

    @property
    def game_name(self) -> str:
        if "GEN8" not in self.chunks:
            return "unknown"
        off, _ = self.chunks["GEN8"]
        return self.string_at(self.u32(off + 8)) or "unknown"

    # -- textures --
    def texture_pages(self) -> list[Image.Image]:
        """Decode every atlas in TXTR into a Pillow image (RGBA)."""
        pages: list[Image.Image] = []
        for ptr in self.pointer_list("TXTR"):
            # GMS 1.4 entry: u32 scaled, u32 offset-of-PNG-blob
            blob_off = self.u32(ptr + 4)
            if self.buf[blob_off:blob_off + 8] != PNG_MAGIC:
                # some builds add fields before the blob pointer; scan a little
                found = self.buf.find(PNG_MAGIC, ptr, ptr + 64)
                blob_off = found if found != -1 else blob_off
            length = self._png_length(blob_off)
            if length <= 0:
                pages.append(Image.new("RGBA", (1, 1)))
                continue
            import io
            img = Image.open(io.BytesIO(self.buf[blob_off:blob_off + length]))
            pages.append(img.convert("RGBA"))
        return pages

    def _png_length(self, off: int) -> int:
        """Exact byte length of the PNG at ``off`` (walk chunks to IEND)."""
        if self.buf[off:off + 8] != PNG_MAGIC:
            return -1
        pos = off + 8
        while pos + 8 <= len(self.buf):
            clen = struct.unpack_from(">I", self.buf, pos)[0]
            ctype = self.buf[pos + 4:pos + 8]
            pos += 12 + clen          # length + type + data + crc
            if ctype == b"IEND":
                return pos - off
        return -1

    # -- texture page entries --
    def tpag_entries(self) -> dict[int, dict[str, int]]:
        """{file offset: rect} for every TPAG entry (11 × u16 = 22 bytes)."""
        out: dict[int, dict[str, int]] = {}
        for ptr in self.pointer_list("TPAG"):
            out[ptr] = {
                "src_x": self.u16(ptr), "src_y": self.u16(ptr + 2),
                "src_w": self.u16(ptr + 4), "src_h": self.u16(ptr + 6),
                "dst_x": self.u16(ptr + 8), "dst_y": self.u16(ptr + 10),
                "dst_w": self.u16(ptr + 12), "dst_h": self.u16(ptr + 14),
                "bound_w": self.u16(ptr + 16), "bound_h": self.u16(ptr + 18),
                "tex_id": self.u16(ptr + 20),
            }
        return out

    # -- sprites --
    def sprites(self) -> list[dict[str, Any]]:
        """Every sprite: name, size, origin, and its frames' TPAG offsets."""
        out: list[dict[str, Any]] = []
        for ptr in self.pointer_list("SPRT"):
            # +0 name, +4 w, +8 h, +12..+24 margins, +28 transparent, +32 smooth,
            # +36 preload, +40 bboxmode, +44 sepmasks, +48/+52 origin,
            # +56 frame count, +60.. frame → TPAG offsets.
            name = self.string_at(self.u32(ptr))
            width, height = self.u32(ptr + 4), self.u32(ptr + 8)
            origin_x, origin_y = self.u32(ptr + 48), self.u32(ptr + 52)
            count = self.u32(ptr + 56)
            # GMS2 marks special sprite types with a -1 sentinel here; those
            # carry no plain frame list, so record them rather than misread.
            if count == 0xFFFFFFFF or count > 4096:
                out.append({"name": name, "width": width, "height": height,
                            "origin": [origin_x, origin_y], "frames": [],
                            "special": True})
                continue
            frames = [self.u32(ptr + 60 + 4 * i) for i in range(count)]
            out.append({"name": name, "width": width, "height": height,
                        "origin": [origin_x, origin_y], "frames": frames,
                        "special": False})
        return out

    # -- backgrounds --
    def backgrounds(self) -> list[dict[str, Any]]:
        """Room backdrops: name + one TPAG offset."""
        out: list[dict[str, Any]] = []
        for ptr in self.pointer_list("BGND"):
            out.append({"name": self.string_at(self.u32(ptr)),
                        "frame": self.u32(ptr + 16)})
        return out

    # -- fonts --
    def fonts(self) -> list[dict[str, Any]]:
        """Fonts: name, face, size, and the TPAG offset of the glyph sheet."""
        out: list[dict[str, Any]] = []
        for ptr in self.pointer_list("FONT"):
            out.append({
                "name": self.string_at(self.u32(ptr)),
                "face": self.string_at(self.u32(ptr + 4)),
                "size": self.u32(ptr + 8),
                "bold": bool(self.u32(ptr + 12)),
                "italic": bool(self.u32(ptr + 16)),
                "frame": self.u32(ptr + 28),
            })
        return out


# ── rendering ────────────────────────────────────────────────────────────────

def render_frame(pages: list[Image.Image], rect: dict[str, int],
                 *, trim: bool = False) -> Optional[Image.Image]:
    """Rebuild one frame: crop the atlas rect, place it on the bounding canvas.

    The atlas stores sprites tightly packed with whitespace stripped; ``dst_x``/
    ``dst_y`` say where that crop sits inside the sprite's true ``bound_w`` ×
    ``bound_h`` box. Rebuilding the full box keeps every frame of an animation
    aligned — trimming instead would make them jitter.
    """
    tex_id = rect["tex_id"]
    if tex_id >= len(pages):
        return None
    src_w, src_h = rect["src_w"], rect["src_h"]
    if src_w <= 0 or src_h <= 0:
        return None
    crop = pages[tex_id].crop((rect["src_x"], rect["src_y"],
                              rect["src_x"] + src_w, rect["src_y"] + src_h))
    if trim:
        return crop
    canvas = Image.new("RGBA", (max(rect["bound_w"], 1), max(rect["bound_h"], 1)),
                       (0, 0, 0, 0))
    canvas.paste(crop, (rect["dst_x"], rect["dst_y"]))
    return canvas


def safe_name(name: str) -> str:
    """Filesystem-safe asset name (case-insensitive FS on the Ally: keep it flat)."""
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in name) or "unnamed"


# ── the run ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game-dir", help="game install (auto-detects Steam if omitted)")
    ap.add_argument("--out", default=None,
                    help="output root (default: static/assets/local)")
    ap.add_argument("--only", default=None,
                    help="glob over asset names, e.g. 'spr_sans*'")
    ap.add_argument("--list", action="store_true",
                    help="inventory only — writes nothing")
    ap.add_argument("--trim", action="store_true",
                    help="write tight crops instead of full bounding boxes")
    ap.add_argument("--skip", choices=("sprites", "backgrounds", "fonts"),
                    action="append", default=[])
    args = ap.parse_args()

    game_dir = find_game_dir(args.game_dir)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_root = args.out or os.path.join(repo, "static", "assets", "local")

    data = DataWin(os.path.join(game_dir, "data.win"))
    print(f"game      : {data.game_name}")
    print(f"source    : {data.path}")
    print(f"chunks    : {len(data.chunks)}  strings: {len(data.strings)}")

    sprites = data.sprites()
    backgrounds = data.backgrounds()
    fonts = data.fonts()

    def keep(name: str) -> bool:
        return not args.only or fnmatch.fnmatch(name.lower(), args.only.lower())

    sprites = [s for s in sprites if keep(s["name"])]
    backgrounds = [b for b in backgrounds if keep(b["name"])]
    fonts = [f for f in fonts if keep(f["name"])]
    frame_total = sum(len(s["frames"]) for s in sprites)

    print(f"sprites   : {len(sprites)}  ({frame_total} frames)")
    print(f"backgrounds: {len(backgrounds)}")
    print(f"fonts     : {len(fonts)}")

    if args.list:
        print("\n── sprites ──")
        for s in sorted(sprites, key=lambda x: x["name"]):
            mark = " [special]" if s.get("special") else ""
            print(f"  {s['name']:<44} {s['width']:>4}x{s['height']:<4} "
                  f"{len(s['frames']):>3} frame(s){mark}")
        print("\n── backgrounds ──")
        for b in sorted(backgrounds, key=lambda x: x["name"]):
            print(f"  {b['name']}")
        print("\n── fonts ──")
        for f in sorted(fonts, key=lambda x: x["name"]):
            print(f"  {f['name']:<24} face={f['face']!r} size={f['size']}")
        return 0

    print("\ndecoding texture atlases …")
    pages = data.texture_pages()
    print(f"  {len(pages)} pages: "
          + ", ".join(f"{p.width}x{p.height}" for p in pages[:8])
          + (" …" if len(pages) > 8 else ""))
    tpag = data.tpag_entries()

    written = 0
    inventory: dict[str, Any] = {"game": data.game_name, "sprites": {},
                                 "backgrounds": [], "fonts": []}

    if "sprites" not in args.skip:
        sprite_root = os.path.join(out_root, "sprites")
        for s in sprites:
            if not s["frames"]:
                continue
            folder = os.path.join(sprite_root, safe_name(s["name"]))
            made = []
            for i, fptr in enumerate(s["frames"]):
                rect = tpag.get(fptr)
                if not rect:
                    continue
                img = render_frame(pages, rect, trim=args.trim)
                if img is None:
                    continue
                os.makedirs(folder, exist_ok=True)
                path = os.path.join(folder, f"{i:02d}.png")
                img.save(path)
                made.append(os.path.basename(path))
                written += 1
            if made:
                inventory["sprites"][s["name"]] = {
                    "frames": len(made), "size": [s["width"], s["height"]],
                    "origin": s["origin"],
                }
        print(f"sprites   → {sprite_root}")

    if "backgrounds" not in args.skip:
        bg_root = os.path.join(out_root, "backgrounds")
        for b in backgrounds:
            rect = tpag.get(b["frame"])
            if not rect:
                continue
            img = render_frame(pages, rect, trim=args.trim)
            if img is None:
                continue
            os.makedirs(bg_root, exist_ok=True)
            img.save(os.path.join(bg_root, f"{safe_name(b['name'])}.png"))
            inventory["backgrounds"].append(b["name"])
            written += 1
        print(f"backgrounds → {bg_root}")

    if "fonts" not in args.skip:
        font_root = os.path.join(out_root, "fonts")
        for f in fonts:
            rect = tpag.get(f["frame"])
            if not rect:
                continue
            img = render_frame(pages, rect, trim=args.trim)
            if img is None:
                continue
            os.makedirs(font_root, exist_ok=True)
            img.save(os.path.join(font_root, f"{safe_name(f['name'])}.png"))
            inventory["fonts"].append({"name": f["name"], "face": f["face"],
                                       "size": f["size"]})
            written += 1
        print(f"fonts     → {font_root}")

    if written:
        os.makedirs(out_root, exist_ok=True)
        with open(os.path.join(out_root, "inventory.json"), "w") as fh:
            json.dump(inventory, fh, indent=2, sort_keys=True)

    print(f"\n{written} images written under {out_root}")
    print("REMINDER: this directory is gitignored — never commit or deploy it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
