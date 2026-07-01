# undertale-vera Backend

## Project Overview
FastAPI backend for "undertale-vera" — an Undertale save parser + AI chat
companion. Parses `file0` / `undertale.ini` saves, normalizes them into a
`SaveTruth` schema (with route detection), and provides grounded LLM chat where
in-game characters answer as themselves. A MultiVera instantiation mirroring
`fft-psx-vera` (read-only reference; never modify it).

## Key Directories & Files
> **Full map:** see [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) — every module,
> the frontend, views, the audio system, the API, and CI. Highlights:

**Core (parse → truth → prompt → chat)**
- `undertale_vera_app.py` — FastAPI app, all endpoints, orchestration.
- `save_parser.py` / `route_detection.py` / `save_truth.py` / `ledger.py` — parse → route
  → normalized SaveTruth + the prompt-contract wall + snapshot/remembrance ledger.
- `prompt_builder.py` — two-bucket grounded system prompts.
- `llm_client.py` — chat backend, mockable. Default local **Ollama**
  (`UNDERTALE_VERA_BACKEND=ollama`, `OLLAMA_MODEL=llama3.1:8b`); set
  `UNDERTALE_VERA_BACKEND=anthropic` for Claude (`claude-opus-4-8`). Any backend
  failure → `LLMUnavailable` → grounded deterministic fallback (never a 500).
- `hallucination_guard.py` / `provenance.py` — the wall, enforced + made visible.

**Characters & memory:** `character_config.py` (ADD-only), `character_disposition.py`,
`affinity.py`, `relationships.py`, `living_memory.py`, `chat_style.py`, `save_flavor.py`.

**Features (each: in-voice instruction + deterministic fallback):** `council.py`,
`journal.py`/`milestones.py`, `chronicle.py`, `judgment.py`, `reports.py` (Report Cards),
`proactive.py` (reach-out), `crossave.py`/`constellation.py`/`divergence.py` (cross-save +
Two-Save Divergence), `agentmail_client.py` (opt-in report email, env-gated).

**Assets/retrieval:** `avatar_resolver.py`, `scene_resolver.py`, `rag_engine.py`.

**Frontend (`static/`, no build):** `index.html`; `css/determination.css` (base + type
scale) + `css/undertale.css` (skin); `js/app.js` (router, views, chat, eggs, `AudioBus`);
`js/music.js` (`MusicLayer` — route + character beds), `js/voices.js` (`VoiceLayer` blips),
`js/soundtest.js` (`SoundTest` room), `js/scene.js`, `js/emblems.js`.
Audio files live in `static/audio/*.mp3` (gitignored) — see [`docs/EASTER_EGGS.md`](../docs/EASTER_EGGS.md)
for secrets and the audio memory for the loop/normalize recipe.

- `inspector.py` — QA harness (Playwright or HTTP-only sweep).
- `tools/frontend_smoke.py` — headless-browser UI smoke (a CI merge gate).
- `tests/` — Pytest suite. **Always run `pytest -q` before committing.**

## Core Rules & Guardrails
1. **SaveTruth First (FACTS ARE SACRED):** parser-derived facts always win. The LLM
   must never invent the player's name, LOVE, route, or kill count.
2. **No Save Editing:** strictly read-only re: save files. No mutation endpoints.
3. **Unknowns → null:** unreadable/absent save fields are `null`, never guessed.
4. **Route honesty:** ambiguous signals → `undetermined`, never a guessed route.
5. **Two-bucket wall:** memory/personality (FREE) may colour HOW a character speaks,
   never WHAT the save says (SACRED). Memory endpoints never touch `Project.save_data`.
6. **DB ADD-only; commit allow-list only; generated art is gitignored.**

## Key Commands
- `python3 -m py_compile *.py backend/*.py` — quick Python syntax check.
- `node --check static/js/<file>.js` — quick JS syntax check before committing frontend.
- `pytest -q` — full test suite (mock the LLM; never require a live model in CI).
- `SMOKE_BASE=http://127.0.0.1:9092 python tools/frontend_smoke.py` — headless UI smoke
  (also a CI merge gate; point `SMOKE_CHROMIUM` at a browser locally if needed).
- `python3 inspector.py --base http://127.0.0.1:9092` — QA sweep.
- CI (`.github/workflows/ci.yml`): **`syntax + pytest`** and **`frontend smoke`** — both green to merge.

## Development Workflow
- TDD for pure helpers (parser/route/truth). Mock `generate_reply` in chat tests.
- When building AI features, default to the latest, most capable Claude models.
