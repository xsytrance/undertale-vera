#!/usr/bin/env python3
"""Generate training reference images via ComfyUI API."""
import json, os, time, urllib.request

COMFY_URL = "http://localhost:18188"
OUT_DIR = "/home/xsyprime/undertale-vera/workspace/lora_dataset"
os.makedirs(OUT_DIR, exist_ok=True)

def make_workflow(seed, filename_prefix):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "Illustrious-XL-v2.0.safetensors"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {
            "text": "determination_chronicle_style, deep obsidian background, warm ember and brass rim light, museum-lit, pixel art, bust portrait of a fantasy character, looking at viewer, detailed face, pixelated texture, dark museum atmosphere, single character, upper body",
            "clip": ["1", 1]
        }},
        "3": {"class_type": "CLIPTextEncode", "inputs": {
            "text": "red heart icon, copyrighted game sprite, watermark, signature, text, logo, ui, frame, border, extra limbs, deformed hands, blurry, lowres, jpeg artifacts, full body, landscape, multiple characters, photo, realistic",
            "clip": ["1", 1]
        }},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "sdxl_vae.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0],
            "latent_image": ["5", 0], "seed": seed, "steps": 30, "cfg": 5.5,
            "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0
        }},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["4", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": filename_prefix}}
    }

seeds = [42, 137, 256, 314, 512, 777, 1000, 1234, 1500, 2000,
         2048, 2500, 3000, 3141, 4096, 5000, 5555, 6000, 7000, 8000,
         9000, 10000, 11000, 12000, 13000]

print(f"Queueing {len(seeds)} reference image generations...")
for i, seed in enumerate(seeds):
    wf = make_workflow(seed, f"ref_{i:03d}")
    try:
        data = json.dumps({"prompt": wf}).encode()
        req = urllib.request.Request(
            f"{COMFY_URL}/prompt",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req)
        result = json.loads(resp.read())
        print(f"  [{i+1:2d}/{len(seeds)}] seed={seed:6d} → {result.get('prompt_id', 'ok')}")
    except Exception as e:
        print(f"  [{i+1:2d}/{len(seeds)}] seed={seed:6d} ERROR: {e}")
    time.sleep(0.3)

print(f"\nDone! {len(seeds)} images queued. They'll save to ComfyUI/output/")
