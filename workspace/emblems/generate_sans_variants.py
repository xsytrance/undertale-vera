import copy
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY = 'http://127.0.0.1:8188'
OUT = Path('/home/xsyprime/undertale-vera/workspace/emblems/raw')
OUT.mkdir(parents=True, exist_ok=True)

base_positive = """crisp pixel art inventory emblem icon, ONE SINGLE OBJECT ONLY, isolated centered abstract almond eye sigil with one vertical slit pupil, three small cyan flame tongues rising from the top edge of the eye, electric cyan blue accent on pure black background, white tiny hard pixel highlight, chunky black outline, limited palette cyan blue deep teal white black, flat iconographic heraldic crest, no frame no border no cross no sword no flower, readable at tiny icon size, hard pixel edges, 16-bit game UI, centered with empty black around it"""
negative = """skull, skeleton, face, head, teeth, character, person, mascot, monster character, monster, Undertale, sans, copyrighted character, body, hands, torso, limbs, portrait, sprite, game sprite, cartoon face, flower, plant, leaf, sword, cross, crucifix, starburst, window, frame, border, rectangle frame, multiple objects, text, letters, watermark, signature, white background, gray background, scenery, busy background, cluttered, blurry, anti-aliased, soft gradient, glow haze, photorealistic, 3d render"""

def make_wf(seed):
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sdxl_base_1.0.safetensors'}},
        '2': {'class_type': 'LoraLoader', 'inputs': {'model': ['1', 0], 'clip': ['1', 1], 'lora_name': 'pixel-art-xl.safetensors', 'strength_model': 0.8, 'strength_clip': 0.8}},
        '3': {'class_type': 'LoraLoader', 'inputs': {'model': ['2', 0], 'clip': ['2', 1], 'lora_name': 'flat-icon.safetensors', 'strength_model': 0.45, 'strength_clip': 0.45}},
        '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': base_positive, 'clip': ['3', 1]}},
        '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['3', 1]}},
        '8': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
        '9': {'class_type': 'KSampler', 'inputs': {'model': ['3', 0], 'positive': ['6', 0], 'negative': ['7', 0], 'latent_image': ['8', 0], 'seed': seed, 'steps': 32, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m', 'scheduler': 'karras', 'denoise': 1.0}},
        '10': {'class_type': 'VAEDecode', 'inputs': {'samples': ['9', 0], 'vae': ['1', 2]}},
        '11': {'class_type': 'SaveImage', 'inputs': {'images': ['10', 0], 'filename_prefix': f'uv_emblem_sans_eye_flame_seed{seed}'}},
    }

def post(path, payload):
    req = urllib.request.Request(path, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(path, timeout=30) as r:
        return json.loads(r.read().decode())

def wait_and_download(pid):
    for _ in range(240):
        hist = get(COMFY + '/history/' + pid)
        outputs = (hist.get(pid, {}) or {}).get('outputs') or {}
        if outputs:
            saved = []
            for node in outputs.values():
                for img in node.get('images', []):
                    params = urllib.parse.urlencode({'filename': img['filename'], 'subfolder': img.get('subfolder', ''), 'type': img.get('type', 'output')})
                    target = OUT / img['filename']
                    with urllib.request.urlopen(COMFY + '/view?' + params, timeout=60) as r, open(target, 'wb') as f:
                        f.write(r.read())
                    saved.append(str(target))
            return saved
        time.sleep(2)
    raise TimeoutError(pid)

for seed in [41011, 41012, 41013, 41014]:
    pid = post(COMFY + '/prompt', {'prompt': make_wf(seed)})['prompt_id']
    print('prompt_id', seed, pid, flush=True)
    for path in wait_and_download(pid):
        print(path, flush=True)
