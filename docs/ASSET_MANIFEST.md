# Art Asset Manifest — the drop-in contract for Prime

Everything Prime's ComfyUI pipeline produces lands in `static/assets/` and is served
read-only by the app. **All generated art is gitignored** (see `.gitignore`); only
the resolvers, the pipeline graph, and this contract are committed. If a file matches
the slug + size below, it drops in with **zero code changes** — the resolvers find it
automatically.

## 1. Character portraits → `static/assets/portraits/<slug>.png`
Resolved by `avatar_resolver.resolve_avatar`. Missing → the app renders the
ember-gem SOUL sigil crest (never an error).

| Slug | Character | Notes |
|---|---|---|
| `sans.png` | Sans | dry, deadpan; half-lidded |
| `toriel.png` | Toriel | warm, motherly, gently firm |
| `papyrus.png` | Papyrus | loud, earnest, theatrical |
| `flowey.png` | Flowey | saccharine→sharp; switches register |
| `undyne.png` | Undyne | fierce, blazing, all-in |

- **Format:** PNG, **512×512**, transparent background (BiRefNet alpha).
- **Framing:** bust / shoulders-up, looking at viewer, museum-lit.
- The frontend frames them as relics (`.relic-portrait`: brass frame, warm inner glow,
  `image-rendering: pixelated`) — deliver the subject *unframed* on transparency; the
  CSS supplies the frame.

## 2. Route-reactive scene backdrops → `static/assets/scenes/<route>.png`
Resolved by `scene_resolver.resolve_scene`; surfaced via `GET /api/scenes` and applied
by `static/js/scene.js`. Missing → the CSS route-tinted gradient stays (never an error).

| File | Route | Mood |
|---|---|---|
| `pacifist.png` | Pacifist | warm dawn; gold/ember; hopeful, gentle |
| `neutral.png` | Neutral | ambiguous dusk; muted violet/grey; unresolved |
| `genocide.png` | Genocide | ashen aftermath; dim crimson embers; still, wrong |
| `undetermined.png` | undetermined | murk; cold obsidian haze; unknowable |

- **Format:** PNG (or JPG/WebP), **1920×1080** landscape, full-bleed.
- **Composition:** atmospheric environment, **no characters, no text, no UI**. The app
  dims it (~0.85 opacity + an obsidian radial wash) so it reads as mood behind parchment
  text — keep it low-contrast and uncluttered, weighted toward the top.
- **Determination-red is RARE:** only the Genocide scene may use it, sparingly.

## Style (shared)
Per `docs/ART_DIRECTION.md`: Undertale's visual *grammar* in the **MultiVera accent** —
deep obsidian field, ember/brass/crimson warmth, the reinterpreted ember-gem SOUL (a
faceted lozenge, **never** the red pixel heart). **Do not** copy Undertale sprites,
fonts, or the red heart. Our own generated reference art only.

## Hand-off
The literal generation prompts (positive/negative, per portrait and per scene) and the
LoRA training notes are in **`docs/LORA_NOTES.md`**.
