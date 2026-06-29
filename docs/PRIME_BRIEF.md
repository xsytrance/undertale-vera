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
Positive = `<style token>, pixel art character portrait, bust framing, shoulders up,
expressive face, looking at viewer,` + the per-character clause:

- **sans.png** — `a short skeleton with a perpetual easy grin, half-lidded eye sockets,
  blue hoodie, dry and unbothered, a glint of hidden weight behind the smile`
- **toriel.png** — `a tall gentle horned goat-mother monster, soft warm eyes, flowing
  robe with a quiet sigil, protective and kind, faint motherly smile`
- **papyrus.png** — `a tall enthusiastic skeleton, theatrical confident grin, jaunty
  pose, polished bravado, boundless earnest energy`
- **flowey.png** — `a small sentient golden flower with an expressive face, sweet smile
  edged with something sharp, vivid and unsettling, saccharine menace`
- **undyne.png** — `a fierce finned warrior monster with a fiery glare, sharp toothy
  grin, blazing determination, all-in intensity`

Run each at a few seeds; pick the cleanest read. BiRefNet must leave clean alpha (no
halo). Deliver unframed — the app supplies the relic frame.

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
