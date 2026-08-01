import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFY = 'http://127.0.0.1:8188'
OUT = Path('/home/xsyprime/undertale-vera/workspace/emblems/raw')
OUT.mkdir(parents=True, exist_ok=True)

positive = """pixel art emblem icon, single centered subject, square 1:1, a single stylized almond-shaped eye with a slit pupil, abstract eye-and-flame sigil, a wisp of electric cyan-blue flame curling up from the eye, glowing blue ember, minimalist heraldic sigil, inventory icon, crisp pixel grid, chunky black outline, limited palette of electric cyan blue, deep teal, white, black, hard pixel edges, slight inner glow only on cyan accent, flat solid pure black background, high contrast, clean readable silhouette, retro 16-bit dark game UI icon, calm menacing flat lens shape, single hard white highlight, flame made of three distinct pixel tongues, no haze"""
negative = """skull, skeleton, face, head, teeth, character, person, mascot, monster character, monster, Undertale, sans, copyrighted character, body, hands, torso, limbs, text, letters, watermark, signature, blurry, anti-aliased, soft gradient, glow haze, photorealistic, 3d render, multiple objects, busy background, cluttered, frame, border, portrait, sprite, game sprite, cartoon face"""

wf = {
    '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'sdxl_base_1.0.safetensors'}},
    '2': {'class_type': 'LoraLoader', 'inputs': {
        'model': ['1', 0], 'clip': ['1', 1],
        'lora_name': 'pixel-art-xl.safetensors', 'strength_model': 0.8, 'strength_clip': 0.8
    }},
    '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': positive, 'clip': ['2', 1]}},
    '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['2', 1]}},
    '8': {'class_type': 'EmptyLatentImage', 'inputs': {'width': 1024, 'height': 1024, 'batch_size': 1}},
    '9': {'class_type': 'KSampler', 'inputs': {
        'model': ['2', 0], 'positive': ['6', 0], 'negative': ['7', 0], 'latent_image': ['8', 0],
        'seed': 41001, 'steps': 30, 'cfg': 6.5, 'sampler_name': 'dpmpp_2m', 'scheduler': 'karras', 'denoise': 1.0
    }},
    '10': {'class_type': 'VAEDecode', 'inputs': {'samples': ['9', 0], 'vae': ['1', 2]}},
    '11': {'class_type': 'SaveImage', 'inputs': {'images': ['10', 0], 'filename_prefix': 'uv_emblem_sans_eye_flame'}},
}

def post(path, payload):
    req = urllib.request.Request(path, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def get(path):
    with urllib.request.urlopen(path, timeout=30) as r:
        return json.loads(r.read().decode())

resp = post(COMFY + '/prompt', {'prompt': wf})
pid = resp['prompt_id']
print('prompt_id', pid)

for _ in range(240):
    hist = get(COMFY + '/history/' + pid)
    item = hist.get(pid, {})
    outputs = item.get('outputs') or {}
    if outputs:
        saved = []
        for node in outputs.values():
            for img in node.get('images', []):
                params = urllib.parse.urlencode({'filename': img['filename'], 'subfolder': img.get('subfolder', ''), 'type': img.get('type', 'output')})
                url = COMFY + '/view?' + params
                target = OUT / img['filename']
                with urllib.request.urlopen(url, timeout=60) as r, open(target, 'wb') as f:
                    f.write(r.read())
                saved.append(str(target))
        print('\n'.join(saved))
        raise SystemExit(0)
    time.sleep(2)
raise TimeoutError('ComfyUI generation did not finish')
