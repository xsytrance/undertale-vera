# Prime Brief — the magic prompts (ComfyUI hand-off)

For the GPU/ComfyUI agent. Targets the pipeline in
`comfy_workflows/portrait_undertale.json` (Illustrious-XL → `undertale_determination_pixel`
style LoRA → encode → KSampler dpmpp_2m/karras, cfg 5.5, 30 steps → BiRefNet bg-removal →
512² PNG). Deliver to the slugs/sizes in `docs/ASSET_MANIFEST.md`. **Our own reference
art only — do not train on, copy, or reproduce Undertale's sprites, fonts, or the red
heart.** Outputs are gitignored; just drop them in `static/assets/...`.

A shared **style token** prefixes every positive prompt:
`determination_chronicle_style, deep obsidian background, warm ember and brass rim light,
museum-lit, pixel art`

Shared **negative** (use for everything):
`red heart icon, copyrighted game sprite, watermark, signature, text, logo, ui, frame,
border, extra limbs, deformed hands, blurry, lowres, jpeg artifacts`

---

## A. Style LoRA (train first if not done)
Train `undertale_determination_pixel` on **our own** museum-lit pixel-portrait reference
set (obsidian + ember/brass, faceted-gem motif). Targets from our earlier unblock:
~2–4k steps (NOT 200k), network dim/alpha 16–32, LR ~1e-4 cosine, SDXL/Illustrious base.
Hold out a few images; stop when the obsidian/brass rim-light reads without frying detail.

## B. Character portraits (512×512, transparent, bust framing)
Use the SAME proven pipeline as the approved scenes: **pixel-art-xl LoRA (~1.0–1.2)
on Illustrious-XL** + true-pixel post — NOT the custom LoRA (paused; see notes).

⚠️ Drift fix: the earlier portrait attempts wandered into abstract texture because the
prompts were long flowery sentences. Keep prompts **short, tag-style, subject-and-
framing FIRST**, with emphasis weights on the framing so the model can't drift. Plain
dark background (helps the BiRefNet cutout).

Positive = this exact prefix + ONE per-character clause (keep it terse):
`(character portrait:1.3), (bust shot, head and shoulders:1.2), single character,
centered, facing viewer, {SUBJECT}, pixel art, pixelart, 16-bit, crisp pixel shading,
limited palette, dramatic warm ember rim light, museum-lit, plain dark obsidian
background, vignette, masterpiece`

- **sans.png** — `{SUBJECT} = a short stout skeleton, wide easy grin, half-lidded eye sockets, hood up on a worn blue jacket, calm`
- **toriel.png** — `{SUBJECT} = a tall gentle horned goat-woman, soft warm eyes, long ears, dark flowing robe with a small ember gem, serene`
- **papyrus.png** — `{SUBJECT} = a tall lanky skeleton, big confident toothy grin, chin up in a heroic pose, bold`
- **flowey.png** — `{SUBJECT} = a small golden flower with a cartoonish face, sweet smile with a sly sharp edge, glossy petals`
- **undyne.png** — `{SUBJECT} = a fierce blue-skinned finned warrior, one eye, sharp-toothed grin, red ponytail, blazing`

Negative (portraits): `full body, multiple characters, two heads, text, watermark,
signature, logo, ui, frame, border, busy background, scenery, landscape, blurry,
lowres, jpeg artifacts, extra limbs, deformed hands, fused fingers, photorealistic,
3d render`

Pipeline: gen 1024×1024 (dpmpp_2m / karras, cfg ~5.5, ~28–30 steps) → true-pixel post
(downscale **nearest** to ~144 px long edge → palette-quantize ~28 colors → upscale
**nearest** to 512) → **BiRefNet** background removal → transparent 512×512 PNG.

Run **4–6 seeds each, CURATE the single best** per character (clean face, clear
silhouette, on-style — don't ship a drifted one). BiRefNet must leave clean alpha (no
halo; raise the matte threshold if it does). Deliver unframed — the app supplies the
relic frame. Send a 5-up grid before finalizing. If a gen still drifts to texture,
bump `(character portrait:1.4)` and drop a couple of steps.

These are **our own reinterpretations** in the Determination Chronicle accent — original
character designs, never traced from or a copy of Undertale's sprites.

## C. Route-reactive scenes (1920×1080, landscape, NO characters/text)
Positive = `<style token>, atmospheric environment, wide establishing shot, cinematic,
empty of characters, no text,` + the per-route clause. Keep low-contrast and top-weighted
(the app dims them behind parchment text):

- **pacifist.png** — `a warm golden dawn breaking over a quiet underground cavern, soft
  ember light, gentle hopeful calm, motes of light, peaceful`
- **neutral.png** — `an ambiguous violet-grey dusk in a hushed underground hall,
  unresolved and still, muted, neither warm nor cold`
- **genocide.png** — `an ashen silent aftermath, dim crimson embers in cold dark stone,
  dust settling, wrong and empty, sparse rare determination-red glow` *(red used sparingly)*
- **undetermined.png** — `a cold obsidian haze, an unknowable dim cavern, shapes lost in
  shadow, mysterious, unresolved`

## Drop-in checklist
1. Portraits → `static/assets/portraits/<slug>.png` (512², transparent).
2. Scenes → `static/assets/scenes/<route>.png` (1920×1080).
3. No code changes needed — `avatar_resolver` / `scene_resolver` + `/api/scenes` find
   them; the frontend fades scenes in over the route-tint gradient automatically.
4. Send a contact-sheet grid back for a likeness/style review before batching the rest.
