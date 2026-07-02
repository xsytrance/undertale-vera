# Ember — Architecture & Feature Map

*Ember* (codename `undertale-vera`) is a save-aware **Undertale** companion: it parses
your real `file0` / `undertale.ini` into a normalized **SaveTruth**, detects your route,
and lets the in-game cast talk to you **grounded in your actual save** — plus a soundtrack,
reports, cross-save reflection, and more.

> **Prime directive: FACTS ARE SACRED, FEELINGS ARE FREE.** Parser-derived facts (name,
> LOVE, route, kills) always win; the LLM never invents them. Voice, mood, memory, and
> flavour are free.

---

## The two-bucket wall
Every grounded response is built from two buckets that never cross:
- **SACRED** — SaveTruth facts (route, LOVE, kills, name, dispositions). Rendered verbatim
  into the prompt; the `hallucination_guard` re-checks the model's reply against them.
- **FREE** — the character's voice, personality, lore, Living Memory, emotion.

Every grounding block returns `""` when empty, so the baseline prompt stays byte-identical.

---

## Backend (Python / FastAPI)

**App & data**
- `undertale_vera_app.py` — the FastAPI app: all endpoints + orchestration.
- `backend/models.py` — SQLAlchemy models: `Project`, `SaveSnapshot`, `Conversation`,
  `JournalEntry`, `ReportEntry`, `CharacterMemory`. **DB is ADD-only** (except the
  player-owned reports history, which can be archived/deleted).

**Parse → truth → route**
- `save_parser.py` — read-only `file0` / `undertale.ini` parser (unknowns → `null`).
- `route_detection.py` — Pacifist / Neutral / Genocide (ambiguous → `undetermined`).
- `save_truth.py` — normalized SaveTruth schema + validator + the prompt-contract wall.
- `ledger.py` — the remembrance ledger / snapshot fields / resets.

**Prompt & LLM**
- `prompt_builder.py` — assembles the two-bucket grounded system prompt (+ `emphasis_note`).
- `llm_client.py` — `generate_reply()`; Ollama (default) + Anthropic backends; any failure
  → `LLMUnavailable` → grounded deterministic fallback (never a 500).
- `chat_style.py` — response dials (length/intensity/lore/meta) as FREE directives.
- `hallucination_guard.py` — checks a reply against SaveTruth (the wall, enforced).
- `provenance.py` — per-reply SACRED-vs-FREE breakdown for the UI.

**Character system**
- `character_config.py` — the 9-character registry (ADD-only).
- `character_disposition.py` — who the save records as killed/spared/befriended.
- `affinity.py` — each character's stance toward you (warm/wary/grieving/hostile…).
- `relationships.py` — the fate of those a character cares about.
- `living_memory.py` — pure ask/remember/recall (Bucket B).

**Cross-save & history**
- `crossave.py` — New Game+ recognition + the Other's Echo.
- `constellation.py` — the whole-history verdict + auto-divergence (kindest vs cruelest).
- `divergence.py` — **Two-Save Divergence**: a chosen character speaks to the fork between
  any two saves you pick.
- `milestones.py` — the self-filling Keepsake Journal's milestone entries.

**Feature modules** (each: an in-voice instruction + a deterministic fallback)
- `council.py` — the whole Underground reacts at once.
- `journal.py` — the Keepsake Journal (characters write grounded entries).
- `chronicle.py` — the full written record, exportable as markdown.
- `judgment.py` — the verdict, grounded in the save.
- `reports.py` — **Report Cards**: per-character after-action reports.
- `proactive.py` — characters reach out to you unprompted.
- `save_flavor.py` — small SACRED texture (area / play time / pie / the Fun-value anomaly).

**Assets, retrieval, email**
- `avatar_resolver.py` — portrait/emblem URL resolution (photo > emblem > SVG > crest).
- `scene_resolver.py` — route-reactive backdrop art resolution.
- `rag_engine.py` / `knowledge_ingest.py` — world-lore retrieval (keyword fallback in CI).
- `agentmail_client.py` — **email a report** via AgentMail (opt-in, env-gated, mockable).

**Art pipeline** (on-box, gitignored territory): `train_lora*.py`, `comfy_workflows/`.

---

## Frontend (`static/`, no build step)
- `index.html` — the "Console" shell: top bar · left rail (saves · cast · views) · stage
  (one active view) · right rail (the save) · mobile drawers + bottom nav.
