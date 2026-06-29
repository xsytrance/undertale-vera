# undertale-vera Backend

## Project Overview
FastAPI backend for "undertale-vera" — an Undertale save parser + AI chat
companion. Parses `file0` / `undertale.ini` saves, normalizes them into a
`SaveTruth` schema (with route detection), and provides grounded LLM chat where
in-game characters answer as themselves. A MultiVera instantiation mirroring
`fft-psx-vera` (read-only reference; never modify it).

## Key Directories & Files
- `undertale_vera_app.py` — FastAPI app, endpoints, orchestration.
- `save_parser.py` — read-only file0/undertale.ini parser.
- `route_detection.py` — derives Pacifist/Neutral/Genocide (or undetermined).
- `save_truth.py` — normalized SaveTruth schema + validator + prompt-contract wall.
- `prompt_builder.py` — two-bucket grounded system prompts.
- `character_config.py` — Undertale character registry (ADD-only).
- `living_memory.py` — pure ask/remember/recall functions (Bucket B).
- `llm_client.py` — Anthropic Claude client (default `claude-opus-4-8`), mockable.
- `inspector.py` — QA harness (Playwright or HTTP-only sweep).
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
- `python3 -m py_compile *.py backend/*.py` — quick syntax check.
- `pytest -q` — full test suite (mock the LLM; never require a live model in CI).
- `python3 inspector.py --base http://127.0.0.1:9092` — QA sweep.

## Development Workflow
- TDD for pure helpers (parser/route/truth). Mock `generate_reply` in chat tests.
- When building AI features, default to the latest, most capable Claude models.
