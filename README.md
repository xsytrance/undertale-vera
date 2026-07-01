# undertale-vera

[![CI](https://github.com/xsytrance/undertale-vera/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/xsytrance/undertale-vera/actions/workflows/ci.yml)

A save-aware companion app for **Undertale** — in-game characters answer as
themselves, grounded in the player's **actual** save state. A new MultiVera
instantiation mirroring `fft-psx-vera`'s architecture.

> **North star:** **Facts are sacred, feelings are free.** Undertale's save is
> morally-loaded state — we never fabricate kill counts, route, or choices; we
> take full creative latitude on voice and flavour.

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

**Quality gates** — the two-bucket wall is enforced by `hallucination_guard`, an
adversarial `voice_eval`, a `lore_eval`, the pytest suite, **and** a headless-browser
frontend smoke (`tools/frontend_smoke.py`). All are CI merge gates.

## Run
```bash
pip install -r requirements.txt
pytest -q                                   # 263 passing
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
