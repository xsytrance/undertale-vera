# undertale-vera

[![CI](https://github.com/xsytrance/undertale-vera/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xsytrance/undertale-vera/actions/workflows/ci.yml)

A save-aware companion app for **Undertale** — in-game characters answer as
themselves, grounded in the player's **actual** save state. A new MultiVera
instantiation mirroring `fft-psx-vera`'s architecture.

> **North star:** **Facts are sacred, feelings are free.** Undertale's save is
> morally-loaded state — we never fabricate kill counts, route, or choices; we
> take full creative latitude on voice and flavour.

## Spine 0 — "The Save Remembers" (this build)
Scaffold + grounded character chat:
- **Parser** (`save_parser.py`) — reads `file0` + `undertale.ini` **read-only**;
  unknowns → `null`, never guessed.
- **Route detection** (`route_detection.py`) — Pacifist / Neutral / Genocide
  derived from real flags; ambiguous → `undetermined`.
- **SaveTruth** (`save_truth.py`) — normalized schema + the prompt-contract wall.
- **Grounded chat** (`prompt_builder.py` + `llm_client.py`) — the two-bucket wall:
  SaveTruth sacred, character voice + Living Memory free. Claude `claude-opus-4-8`.
- **Living Memory** (`living_memory.py`) — ask / remember / recall across sessions.
- **Ember** — the front-end shell + Undertale-flavoured style layer (`static/`) +
  ComfyUI pixel-portrait pipeline (`comfy_workflows/`).
- **Inspector** (`inspector.py`) — inherited QA harness, sweeps day one.

## Run
```bash
pip install -r requirements.txt
pytest -q                                   # 19 passing
python3 -m uvicorn undertale_vera_app:app --port 9092
python3 inspector.py --base http://127.0.0.1:9092
```

## Pipeline
```
save files → parser → SaveTruth (+ ROUTE) → storage
          → prompt builder (two-bucket wall) → grounded chat
          → automated truth verification (Inspector)
```

See `docs/` for the port plan, save format, art direction, buildlog, and roadmap.
