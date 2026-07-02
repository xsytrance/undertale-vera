# LoRA Notes — `undertale_determination_pixel`

**Style Name:** Determination Chronicle  
**Trigger Token:** `determination_chronicle_style`  
**Base Model:** Illustrious-XL-v2.0  
**LoRA Type:** SDXL LoRA ( networks.lora, UNet-only )  
**Output:** `undertale_determination_pixel.safetensors`

---

## 1. Design Goal

A pixel-portrait accent LoRA for **museum-lit character portraits** in OUR branding (no Undertale assets):

- **Deep obsidian field** — near-black backgrounds that recede
- **Ember / brass museum lighting** — warm rim + key, gallery vibes
- **Relic-framed bust portraits** — bust framing, not full-body
- **Determination-red reserved as a rare accent** — soul/route beats only, never the default

Reference: `docs/ART_DIRECTION.md` → "Determination Chronicle" spec.

---

## 2. Dataset

- **25 reference images** generated via ComfyUI pixel-art pipeline
- **Source approach:** Generated through Illustrious-XL + pixel-art-xl LoRA v1.0 with long, explicit negative prompts (NO Undertale sprites or copyrighted assets)
- **Character variety:** Diverse Underground-aligned archetypes, all original
- **Captions:** Every image tagged with `determination_chronicle_style` trigger token
- **Repeats:** 10× per image (250 effective samples)
- **Resolution:** 768×768 (resized from original 1024×1024 ComfyUI output)

### Why generated (not scraped or hand-drawn)

This project's hard rule: **no training on, copying, or redistributing any copyrighted game sprites/art.** The pixel-art LoRA was used here as a *style transfer oracle* to produce reference images that share pixel-art grammar (limited palettes, hard edges, readable silhouettes) without crossing into any existing IP. The resulting LoRA learns our *accent*, not anyone else's assets.

---

## 3. Training Parameters

| Parameter | Value |
|---|---|
| Script | kohya_ss `sdxl_train_network.py` |
| Base model | Illustrious-XL-v2.0 |
| Network module | `networks.lora` |
| Network dim (rank) | 16 |
| Network alpha | 8 |
| Resolution | 768×768 |
| Batch size | 1 (grad accum × 2) |
| Max steps | 1500 |
| Learning rate | 1e-4 |
| LR scheduler | cosine |
| Warmup steps | 100 |
| Optimizer | AdamW8bit |
| Mixed precision | bf16 |
| Save precision | fp16 |
| Gradient checkpointing | on |
| Text encoder | UNet-only (outputs cached to disk) |
| Noise offset | 0.05 |
| Min SNR gamma | 5 |
| Attention | PyTorch SDPA (no xformers — Blackwell SM_120 incompatible) |
| Seed | 42 |
| GPU | RTX 5060 Ti 16GB |

---

## 4. Sample Grid

*Generated after training with trigger token at weight 0.8, steps 30, CFG 7:*

| Pacifist Hero | Neutral Wanderer | Genocide Blade | Undetermined Echo |
|---|---|---|---|
| _(grid pending first checkpoint save)_ | | | |

> Grid images saved to `static/assets/portraits/` when generated. See `.gitignore` — raw art is not committed; only this notes file goes into the repo.

---

## 5. Usage in Workflow

`comfy_workflows/portrait_undertale.json` → `LoraLoader` node:
- **LoRA file:** `undertale_determination_pixel.safetensors` (env `COMFY_LORA`)
- **Recommended weight:** 0.7–0.9
- **Positive trigger:** `determination_chronicle_style`
- **Negative additions:** `red heart icon, copyrighted undertale sprite, watermark, text, signature, frame, extra limbs, blurry, full body, hands`

---

## 6. Guardrails Recap

- ✅ **Original dataset only** — generated from our pipeline, no copyrighted inputs
- ✅ **Style grammar, not asset copy** — we learn the *accent* (lighting, framing, palette), not anyone's characters
- ✅ **Weights not committed** — `*.safetensors` gitignored; LoRA lives in ComfyUI's `models/loras/`
- ✅ **Training images not committed** — `dataset/` gitignored; reproducible from this doc if needed
