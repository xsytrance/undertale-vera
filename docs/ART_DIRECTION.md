# Determination Chronicle — Art Direction

Undertale's visual **grammar** rendered in the **MultiVera accent**. We do **not**
copy Undertale's assets, fonts, or its red pixel heart. The style layer lives in
`static/css/determination.css`; sample proofs render via
`tools/generate_sample_portraits.py`.

## The grammar, in our accent
- **Field:** deep obsidian (`--obsidian #0c0b10`) warmed by the MultiVera
  ember / brass / crimson palette (`--ember`, `--brass`, `--crimson`).
- **The SOUL, reinterpreted:** an **ember-gem sigil** — a faceted lozenge
  (`clip-path` diamond), museum-lit. **Not** the red pixel heart. Distinct geometry
  by design (`.soul-sigil`).
- **Dialogue vessel:** an engraved-plate frame + portrait inset + **typewriter
  ink-reveal** (`.dialogue-vessel`, `.ink-reveal`) — reusing the campfire kinetics
  from the FFT spine.
- **Portraits:** "museum-lit" pixel portraits framed like **relics**
  (`.relic-portrait`): brass frame, inner warm glow, `image-rendering: pixelated`.
- **Determination-red** (`--determination #d12f3e`): a **rare** accent reserved for
  soul / route / high-emotion beats only (e.g. the Genocide route badge, or
  `.soul-sigil.determined`). It must stay rare to keep its weight.

## ComfyUI pixel-portrait pipeline
`comfy_workflows/portrait_undertale.json` (ported from the FFT portrait graph):
Illustrious-XL checkpoint → **new** `undertale_determination_pixel` style LoRA →
positive/negative encode → KSampler (dpmpp_2m / karras, cfg 5.5, 30 steps) →
BiRefNet background removal → alpha join → scale to 512×512 → SaveImage.

**Prompt approach**
- Positive: `determination_chronicle_style, pixel art character portrait,
  {character} of the Underground, bust framing, museum-lit, warm ember and brass
  rim light, deep obsidian background, expressive face, looking at viewer`.
- Negative: `red heart icon, copyrighted undertale sprite, watermark, text,
  signature, frame, extra limbs, blurry, full body, hands`.

Outputs are 512×512 transparent PNGs in `static/assets/portraits/` (**gitignored**).

## Samples
Generate **2–3 sample relic portraits only** (do **not** batch the full cast):
- `python3 tools/generate_sample_portraits.py` → local **placeholder** relic frames
  (Pillow) proving the framing renders, for review.
- `python3 tools/generate_sample_portraits.py --comfy` → the **real** pixel
  portraits via a running ComfyUI ($COMFY_URL) once the style LoRA is trained.

## Needs human review
- The new style LoRA must be trained/curated (Egi) — placeholders stand in until then.
- Canonical character likeness vs. our reinterpretation is a review call.
