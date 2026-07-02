# Pipelines — running the full-fat tier, end to end

Ember's top rung: everything the app uses can be produced on your own machine
(or with one hosted tool where that's honestly the better road). This is the
recipe book for that tier — chat, art, and music. The prompts themselves live
on the in-app **🛠 Prompt Workshop** page; this document is the machinery around
them.

> The lower rungs need none of this: 🕯 Spark mode runs with zero setup, and
> 🔑 BYOK needs only an OpenRouter key (pick both in the app's power picker).

## 1. Chat — a local model via Ollama

```bash
ollama pull llama3.1:8b
UNDERTALE_VERA_BACKEND=ollama OLLAMA_MODEL=llama3.1:8b uvicorn undertale_vera_app:app --port 9092
```

Or skip the env vars entirely and choose 🖥 in the in-app power picker. Any model
Ollama serves works; 8B-class instruct models are plenty because **the prompts do
the heavy lifting** — the facts arrive pre-parsed and fenced, so the model is
only asked to be a voice, never a source of truth. If the model misbehaves, the
hallucination guard flags the reply; if the backend dies, Spark answers instead.

## 2. Art — ComfyUI pixel scenes and portraits

The chat backdrops and portrait experiments come from a local
[ComfyUI](https://github.com/comfyanonymous/ComfyUI) pipeline. Two workflow
graphs ship in `comfy_workflows/`:

- `scene_pixelart_v3.json` — area backdrops. The graph is deliberately boring:
  **checkpoint → LoRA → prompt/negative → KSampler → VAE decode → save**, then the
  part that makes it read as game art: **downscale → nearest-neighbour upscale →
  palette quantize → save**. Generating large and crushing to a quantized grid is
  what makes it look *pixel* instead of "AI painting of pixels".
- `portrait_undertale.json` — bust portraits (ported from the sibling project's
  graph).

The style itself is a custom SDXL LoRA — see [`LORA_NOTES.md`](LORA_NOTES.md)
for the full training recipe (base model, 25-image self-generated dataset, the
`determination_chronicle_style` trigger token, and the design goal: obsidian
field, ember museum lighting, determination-red as a rare accent). The
one-line-per-subject brief pattern is in [`ART_DIRECTION.md`](ART_DIRECTION.md)
and on the Workshop page. House rules: **all art is original** (no ripped
sprites, ever) and **all generated art is gitignored** — the repo stays
asset-free.

## 3. Music — two roads

### Road A — hosted (Suno): the road actually taken
The shipped soundtrack was made with [Suno](https://suno.com) driven by the
prompts published on the Workshop page. What made it work was prompt craft, not
the tool: describing the **DNA of the sound** (music box, felt piano, plucked
SNES-style ostinatos, choir "aah" pads, tempo, key, the feeling of a specific
place) instead of naming a game, and always ending with
`seamless loop, instrumental, no vocals`.

*(Reserved: the maker's own account of the ChatGPT → Suno drafting loop — the
same story slotted on the Workshop page.)*

### Road B — fully local, Suno-style (HeartMuLa) — **field-tested**
[HeartMuLa](https://github.com/HeartMuLa/heartlib) is an open-source family of
music foundation models (2026) that brings Suno-style generation fully offline:
full tracks from style tags (and lyrics, if you want vocals — we don't), runnable
on your own GPU, with ComfyUI integration and web-studio front-ends like
[heartmula-studio](https://github.com/rustyorb/heartmula-studio). The public
release is **HeartMuLa-oss-3B** (the 7B that matches Suno is internal-only).

**Verified on this box** (RTX 5060 Ti 16 GB): a 60-second instrumental from the
char-toriel style prompt in ~5 minutes (RTF ≈ 5 with the codec decoding on CPU).
Setup: clone `heartlib`, `pip install -e .` in a venv, `hf download` the three
checkpoint repos (~21 GB on disk). Field notes that will save you an afternoon:

- **Instrumental** isn't a flag — the model is lyrics-conditioned. Use a
  structure-only lyrics file and put `instrumental, no vocals` in the tags.
  Tags are free text inside `<tag>…</tag>` — a Workshop-style comma list
  works as-is.
- **The structure paces the duration.** A sparse skeleton
  (`[intro]/[inst]/[outro]`) lets the model sample its end-of-song token
  after ~10 seconds; `max_audio_length_ms` is only a ceiling, not a request.
  For a full-length track, write a full-length skeleton — a dozen alternating
  `[inst]`/`[verse]`/`[chorus]`/`[bridge]` sections carried a 3-minute render
  reliably to the cap.
- **VRAM**: ~9.4 GB peak for the 3B in bf16, of which ~3 GB is the KV cache —
  sized by the stock config for 8192 positions (~11 minutes of audio) no matter
  how short your clip. If the card is shared (an Ollama model, a desktop), cap
  it before generating: `pipe.mula.backbone.max_seq_len = 1024` covers a
  60-second clip and reclaims most of that. A 60 s clip needs ≈ text tokens +
  duration_ms/80 positions.
- **Evict your cohabitants**: anything that keeps a model resident (Ollama
  keep-alive, a ComfyUI cached checkpoint — `POST /free` releases it) will
  OOM you at cache setup, and Ollama reloads the moment anything asks it a
  question. Flipping Ember to 🕯 Spark for the window stops the asking.
- **Saving**: `torchaudio.save` now routes through `torchcodec`, whose wheels
  may want a different CUDA runtime than your torch. Sidestep it — patch the
  save to `soundfile` and write a WAV; the finishing pass below makes the MP3
  anyway (one lambda: `mg.torchaudio.save = lambda p, wav, sr:
  soundfile.write(p, wav.numpy().T, sr)`).

The Workshop's final style prompts — including their Exclude lists — port over
nearly as-is.

**The honest caveat**: HeartMuLa is a *song* model — even with structure-only
lyrics and `instrumental, no vocals` in the tags, it can and did sing anyway
on this box. Beautiful beat, uninvited choir. If the goal is instrumental
loops (it is, here), use the MusicGen road below and keep HeartMuLa for when
you actually want Suno-style songcraft.

### Road B′ — fully local, instrumental-by-construction (MusicGen) — **field-tested**
Meta's MusicGen cannot sing — which makes it the *reliable* local road for
this app's instrumental loops. It runs on a single modest GPU via
🤗 Transformers, and it's fast: on the resident RTX 5060 Ti, **30 s of audio in
18 s** with `musicgen-small` (weights already cached from an earlier session)
and **30 s in 43 s** with `musicgen-medium` in fp16. Load medium in fp16 —
fp32 (~6 GB weights + T5 + activations) OOMs a 16 GB card that's sharing with
a resident Ollama model. The app's audio layer loops whatever it's given, so a
clean ~27 s crossfaded loop serves as a character bed just as well as a
3-minute one. The whole pipeline is ~30 lines:

```python
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import soundfile as sf

proc = AutoProcessor.from_pretrained("facebook/musicgen-medium")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-medium").to("cuda")
inputs = proc(text=["Mysterious dark-fantasy chiptune loop, music-box arpeggios, "
                    "slow 76 BPM, B minor, seamless video game background music, no vocals"],
              return_tensors="pt").to("cuda")
audio = model.generate(**inputs, max_new_tokens=1503)   # ≈30 s @ 50 tok/s
sf.write("dark-world.wav", audio[0, 0].cpu().numpy(), model.config.audio_encoder.sampling_rate)
```

The same Workshop prompts work with light edits (MusicGen prefers plainer
descriptions — drop the poetry, keep instruments/tempo/key/mood). Generate
~30 s and let the finishing pass below turn it into a loop.

### The finishing pass (both roads)
Raw generations don't loop. The fix: rotate the head into the tail with a
crossfade, then normalize so the whole soundtrack sits level:

```bash
D=4  # crossfade seconds
ffmpeg -y -i in.mp3 -t $D -c:a pcm_s16le _head.wav
ffmpeg -y -ss $D -i in.mp3 -c:a pcm_s16le _body.wav
ffmpeg -y -i _body.wav -i _head.wav \
  -filter_complex "[0][1]acrossfade=d=${D}:c1=tri:c2=tri,loudnorm=I=-14:TP=-1.5:LRA=11" \
  -c:a libmp3lame -b:a 192k out.mp3
```

Verify with `ffmpeg -i out.mp3 -af ebur128 -f null -` (target ≈ −14 LUFS; one-pass
loudnorm can undershoot quiet material — re-run with a gain touch-up if a track
lands below ≈ −15). Drop the result into `static/audio/` under the exact filenames
listed in [`ARCHITECTURE.md`](ARCHITECTURE.md)'s audio section — the audio layer picks it up with no
restart, and every missing file falls back silently, so partial soundtracks are
fine.

## 4. Voices
No pipeline at all: the character blips are synthesized live in the browser
(`static/js/voices.js`) — waveform + pitch + envelope per character. Adding a
voice is writing a profile, not generating a file.
