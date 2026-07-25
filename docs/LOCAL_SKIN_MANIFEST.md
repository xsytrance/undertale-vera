# Local Skin Manifest — the authentic look, and why each slot holds what it does

The private, machine-local skin: real game art in place of the committed
ember-gem originals. Enabled with `UNDERTALE_VERA_SKIN=authentic`.

> **This art is never committed and never deployed.** `static/assets/local/` is
> gitignored. The art belongs to the game's creators; this is a personal re-skin
> of a personal tool on a machine that owns the game. The *pipeline* and *this
> manifest* are committed so any owner can reproduce it — the output is not.
> The shared/public build keeps the original art, always.

## The pipeline

```bash
# 1. read your own install → static/assets/local/{sprites,backgrounds,fonts}/
python3 tools/extract_undertale_assets.py            # --list to inventory first

# 2. fill the app's slots → static/assets/local/{emblems,portraits,scenes,ui}/
python3 tools/map_local_skin.py --preview

# 3. run with the skin on
UNDERTALE_VERA_SKIN=authentic python3 -m uvicorn undertale_vera_app:app --port 9092
```

Step 1 auto-detects Steam on Linux and Windows; pass `--game-dir` otherwise.
Re-run both per machine rather than copying output around.

## What step 1 yields (verified on this install)

| | Count |
|---|---|
| Sprites | 2583 (6333 frames) |
| Backgrounds | 249 |
| Fonts | 20 glyph sheets |
| Texture atlases decoded | 26 |
| Total written | 6550 images, ~45 MB, ~2 s |

## Character slots

Three naming conventions coexist in the archive, which is why these look
inconsistent — the mapping is empirical, not derivable:

| Slot | Source sprite | Note |
|---|---|---|
| `sans` | `spr_face_sans` | |
| `papyrus` | `spr_face_papyrus` | |
| `toriel` | `spr_face_torieltalk` | no plain `spr_face_toriel` exists |
| `undyne` | `spr_face_undyne0` | |
| `alphys` | `spr_alphysface_0` | second convention |
| `asgore` | `spr_asgore_face0` | third convention |
| `mettaton` | `spr_mettface_general` | |
| `flowey` | `spr_flowey` | **no dialogue portrait** — overworld sprite |
| `napstablook` | `spr_napstablook_d` | **no dialogue portrait** — overworld sprite |

**The black plate is keyed out.** Dialogue portraits are white line-art on a
solid black rectangle — correct in-game, where the box is black, but a hard
block against our obsidian UI. `map_local_skin.py` drops it so the linework
floats, which is how it reads in the game anyway. `--keep-plate` opts out.

**Frames are rebuilt on the bounding box, not trimmed.** The atlas packs sprites
with whitespace stripped; each entry records where the crop sits inside the true
sprite box. Rebuilding the full box keeps animation frames aligned — trimming
would make them jitter. `--trim` opts out.

## UI slots

| Slot | Source | Replaces |
|---|---|---|
| `ui/soul` | `spr_heart` | the ember-gem lozenge (`.soul-sigil`) |
| `ui/soul_broken` | `spr_heartbreak` | — |
| `ui/savepoint` | `spr_savepoint` | — |

## Scene slots

Chosen for mood per `docs/ART_DIRECTION.md` — atmospheric, no text, no UI.
These are the most subjective picks here; re-point them freely.

| Route | Background | Why |
|---|---|---|
| `pacifist` | `bg_endingview` | the surface — warm, hopeful |
| `neutral` | `bg_firstroom` | where every run begins — unresolved |
| `genocide` | `bg_core_distance` | dim, industrial, still, wrong |
| `undetermined` | `bg_tb` | murk — unknowable |

## Not available

**Deltarune is not installed** on this machine (only save fixtures in
`saves/deltarune`). These 8 emblems keep their committed original art: `susie`,
`ralsei`, `lancer`, `jevil`, `seam`, `noelle`, `king`, `rouxls-kaard`. Install
Deltarune and point `--game-dir` at it — the extractor handles that archive too,
and the resolvers need no changes.

## How the fence works

`local_skin.py` fails closed: anything other than exactly `authentic` (case and
surrounding whitespace tolerated) resolves to the original skin. Unset, empty,
mistyped, or wrong-value all keep the committed look, so the private skin cannot
switch itself on by accident on a shared host. `tests/local_skin_test.py` pins
this, plus the guarantee that with the skin off every resolver returns exactly
what it returned before the skin existed.

Resolution order per slot, authentic skin on:

```
static/assets/local/<kind>/<slug>.png   ← extracted art
static/assets/<kind>/<slug>.png         ← the committed original
""                                       ← the built-in inline crest
```

Every step degrades safely, so a slot with nothing mapped yet still renders.

## Fonts — not yet wired

20 glyph sheets extract cleanly, but they are **bitmap atlases, not TTFs**.
Turning them into usable webfonts means generating font files from bitmap
glyphs — a real sub-project, not a drop-in. Until then the app keeps its
current typefaces.

Related and worth doing regardless: `static/index.html` pulls three stylesheets
from `fonts.googleapis.com`. That's a hard blocker for an offline handheld, so
self-hosting the fonts is a prerequisite for the ROG Ally phase — see
`docs/MASTER_PLAN.md` Phase 4.