- `css/determination.css` — base layout + the type/easing scale.
- `css/undertale.css` — the Undertale skin (override layer: black panels, white pixel
  borders, Pixelify/VT323 fonts, the `* ` dialogue marker).
- `js/app.js` — the whole client: router, all views, chat, portraits, emblems, feel,
  Easter eggs, the `AudioBus` master. (~1900 lines.)
- `js/music.js` — `MusicLayer`: the ambient bed (route + character themes, gesture-safe).
- `js/voices.js` — `VoiceLayer`: per-character synthesized typing blips + UI sounds.
- `js/soundtest.js` — `SoundTest`: the Sound Test room's WebAudio graph (jukebox + jam).
- `js/scene.js` — route-reactive backdrop. `js/emblems.js` — the 9 inline SVG fallbacks.

---

## Views / features (the Modes menu)
Chat · The Council · Timeline · Keepsake Journal · Across Your Saves (Constellation +
the Two-Save Divergence picker) · The Chronicle · Judgment · Report Cards · **Sound Test**.
Plus: per-character portraits, proactive reach-out (with cadence control), route
atmosphere, the master volume/mute, and the first-time explainer modals.

## Audio system
`static/audio/*.mp3` (all gitignored). See **[audio memory / recipe]** for the loop +
normalize pipeline. Filenames: `a-new-save-file.mp3` (main), `route-{pacifist,neutral,
genocide}.mp3`, `char-<slug>.mp3` (9). Fallbacks are silent-safe (missing bed → route bed
→ main theme). Everything is scaled by the global `AudioBus` (top-bar volume + mute).

## API (selected)
`POST /api/upload` · `GET/POST /api/projects…` · `POST …/chat` · `GET …/council` ·
`GET …/journal` + `POST …/journal/{inscribe,add}` · `GET …/chronicle` · `GET …/judgment`
+ `POST …/judgment/speak` · `POST …/report`(+`/full`,`/email`,`/digest/email`) +
`GET/PATCH/DELETE …/reports…` · `POST …/reach-out` · `GET /api/constellation` ·
`POST /api/divergence` · `GET /api/email/status` · memory + affinity + recognition routes.

## Easter eggs
See **[docs/EASTER_EGGS.md](EASTER_EGGS.md)** — the maintained list (soul-taps, Konami,
corner code, Sound-Test jam, lore spam, character emotes, the Genocide hidden room, and
the chat word-eggs). All pure UI, never touching the wall.

---

## Deltarune (one app, two games)
Drop `filech1_0` (from `%LocalAppData%\DELTARUNE`) into the save slot — detected by
filename. `deltarune_parser.py` applies the parser-truth law (only corroborated lines
named: player name, Dark Dollars; the rest raw); `deltarune_truth.py` produces a
SaveTruth-compatible truth (route honestly `undetermined` — Ch1's Pacifist/Violent
isn't corroborated from flags yet). The registry is game-aware: 8 Ch1 voices (Susie,
Ralsei, Lancer, Noelle, King, Rouxls Kaard, Jevil, Seam) plus **Hometown personas**
for Toriel/Asgore/Alphys/Sans. A Deltarune save flips the console into **Dark World
mode** (violet accents via scoped `--ember` variables), swaps the roster, facts, lore
and quote cards, starters, and prefers a `dark-world.mp3` bed (silent-safe fallback).
**Across Two Worlds** (`crossave.build_two_worlds_grounding`): once saves from both
games exist, the returning faces feel the other universe — its facts clearly labelled
SACRED, the conceit FREE, never asserted as this world's truth. The Two-Save
Divergence picker works cross-world ("TWO SAVE FILES FROM TWO WORLDS, THE SAME HANDS").

## Testing & CI
- `pytest -q` — backend suite (263+ tests; mocks the LLM, keyword-only RAG).
- `python -m tools.voice_eval --min 1.0` — adversarial two-bucket-wall gate.
- `python -m tools.lore_eval --min 1.0` — lore recall gate.
- `tools/frontend_smoke.py` — headless-browser smoke over the built UI (every view, chat,
  Sound Test, master mute, an Easter egg, zero console errors). **A CI merge gate** — see
  `.github/workflows/ci.yml` (`syntax + pytest` and `frontend smoke` jobs).

## Guardrails
1. SaveTruth first (facts are sacred). 2. Read-only saves; unknowns → `null`.
3. Route honesty (ambiguous → `undetermined`). 4. Two-bucket wall.
5. DB ADD-only (except the managed reports history). 6. Generated art/audio is gitignored —
   the repo stays asset-free. 7. Always run `pytest -q` before committing.
