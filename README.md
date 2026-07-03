# Ember — a save-aware companion for Undertale & Deltarune

[![CI](https://github.com/xsytrance/undertale-vera/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xsytrance/undertale-vera/actions/workflows/ci.yml)

**Show Ember your save file and the Underground talks back — about *your* run.**
The characters answer as themselves, grounded in what your save actually says:
your route, your LOVE, what you did. They never make your story up.

> **The covenant: facts are sacred, feelings are free.** Your save is read-only,
> unknown fields stay unknown, an ambiguous route is called *undetermined* —
> and the voices are original reinterpretations, never copied dialogue.

## Quick start (no AI setup needed)

You'll need **Python 3.11+** and git. Then:

```bash
git clone https://github.com/xsytrance/undertale-vera
cd undertale-vera
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn undertale_vera_app:app --port 9092
```

> **New to this?** The [step-by-step guide](docs/GETTING_STARTED.md) assumes
> nothing — it starts at "open a terminal" and covers Windows/macOS/Linux,
> installing Python and git, and connecting a local model, with troubleshooting.

Open http://127.0.0.1:9092, tap **＋ Read a save** (there's a step-by-step
"where is my save file" guide right there), and you're playing. With no AI
configured, Ember runs in 🕯 **Spark mode** — every character answers with a
scripted, save-grounded voice. Zero keys, zero downloads.

Want a real model behind them? **⚙ Settings → Power source** offers three
roads: 🔑 an OpenRouter key (free-tier models suggested), 🖥 a local model via
[Ollama](https://ollama.com) — the picker's **⌕ Detect installed** button lists
what your Ollama actually has — or 🔌 **your own server**: any OpenAI-compatible
endpoint (vLLM, LM Studio, llama.cpp) by base URL + model name. See
[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) for all three walked
through, and [`docs/PIPELINES.md`](docs/PIPELINES.md) for the full
local-everything recipe book. Two editions ship from this one codebase: set
`EMBER_EDITION=lite` for the trimmed, Spark-locked newbie deployment.

This is part of **MultiVera** — one engine, many worlds. The in-app 🌌 page
tells that story; [`docs/GAME_PACKS.md`](docs/GAME_PACKS.md) is the spec for
teaching it a new game.

## What it does
> **Full map:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). **Secrets:**
> [`docs/EASTER_EGGS.md`](docs/EASTER_EGGS.md).

**Foundation** — read `file0` + `undertale.ini` **read-only** (unknowns → `null`),
detect the route (ambiguous → `undetermined`), normalize into **SaveTruth**, and drive
**grounded chat** through the two-bucket wall (SaveTruth sacred; voice + Living Memory
free). Any LLM failure → a grounded deterministic fallback, never a 500.

**Ember — the app** (front-end shell in `static/`, no build step):
- **Grounded chat** with all 9 characters + a provenance overlay (SACRED vs FREE).
- **The Council** — the whole Underground reacts at once, stance-coloured.
- **Report Cards** — per-character after-action reports, with a managed history and
  optional **email** (via AgentMail, opt-in).
- **Across Your Saves** — the Constellation verdict + a **Two-Save Divergence** picker
  (any two saves, any character speaks to the fork).
- **Keepsake Journal**, **Timeline**, **The Chronicle**, **Judgment**, proactive reach-out.
- **Sound Test** — an interactive soundtrack room (jukebox + jam + visualizer); a full
  route-and-character music system with a global volume/mute; per-character typing voices.
- **Route atmosphere**, per-character portraits, first-time explainers, and a deep layer
  of Easter eggs.

**Deltarune Chapter 1** — one app, two games: drop `filech1_0` in and the console
falls into **Dark World mode** (violet, Ch1 cast + Hometown personas of the returning
faces, honest `undetermined` route). Show saves from both worlds and **Across Two
Worlds** wakes: Toriel dreams of the other universe; Divergence speaks across games.

**🧭 Guided Mode** — play the game beside Ember: watch your save folder (read-only,
never game memory), and every in-game save becomes a live beat with your pinned
party reacting to exactly what changed, plus a spoiler-dialled hint ladder.
Full guide: [`docs/GUIDED_MODE.md`](docs/GUIDED_MODE.md).

**Game packs** — the engine is game-agnostic; Undertale and Deltarune Ch1 are the
first two packs. Want to teach it another game (FFT is next)? The spec:
[`docs/GAME_PACKS.md`](docs/GAME_PACKS.md). Step zero matters most: **pick a game
with easily readable save data** (plain text / INI / JSON) — the save must be
parsed or reverse-engineered before anything else, and AI assistants are
genuinely good partners for that part.

**Quality gates** — the two-bucket wall is enforced by `hallucination_guard`, an
adversarial `voice_eval`, a `lore_eval`, the pytest suite, **and** a headless-browser
frontend smoke (`tools/frontend_smoke.py`). All are CI merge gates.

## Run
```bash
pip install -r requirements.txt
pytest -q                                   # 296 passing
python3 -m uvicorn undertale_vera_app:app --port 9092
python3 inspector.py --base http://127.0.0.1:9092
SMOKE_BASE=http://127.0.0.1:9092 python tools/frontend_smoke.py   # UI smoke
```

## Pipeline
```
save files → parser → SaveTruth (+ ROUTE) → storage
          → prompt builder (two-bucket wall) → grounded chat
          → automated truth verification (Inspector)
```

See `docs/` for the port plan, save format, art direction, buildlog, and roadmap.
