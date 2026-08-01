#!/usr/bin/env python3
"""Generate 4 route scenes via ComfyUI — stronger prompts for cavern-only interiors."""
import json, os, time, urllib.request

COMFY_URL = "http://localhost:18188"

ROUTES = {
    "pacifist": {
        "positive": "pixel art, 16-bit style, crisp pixels, limited color palette, interior of an underground cavern, warm golden light emanating from embers and torchlight, soft glow on stone walls, stalactites, peaceful atmosphere, gentle warm light rays, no people, no characters, no figures, no creatures, empty cavern, golden dawn light filtering down, underground spring, warm amber tones",
        "negative": "people, person, human, character, figure, creature, animal, text, watermark, logo, ui, blurry, jpeg artifacts, realistic, photo, outdoor, sky, sun, plants, trees, grass"
    },
    "neutral": {
        "positive": "pixel art, 16-bit style, crisp pixels, limited color palette, interior of a dim violet-grey cavern at dusk, hushed and quiet, unresolved atmosphere, misty, muted purple-grey tones, faint bioluminescent glow, stalagmites, still water pool, ambiguous lighting, no people, no characters, no figures, no creatures, empty cavern interior",
        "negative": "people, person, human, character, figure, creature, animal, text, watermark, logo, ui, blurry, jpeg artifacts, realistic, photo, outdoor, sky, bright, warm, golden"
    },
    "genocide": {
        "positive": "pixel art, 16-bit style, crisp pixels, limited color palette, interior of a destroyed cavern, aftermath, cold dark stone walls, dim red embers glowing faintly, ash covering the ground, sparse crimson light, desolate and empty, wrong and hollow, dead embers, no people, no characters, no figures, no creatures, ruined stone formations, ashen wasteland underground",
        "negative": "people, person, human, character, figure, creature, animal, text, watermark, logo, ui, blurry, jpeg artifacts, realistic, photo, outdoor, sky, warm, golden, green, alive, cheerful, bright"
    },
    "undetermined": {
        "positive": "pixel art, 16-bit style, crisp pixels, limited color palette, interior of an unknowable cavern, cold obsidian haze, deep shadows, dim and mysterious, void-like darkness, minimal detail, barely visible stone walls, fog, cold blue-black tones, no people, no characters, no figures, no creatures, empty void, abstract darkness",
        "negative": "people, person, human, character, figure, creature, animal, text, watermark, logo, ui, blurry, jpeg artifacts, realistic, photo, outdoor, sky, warm, golden, bright, detailed, colorful"
    }
}

def make_workflow(route_name, cfg_scale=7.0, seed=None):
    import random
    if seed is None:
        seed = random.randint(1, 99999)
    pos = ROUTES[route_name]["positive"]
    neg = ROUTES[route_name]["negative"]
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "Illustrious-XL-v2.0.safetensors"}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "lora_name": "pixel-art-xl.safetensors",
            "strength_model": 1.2,
            "strength_clip": 1.0,
            "model": ["1", 0],
            "clip": ["1", 1]
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 1]}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": "sdxl_vae.safetensors"}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0],
            "latent_image": ["6", 0], "seed": seed, "steps": 30,
            "cfg": cfg_scale, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["5", 0]}},
        "11": {"class_type": "SaveImage", "inputs": {
            "images": ["8", 0], "filename_prefix": f"v2_scene_{route_name}"
        }}
    }

os.makedirs("/home/xsyprime/undertale-vera/static/assets/scenes", exist_ok=True)

print(f"Generating 4 route scenes (v2) with pixel-art LoRA...")
for route_name in ROUTES:
    wf = make_workflow(route_name)
    data = json.dumps({"prompt": wf}).encode()
    req = urllib.request.Request(
        f"{COMFY_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        print(f"  {route_name:15s} → queued ({result.get('prompt_id', 'ok')})")
    except Exception as e:
        print(f"  {route_name:15s} → ERROR: {e}")
    time.sleep(1)

print("\nQueued! Raw 1024x1024 images will save to ComfyUI/output/ as v2_scene_<route>.png")
print("Will post-process with PIL for true-pixel effect.")
