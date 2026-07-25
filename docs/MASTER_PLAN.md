# Master Plan — Authentic Local Skin → ROG Ally → Linux

**Goal:** a private, local-only build of undertale-vera that looks like *actual
Undertale* — real sprites, real fonts, real UI furniture — running on the son's
**ROG Xbox Ally X** (24 GB / 1 TB, Windows 11), then folded back to Linux/Prime.

**The music is untouched.** `static/audio/` and the whole `MusicLayer` /
`VoiceLayer` / `SoundTest` stack stay exactly as they are. That work stands.

## Status

| Phase | State |
|---|---|
| 0 · Skin switch + fence | **done** — `local_skin.py`, gitignored, 10 tests |
| 1 · Extractor | **done** — 6550 images from 2583 sprites in ~2 s |
| 2 · Slot mapping | **done** — 9 characters, 4 scenes, 3 UI |
| 3 · `authentic.css` | **done** |
| 4 · Handheld / TV / controller | **code done, unverified on hardware** |
| 5 · Linux + Cockpit | **done** — loopback-only `ember-cockpit` on `:9093` |

**Try it:**

```bash
python3 tools/extract_undertale_assets.py && python3 tools/map_local_skin.py
UNDERTALE_VERA_SKIN=authentic python3 -m uvicorn undertale_vera_app:app --port 9092
```

**Known gaps, carried deliberately:**

- `tools/rog_setup.ps1` has **never been executed** — no PowerShell on the dev
  machine. First run on the Ally is a debugging session, not a formality.
- The DualSense **button indices are from the standard spec, not observed**.
  Navigation geometry is tested; the mapping is not. Most likely thing to need
  a tweak, and a two-minute fix once visible.
- **Fonts are pixel webfonts, not the game's.** The 20 extracted sheets are
  bitmap atlases; converting them to real webfonts is a genuine sub-project.
  Typography is pixel-*flavoured*, not authentic.
- Playwright isn't installed locally, so the frontend smoke gate runs only in CI.
- Deltarune isn't installed, so its 8 emblems keep the original crests.

---

## 0. Source of the art — decided

Assets are **extracted from your own installed copy of the game**, not scraped
from fan wikis:

```
~/.local/share/Steam/steamapps/common/Undertale/data.win   (62.9 MB)
```

Verified chunk table (standard GameMaker `FORM`/IFF):

| Chunk | Size | What we take |
|---|---|---|
| `SPRT` | 1.98 MB | sprite definitions — names + frame → page refs |
| `TPAG` | 170 KB | texture-page rects (x, y, w, h, bounds) |
| `TXTR` | 12.7 MB | the texture atlases (embedded PNGs) |
| `BGND` | 6.0 KB | room backdrop refs → route scenes |
| `FONT` | 149 KB | the real in-game typefaces |
| `STRG` | 2.86 MB | the string table every name resolves through |

Why this beats scraping: exact pixels at native resolution with correct alpha,
every sprite (not just the popular ones), no third-party re-hosting, and one
script that re-runs on any machine that has the game — including the Ally.

**Containment rules (non-negotiable):**
1. Extracted art lands under `static/assets/local/**` — **gitignored before the
   first extraction runs**, never committed.
2. Only the *extractor*, the *slot manifest*, and the *skin toggle* are
   committed. Same discipline the repo already uses for generated art.
3. The default/public skin keeps the original ember-gem art. CI, the frontend
   smoke gate, and anything shared stay visually unchanged.

**Not available locally:** Deltarune is not installed (only save fixtures in
`saves/deltarune`). The 8 Deltarune emblems — susie, ralsei, lancer, jevil,
seam, noelle, king, rouxls-kaard — keep their original art unless Deltarune
gets installed, at which point the same extractor points at its `data.win`.

---

## Phase 0 — The skin switch (build the safety first)

Before any extraction:

- `.gitignore` += `static/assets/local/`
- `UNDERTALE_VERA_SKIN` env var: `original` (default) | `authentic`
- Surfaced to the frontend via the existing boot payload; `index.html` gets one
  conditional `<link>` for `css/authentic.css`.

**Why a toggle, not a straight replace:** one env var flip proves the original
build still renders, keeps `pytest -q` + `tools/frontend_smoke.py` green without
needing the art present, and means the repo is still safe to push.

*Gate: `pytest -q` green, smoke green, `git status` shows no art.*

---

## Phase 1 — The extractor

**`tools/extract_undertale_assets.py`** — pure-Python (stdlib + Pillow), no
.NET, no UndertaleModTool, no network:

```
--game-dir   path to the install (auto-detects Steam on Linux + Windows)
--out        default static/assets/local
--only       sprite-name glob, for iterating on one slot
--list       dump the sprite/font inventory without writing images
```

Pipeline: `FORM` walk → `STRG` table → `TXTR` atlas decode → `TPAG` rects →
`SPRT` names + frames → crop each frame → trimmed PNG with alpha →
`static/assets/local/sprites/<sprite_name>/<NN>.png`. Plus `FONT` → glyph
sheets, and `BGND` → room backdrops.

Ships with `--list` output committed as an inventory doc so slot mapping is
reviewable without the art present.

*Gate: `--list` names known sprites; spot-check a handful of PNGs by eye.*

---

