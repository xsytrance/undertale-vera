# 🧭 Guided Mode — play beside them

Guided Mode turns Ember into a **live companion for an actual playthrough**: the game
runs in its own window, Ember rides alongside (second monitor, half your screen, or
your phone over Tailscale), and **every time you save in-game** the run advances here —
what changed, where you are, and your chosen party reacting in voice.

> **The hard rule:** Guided Mode is **file-based and read-only**. It never reads game
> memory, never touches the game window, never writes a save. It knows exactly what
> your save files say — nothing more, and it tells you so when the file is silent.

## Quick start
1. Open **🧭 Guided Mode** (Modes menu).
2. **Watch a save folder** — paste the directory your game saves into:
   - Undertale (Linux): `~/.config/UNDERTALE`
   - Undertale (Windows): `%LocalAppData%\UNDERTALE`
   - Deltarune (Windows): `%LocalAppData%\DELTARUNE`
   The folder is remembered and re-watched on every visit.
3. **Pick your party** — tap companion chips (up to 4 ride along; swap anytime).
   As you enter new areas, Ember suggests who belongs ("Undyne knows Waterfall —
   add her?").
4. **Play.** Save in-game whenever you like. Each save becomes a **beat** in the feed:
   `✦ SAVE — Frisk · Pacifist · Snowdin` plus the honest delta ("LOVE rose from 1 to 2",
   "kills went from 0 to 3") — and the party reacts to *exactly those changes*.

## Asking the guide
- **🧭 Where am I?** — a plain summary of what the save shows right now.
- **✨ What now?** — a progress-gated hint, delivered in your lead companion's voice.
- **The spoiler dial** controls how much it says:
  | dial | you get |
  |---|---|
  | 🌶 nudge | a direction, no specifics |
  | 🌶🌶 hint | the shape of the next step, no solution |
  | 🌶🌶🌶 tell me | plainly what to do next |

  Hints come from Ember's own original guide notes (`guide_kb.py`), anchored to what
  the save proves: Undertale hints key off your **parser-derived area**; Deltarune Ch1
  hints key off **corroborated progression facts** (party composition, the Jevil flag).
  A hint never references content beyond your recorded progress — and when the save
  doesn't show enough, the guide says that instead of guessing.

## How it works (the honest pipeline)
```
game writes a save → 2s poller sees the change → waits for the write to SETTLE
  → re-parses (same read-only parsers as upload) → appends a snapshot (ADD-only)
  → beat = ledger.summarize_change(previous, current)  ← the sacred delta
  → SSE → the feed → party reacts via /guided-react (delta lines are SACRED,
    the voice is FREE — the same two-bucket wall as everything else)
```
- Watched files: `file0` (+`undertale.ini` in the digest) and `filech{N}_{0..2}`
  (+`dr.ini`). Backup slots (`filech1_9`) are ignored.
- First sight of a save file **adopts** it as a fresh project; the rail follows the
  run live, and every beat also lands in the character's chat transcript, the
  snapshots Timeline, and (Undertale) the self-filling Journal — a guided run
  becomes a keepsake automatically.
- Party reactions and hints degrade to grounded deterministic text with no model —
  Guided Mode works offline.

## Read-aloud (TTS) — Guided Mode only
Guided Mode can **speak the party's replies and hints aloud** so you can keep your
eyes on the game. It's **off by default** and lives *only* here — the rest of Ember
keeps Undertale's no-voices silence. Toggle **🔊 Speak the party & hints**.

- **Presentation only:** TTS reads text that is *already* grounded (reactions, hints,
  session stories). It never invents or changes a word — the same wall as everywhere.
- **Two engines, auto-selected** (frontend probes `/api/tts/health`):
  - **Kokoro (local neural), preferred** — Ember synthesizes audio itself and plays it
    in *any* browser/OS. This is what makes it audible on Linux (which has no built-in
    browser voices). Each character gets its own Kokoro voice (Sans `am_onyx`, Toriel
    `af_heart`, Asgore `bm_george`, …). Runs in a dedicated `.venv-tts` (python3.11),
    CPU-only, ~1s per short line, no root. Install: `bash tools/setup_tts.sh`.
    Public/shared deployments never expose the synth endpoint.
  - **Browser Web Speech API, fallback** — used when the Kokoro engine isn't installed
    (e.g. Windows, where built-in SAPI voices work out of the box). Per-character
    rate/pitch colour instead of distinct voices.
- **Auto-speak needs no input** — new beats read themselves as they land, so it works
  while you play. **Repeat / Stop / Toggle** are bindable to a **keyboard key** *and* a
  **gamepad button** (press-to-bind, right in the panel — no joy2key needed).
- **The focus caveat (honest):** a browser only receives key/gamepad input while *its*
  window is focused. Auto-speak is unaffected; to press a control mid-game, keep the
  🪟 pop-out companion focused, or map a pad button → key at the OS level (joy2key /
  AntiMicro). This is a browser limitation, not a bug.

## The demo: replay a recorded run
A labelled save corpus plays back through the watcher like a movie:
```bash
# 1) in Guided Mode, watch:  /tmp/guided-demo
# 2) then:
python -m tools.guided_replay --corpus saves/deltarune/chapter1 \
    --dest /tmp/guided-demo --interval 8
```
You'll watch STEPHANIE's whole Chapter 1 happen — the party forming, Susie storming
off and coming back, dark dollars swinging, Jevil falling — with your party reacting.

## API
- `POST /api/guided/watch {path}` · `DELETE /api/guided/watch` · `GET /api/guided/status`
- `GET /api/guided/events` — SSE beats (`adopted` / `save`, with `changes[]` + `area`)
- `POST /api/projects/{id}/guided-react {character, changes[]}` — a delta-grounded
  in-voice reaction (persisted to the transcript)
- `POST /api/projects/{id}/guided-hint {level, character?}` — the hint ladder

## The Companion Pop-out & Session Stories
- **🪟 Pop out** lifts the party, ask bar, and live feed into a slim companion
  window — Document Picture-in-Picture where available (genuinely always-on-top
  over the game), a popup fallback elsewhere. Close it and everything returns.
- **📖 Tonight's story** — your lead companion narrates the session's arc as a
  short second-person story built ONLY from the recorded save beats; keep it in
  the Journal or download it. A guided evening becomes a keepsake.

## Companion-window setups
- **Half-screen / second monitor**: just place the browser next to the game.
- **Phone**: open Ember over Tailscale — the mobile layout is the sidebar.
- A dedicated always-on-top wrapper (Tauri) is a planned later phase.

## Roadmap (the "make it a thing" arc)
1. ✅ Watcher + beats + party reactions + hint ladder (Phases 1–3)
1b. ✅ Read-aloud (TTS), Guided Mode only — local Kokoro neural voice (+ browser
    fallback), per-character voices, key + gamepad bindable (see above)
2. Always-on-top companion window (Tauri) + first-run setup polish
   - Known rough edge: the party rail doesn't yet swap to the Deltarune cast when a
     DR run is adopted (fine for Undertale; fix before the extraction phase).
3. **Extraction**: the game-pack interface (parser · truth · registry · guide ·
   assets) so new games — FFT next — plug into the same Guided engine.
4. **Far horizon — headset companion**: Guided Mode as a floating window on a
   Meta Quest 3 (or similar) beside the player's main screen, so the party rides
   along in a spatial panel while you play. Same read-only, file-based engine;
   just a new surface for the companion.
