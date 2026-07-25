# The Windows App — what it is, and how to make it fast

Short answer: **it's a real installable Windows app**, and the thing that
determines whether it feels fast has almost nothing to do with the app shell.

## What it actually is

Ember is a local web app: a small Python server on `127.0.0.1` plus a
no-build vanilla-JS frontend. On Windows you install it as a proper app —
in the Ember window, **⋯ > Apps > "Install this site as an app"**.

That gives you:

- its own icon, Start Menu entry, and taskbar pin
- its own window, no tabs and no address bar
- pinnable to the Xbox library as a non-Steam game

### Why not package it as a "real" native app?

Because it would be **slower**, not faster.

| Approach | Rendering | Extra runtime | Verdict |
|---|---|---|---|
| **Installed app (what we do)** | WebView2 — already in Windows | none | fastest |
| Edge `--app=` mode | same engine | none | same speed, no app identity |
| Tauri wrapper | same WebView2 | small | no gain, more to maintain |
| Electron | bundled Chromium | ~100 MB + own processes | strictly worse |

An Electron build would ship a **second copy of Chromium** alongside the one
Windows already has. Same rendering, more memory, slower cold start. Tauri
avoids that by using WebView2 — which is exactly what the installed app
already uses, so wrapping it buys an `.exe` and nothing else.

The frontend is a few hundred KB of plain JS with no framework and no build
step. It is not the bottleneck, and no shell can make it meaningfully faster.

## Where the time actually goes

**The language model dominates everything.** A reply is a model doing
inference. The UI around it renders in milliseconds. So all real tuning is
model tuning.

### 1. Keep the model resident — the biggest single win

By default Ollama evicts an idle model after about 5 minutes, so the next reply
pays several seconds re-reading gigabytes from disk *before generating a single
token*. Play is bursty — a beat fires, a character answers, then nothing for a
while — which is precisely the pattern that keeps landing on a cold model.

`tools/rog_setup.ps1` sets:

```powershell
$env:OLLAMA_KEEP_ALIVE    = "-1"   # pin in RAM for the session
$env:OLLAMA_FLASH_ATTENTION = "1"  # cheaper attention, faster long contexts
$env:OLLAMA_NUM_PARALLEL  = "1"    # one player; don't split the context window
```

On 24 GB, pinning an 8B model costs memory you have and removes a stall you'd
otherwise hit constantly.

### 2. Model size is the main quality/speed dial

`llama3.1:8b` is the default and a reasonable middle. If replies feel slow,
**drop to a ~3B model before touching anything else** — it is the largest
speed lever available and the characters stay grounded either way, because
SaveTruth facts come from the parser, not the model.

```powershell
ollama pull llama3.2:3b
# then edit start-ember.ps1: $env:OLLAMA_MODEL = "llama3.2:3b"
```

Going the other way (a larger model) is also fine on 24 GB — expect slower
replies, and check it still fits alongside the game.

### 3. GPU acceleration — check, don't assume

The Ally's integrated GPU is **not reliably accelerated by Ollama on Windows**.
Ollama's AMD support targets specific discrete cards; an integrated RDNA part
may silently fall back to CPU. CPU inference on this chip is perfectly usable
for a small model, so this is a bonus, not a requirement.

Check which one you got:

```powershell
ollama run llama3.1:8b "hi"        # then, in another terminal:
ollama ps                          # shows CPU vs GPU for the loaded model
```

If it says CPU and you want to chase GPU: **LM Studio** exposes a Vulkan
backend that works well on AMD integrated graphics, and Ember speaks to any
OpenAI-compatible server (see `docs/GETTING_STARTED.md`, Option B). That's the
most promising route — but treat it as an experiment, not a supported path.

### 4. Measure rather than guess

```powershell
ollama run llama3.1:8b --verbose "Say one sentence."
```

`--verbose` prints eval rate in tokens/sec. Compare models with it. **No
numbers are quoted in this document on purpose** — none of this has been
benchmarked on the Ally, and an invented figure is worse than none.

## What is not a performance problem

- **The authentic skin.** Sprites are tiny PNGs served from localhost.
- **The music.** Ordinary audio playback.
- **TV mode / gamepad.** CSS and a `requestAnimationFrame` poll reading a
  controller — negligible.
- **The game running alongside.** Undertale is extremely light; it and an 8B
  model coexist comfortably in 24 GB.

## Setup

```powershell
powershell -ExecutionPolicy Bypass -File tools\rog_setup.ps1 -Tv
```

`-Tv` starts in TV mode (bigger type, overscan inset) for HDMI use. Then
install it as an app from the ⋯ menu, and pin it wherever you want it.

> `rog_setup.ps1` has not been run on hardware — there is no PowerShell on the
> development machine. Expect the first run to need a fix or two.
