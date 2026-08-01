from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path('/home/xsyprime/undertale-vera/static/assets/emblems')
WORK = Path('/home/xsyprime/undertale-vera/workspace/emblems/final')
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)

BLACK = '#000000'
CYAN = '#4dd0e1'
TEAL = '#1a6f7a'
WHITE = '#ffffff'
DARK = '#062529'

# Build at true 64x64 pixel resolution, then nearest-neighbor upscale.
im = Image.new('RGB', (64, 64), BLACK)
d = ImageDraw.Draw(im)

# Flame: three distinct pixel tongues, black outline then fill.
flames_outline = [
    [(29, 27), (27, 20), (29, 12), (32, 5), (35, 13), (34, 21), (33, 27)],
    [(23, 30), (20, 24), (21, 18), (25, 12), (28, 20), (28, 29)],
    [(38, 30), (36, 22), (38, 16), (43, 11), (45, 20), (42, 27), (41, 31)],
]
for poly in flames_outline:
    d.polygon(poly, fill=BLACK)
for poly in [
    [(30, 26), (29, 20), (31, 12), (32, 8), (34, 14), (33, 21), (32, 26)],
    [(24, 28), (22, 24), (23, 19), (25, 15), (27, 21), (27, 28)],
    [(39, 28), (38, 23), (39, 18), (42, 14), (43, 20), (41, 26), (40, 29)],
]:
    d.polygon(poly, fill=TEAL)
for poly in [
    [(31, 24), (31, 18), (32, 11), (33, 18), (33, 24)],
    [(25, 25), (24, 22), (25, 18), (26, 22), (26, 26)],
    [(40, 25), (40, 21), (41, 17), (42, 21), (41, 26)],
]:
    d.polygon(poly, fill=CYAN)

# Outer almond eye: chunky black outline, teal body, white inner edge.
outer = [(9, 36), (15, 30), (24, 26), (32, 25), (40, 26), (49, 30), (55, 36), (49, 42), (40, 46), (32, 47), (24, 46), (15, 42)]
d.polygon(outer, fill=BLACK)
mid = [(12, 36), (17, 32), (25, 29), (32, 28), (39, 29), (47, 32), (52, 36), (47, 40), (39, 43), (32, 44), (25, 43), (17, 40)]
d.polygon(mid, fill=TEAL)
inner_high = [(16, 35), (22, 31), (31, 30), (42, 31), (48, 35), (43, 34), (32, 33), (22, 34)]
d.polygon(inner_high, fill=CYAN)
inner_low = [(16, 37), (22, 41), (31, 42), (42, 41), (48, 37), (43, 38), (32, 39), (22, 38)]
d.polygon(inner_low, fill=DARK)

# Iris/glowing slit core.
d.ellipse((25, 29, 39, 43), fill=BLACK)
d.ellipse((27, 31, 37, 41), fill=CYAN)
d.rectangle((31, 30, 33, 42), fill=BLACK)
d.rectangle((32, 31, 32, 41), fill=DARK)

# Hard white pixel highlight, tiny and intentional.
d.rectangle((28, 32, 30, 34), fill=WHITE)
d.point((35, 37), fill=WHITE)

# Pixel sparks/inner glow only in accent color, no haze.
for pt in [(21, 28), (43, 28), (18, 36), (46, 36), (29, 24), (36, 24), (32, 48)]:
    d.point(pt, fill=CYAN)

# Save canonical 64 and nearest up/down scales.
files = {}
files['64'] = OUT / 'sans_eye_flame_64.png'
im.save(files['64'])
files['1024'] = OUT / 'sans_eye_flame_1024.png'
im.resize((1024, 1024), Image.Resampling.NEAREST).save(files['1024'])
files['30'] = OUT / 'sans_eye_flame_30.png'
im.resize((30, 30), Image.Resampling.NEAREST).save(files['30'])

# Preview sheet on black with scale comparison.
preview = Image.new('RGB', (1320, 1080), BLACK)
preview.paste(Image.open(files['1024']), (0, 0))
preview.paste(im.resize((256, 256), Image.Resampling.NEAREST), (1040, 80))
preview.paste(im.resize((120, 120), Image.Resampling.NEAREST), (1110, 400))
preview_path = WORK / 'sans_eye_flame_preview.png'
preview.save(preview_path)

for key, path in files.items():
    (WORK / path.name).write_bytes(path.read_bytes())
print('files:')
for key, path in files.items():
    print(f'{key}: {path}')
print(f'preview: {preview_path}')
