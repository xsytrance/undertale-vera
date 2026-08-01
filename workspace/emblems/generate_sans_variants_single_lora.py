import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY = 'http://127.0.0.1:8188'
OUT = Path('/home/xsyprime/undertale-vera/workspace/emblems/raw')
OUT.mkdir(parents=True, exist_ok=True)

positive = """crisp pixel art inventory icon of ONE SINGLE ABSTRACT EYE SYMBOL, isolated centered, almond eye shape, vertical slit pupil, three small electric cyan pixel flame tongues rising from top of eye, pure black empty background, minimal flat heraldic sigil, chunky black outline around cyan object, hard pixel edges, limited color palette electric cyan blue deep teal white black, tiny white square highlight, high contrast, readable 30x30, no frame, no border, no cross, no sword, no flower, no body, no face, dark game UI emblem"""
negative = """skull, skeleton, face, head, teeth, character, person, mascot, monster character, monster, Undertale, sans, copyrighted character, body, hands, torso, limbs, portrait, sprite, game sprite, cartoon face, flower, plant, leaf, sword, cross, crucifix, starburst, window, frame, border, rectangle frame, multiple objects, text, letters, watermark, signature, white background, gray background, scenery, busy background, cluttered, blurry, anti-aliased, soft gradient, glow haze, photorealistic, 3d render"""

def make_wf(seed):
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sdxl_base_1.0.safetensors'}},
        '2': {'class_type': 'LoraLoader', 'inputs': {'model': ['1', 0], 'clip': ['1', 1], 'lora_name': 'pixel-art-xl.safetensors', 'strength_model': 0.9, 'strength_clip': 0.9}},
        '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': positive, 'clip': ['2', 1]}},
        '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['2', 1]}},
        '8': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
        '9': {'class_type': 'KSampler', 'inputs': {'model': ['2', 0], 'positive': ['6', 0], 'negative': ['7', 0], 'latent_image': ['8', 0], 'seed': seed, 'steps': 30, 'cfg': 7.0, 'sampler_name': 'dpmpp_2m', 'scheduler': 'karras', 'denoise': 1.0}},
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
        status = (hist.get(pid, {}) or {}).get('status') or {}
        if status.get('status_str') == 'error':
            print(json.dumps(status, indent=2)[:4000])
            return []
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

for seed in [41021, 41022, 41023, 41024]:
    pid = post(COMFY + '/prompt', {'prompt': make_wf(seed)})['prompt_id']
    print('prompt_id', seed, pid, flush=True)
    for path in wait_and_download(pid):
        print(path, flush=True)