## Phase 2 — Slot mapping (`docs/LOCAL_SKIN_MANIFEST.md`)

The app already has clean, resolver-driven slots. Mapping real sprites into
them is mostly **drop-in** — `avatar_resolver` and `scene_resolver` already do
"file on disk → URL, else fall back", and `app.js:avatarMarkup` already prefers
a raster over the inline SVG. Slots to fill:

| Slot | Currently | Becomes |
|---|---|---|
| Character emblems (9) | original SVG/PNG crests | real character sprites |
| Relic portraits | ember-gem crest fallback | real face/expression sprites |
| SOUL sigil | ember-gem faceted lozenge | the real SOUL sprite |
| Route scenes (4) | CSS gradients + generated art | real room backdrops |
| Dialogue vessel | engraved brass plate | the real dialogue box furniture |
| Buttons / chips | brass-on-obsidian | the real battle-button furniture |
| Save/milestone marks | sigils | the real save-point art |
| **Typefaces** | Cinzel / Crimson / Space Mono via Google CDN | the real in-game fonts, **self-hosted** |

The font swap kills the three `fonts.googleapis.com` `<link>`s in
`index.html` — which is a hard requirement anyway for an **offline handheld**.
That's a genuine win beyond looks.

*Gate: side-by-side screenshots, both skins, before anything else proceeds.*

---

## Phase 3 — `css/authentic.css`

The full black-and-white Undertale look layered over the existing structure,
same way `undertale.css` already skins `determination.css`. Real fonts, real
box borders, pixel-exact rendering, sprite-based furniture. No changes to
`determination.css` — the original skin must survive untouched.

*Gate: every view walked in both skins; `node --check` on any touched JS.*

---

## Phase 4 — ROG Xbox Ally X

Two viable architectures. **Recommendation: A.**

**A — All-local on the Ally (recommended).** Python + uvicorn on
`127.0.0.1:9092`, Ollama on the Ally itself, Guided Mode watching the Ally's own
save. 24 GB RAM runs `llama3.1:8b` comfortably with headroom for a larger model.
Fully offline — works on a car ride, no Prime, no tunnel, no network.

**B — Prime-hosted over Tailscale.** Ally is a thin browser client; Prime does
the LLM. Less setup, but needs Prime awake and a network, and Guided Mode would
need the save synced off the Ally. Keep as fallback.

Work items for A:
- `tools/rog_setup.ps1` — one-shot: Python, venv, deps, Ollama, model pull,
  extractor run against the Ally's own game install, launcher + shortcut.
- Windows save-path auto-detect (`%LOCALAPPDATA%\UNDERTALE\file0`) in Guided Mode.
- Kiosk launcher (Edge app mode, fullscreen) + non-Steam shortcut so it appears
  as a tile in the Xbox full-screen experience and launches like a real app.
- Offline audit: zero external requests (fonts fixed — `tools/vendor_fonts.py`).

### The actual setup: docked to a TV, played with a DualSense

This changed the design, so it's recorded rather than assumed. **Docked to a
television there is no pointer at all** — no mouse, no touch. Consequences:

- **Gamepad navigation is the only input path**, not an accessibility extra.
  Without `static/js/gamepad.js` the app is unusable on a TV. Navigation is
  *spatial* (nearest thing in that direction), because DOM order and visual
  layout diverge constantly and tab-order navigation feels broken the moment
  they disagree. Geometry is pinned by `tools/gamepad_nav_test.js`.
- **`pointer: coarse` does not match a gamepad.** Touch-target sizing is
  correct for the handheld but does nothing when docked — so TV needs its own
  gate, not a shared "not-desktop" branch.
- **A TV is a 10-foot UI.** Type sized for a 40 cm screen is unreadable at 3 m,
  so TV mode scales the whole type scale off one root font-size.
- **TVs overscan.** Many sets still crop 3–5% of every edge without saying so;
  anything in that band is gone. TV mode insets the app to survive it.
- TV mode is **opt-in** (`?tv=1`, Options button, persisted) and never
  automatic: a controller connecting does not mean the display is a television.

Controls: D-pad/stick move · Cross select · Circle back · Options toggles TV
mode. Standard Gamepad mapping, so an Xbox pad behaves identically.

*Gate: son plays Undertale on the Ally, Guided Mode reacts live, no network,
and the whole UI is reachable from the DualSense alone.*

---

## Phase 5 — Back to Linux and the rest

- Fold the handheld UX pass back into the main build (it helps everywhere).
- Authentic skin available on Prime behind the same env flag.
- Cockpit integration — the Hyprland "Underground Cockpit" session already at
  Phase 1 gets the authentic skin as its default surface.
- Extractor generalized: point `--game-dir` at Deltarune when installed and the
  8 Deltarune emblems fill in with no code changes.

---

## Standing gates (every phase)

`pytest -q` · `tools/frontend_smoke.py` · `python3 -m py_compile *.py` ·
`node --check static/js/<file>.js` · `git status` clean of art · original skin
visually unchanged.

## Rules this plan does not touch

SaveTruth First · no save editing · unknowns → null · route honesty ·
the two-bucket wall · DB ADD-only · commit allow-list only. This is a **skin and
a port**. No parser, truth, prompt, or guard logic changes anywhere in it.
