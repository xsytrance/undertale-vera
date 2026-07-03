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
- `llm_client.py` — `generate_reply()`; Ollama (default) + Anthropic + OpenRouter (BYOK)
  backends, plus `none` (Spark mode — deliberately model-less); any failure
  → `LLMUnavailable` → grounded deterministic fallback (never a 500).
- `power_config.py` — the power ladder: the player picks a source (🕯 Spark / 🔑 OpenRouter
  BYOK / 🖥 Ollama / ☁ Anthropic) in the UI (`GET/POST /api/power`, `POST /api/power/test`);
  persisted in gitignored `ember_power.json` (chmod 600 — may hold an API key, which the
  API only ever returns masked). Config wins over `UNDERTALE_VERA_BACKEND`; no config →
  env behaviour unchanged.
- `spark.py` — the model-less voice (🕯 Spark mode / any-backend degrade): a regex
  intent ladder + per-character voice packs deliver grounded, in-voice chat replies
  assembled ONLY from SaveTruth (facts stay verbatim — voice styling never touches
  them; unknowns say so). Deterministic variety via a CRC pick.
- `workshop.py` — the Prompt Workshop's live-true content (`GET /api/workshop`): the real
  assembled example prompt (built by `prompt_builder` against a labelled DEMO truth), the
  section anatomy, and every feature instruction imported from its module (the two inline
  ones are verbatim copies guarded by a drift test).
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
  Easter eggs, the `AudioBus` master. (~2900 lines.)
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

## The star map
"Across Your Saves" opens with a live canvas constellation: every save is a star —
positioned chronologically, banded by route (Pacifist high, Genocide low, Dark
World violet), sized by LOVE, twinkling (motion-gated) — strung on the faint
golden thread of the journey. Hover for the save's facts; click to load it.

## Guided Mode (play beside them)
`guided.py` + the watcher in the app: point Ember at a save directory (read-only —
it NEVER touches game memory or the game window) and a 2s poll adopts each save
slot as a project, then on every settled write appends a snapshot and publishes a
**beat** (the honest `ledger.summarize_change` delta) over SSE
(`/api/guided/events`; `POST/DELETE /api/guided/watch`, `GET /api/guided/status`).
The 🧭 Guided view shows the run as a feed; a pinned **party** (localStorage)
reacts to each beat via reach-out, with area-based party suggestions (Undertale
areas only — Deltarune rooms are honestly unmapped). `tools/guided_replay.py`
replays a labelled corpus through the watcher — a whole playthrough as a demo.
Party reactions are DELTA-AWARE (`POST …/guided-react`: the summarize_change lines
ride the prompt as SACRED facts; the voice reacts to exactly what changed), and the
hint ladder (`guide_kb.py` + `POST …/guided-hint`) serves progress-gated original
hints at three spoiler levels (nudge/hint/tell), anchored to the parser-derived area
(Undertale) or corroborated progression facts (Deltarune) — never beyond the save.
Companion-window model: the game stays its own window; Ember rides alongside
(second monitor / phone via Tailscale). Overlay/Tauri wrapper is a later phase.
Full guide: [docs/GUIDED_MODE.md](GUIDED_MODE.md).

## Game packs (the multi-game vision)
The engine is game-agnostic; games plug in as packs (parser + truth + registry +
guide + assets). **The spec, written from the first two packs:**
[docs/GAME_PACKS.md](GAME_PACKS.md) — includes the extraction roadmap toward
`vera-core` + `packs/*` (FFT next).

## The Commons & How It Works (giving back)
Two public-facing pages: **📚 The Commons** publishes the save-file field maps
(including the corpus-derived Deltarune map — partly new community knowledge), the
evidence method itself, tools/knowledge for people without a local LLM (the
deterministic-fallback pattern), credits, and the **soundtrack as free downloads**
(CC BY 4.0; `/api/community/music` lists what's on disk, `/api/community/music.zip`
streams the lot). **❓ How It Works** explains the whole machine in five
progressively deeper layers — concepts and patterns only, no engine internals.
**🛠 The Prompt Workshop** publishes the prompts themselves, live from the code
(`/api/workshop` + the Suno/art briefs); the machinery around them — Ollama, the
ComfyUI pixel pipeline, local MusicGen, the loop/normalize finishing pass — is
documented in [docs/PIPELINES.md](PIPELINES.md).

## Testing & CI
- `pytest -q` — backend suite (300+ tests; mocks the LLM, keyword-only RAG).
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
