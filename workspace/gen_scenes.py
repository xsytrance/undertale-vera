#!/usr/bin/env python3
"""Generate 4 route scenes via ComfyUI with pixel-art LoRA + true-pixel post."""
import json, os, time, urllib.request, base64

COMFY_URL = "http://localhost:18188"

ROUTES = {
    "pacifist": {
        "positive": "pixel art, 16-bit, crisp pixels, limited palette, atmospheric environment, no characters, no text, warm golden underground dawn, soft ember light, hopeful, gentle, cavern interior, warm glow, peaceful",
        "negative": "text, watermark, logo, ui, characters, people, blurry, jpeg artifacts, realistic, photo"
    },
    "neutral": {
        "positive": "pixel art, 16-bit, crisp pixels, limited palette, atmospheric environment, no characters, no text, ambiguous violet-grey dusk, hushed cavern, unresolved, dim, muted colors, foggy, uncertain",
        "negative": "text, watermark, logo, ui, characters, people, blurry, jpeg artifacts, realistic, photo"
    },
    "genocide": {
        "positive": "pixel art, 16-bit, crisp pixels, limited palette, atmospheric environment, no characters, no text, ashen aftermath, dim crimson embers, cold dark stone, wrong and empty, desolate, sparse red, ruined, dead",
        "negative": "text, watermark, logo, ui, characters, people, blurry, jpeg artifacts, realistic, photo, bright, cheerful"
    },
    "undetermined": {
        "positive": "pixel art, 16-bit, crisp pixels, limited palette, atmospheric environment, no characters, no text, cold obsidian haze, unknowable dim cavern, shadows, deep dark, mysterious, void, minimal detail",
        "negative": "text, watermark, logo, ui, characters, people, blurry, jpeg artifacts, realistic, photo, bright, warm"
    }
}

def make_workflow(route_name, cfg_scale=5.5, seed=None):
    import random
    if seed is None:
        seed = random.randint(1, 99999)
    pos = ROUTES[route_name]["positive"]
    neg = ROUTES[route_name]["negative"]
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "Illustrious-XL-v2.0.safetensors"}},
        "2": {"class_type": "LoraLoader", "inputs": {
            "lora_name": "pixel-art-xl.safetensors",
            "strength_model": 1.1,
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
        # True-pixel: downscale nearest to ~256 long edge, then upscale back to 1024
        "9": {"class_type": "ImageScale", "inputs": {
            "image": ["8", 0], "upscale_method": "nearest", "width": 0, "height": 256, "crop": "disabled"
        }},
        "10": {"class_type": "ImageScale", "inputs": {
            "image": ["9", 0], "upscale_method": "nearest", "width": 1920, "height": 1080, "crop": "disabled"
        }},
        "11": {"class_type": "SaveImage", "inputs": {
            "images": ["10", 0], "filename_prefix": f"scene_{route_name}"
        }}
    }

os.makedirs("/home/xsyprime/undertale-vera/static/assets/scenes", exist_ok=True)

print(f"Generating 4 route scenes with pixel-art LoRA...")
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
    time.sleep(0.5)

print("\nQueued! Images will save to ComfyUI/output/ as scene_<route>.png")
