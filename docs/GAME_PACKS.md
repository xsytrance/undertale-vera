# Game Packs — how to teach the Vera engine a new game

Ember is two things: a **game-agnostic engine** (the two-bucket wall, grounded chat,
snapshots/remembrance, the Council/Reports/Journal machinery, Guided Mode's watcher +
hint ladder, the audio/emblem systems) and **game packs** that teach it a specific
game. Undertale and Deltarune Chapter 1 are the first two packs, living in-repo;
`fft-psx-vera` is the sibling ancestor. This document is the spec for building the
next one — written from what the first two packs actually required.

> **The covenant every pack signs: FACTS ARE SACRED, FEELINGS ARE FREE.**
> A pack may only assign meaning to save data it can corroborate with evidence.
> Unknowns are `null`. Ambiguity is said out loud. Voice and flavour are free.

## What a pack provides

### 1. A parser (`<game>_parser.py`) — parser-truth law
- **Read-only, never crashes**: malformed input → warnings, not exceptions.
- Detect your save files (`looks_like_<game>(filename)`) — Guided Mode's watcher
  uses this to adopt files it sees.
- Name ONLY corroborated fields; preserve everything else raw
  (`raw_lines` / raw sections) with `confidence` per field
  (`confirmed/high/medium/low/estimated/unknown`).
- **How fields get promoted**: corpus evidence. Collect real saves at labelled
  progression points, then corroborate (see `tools/deltarune_expand.py` — layout
  stability, cross-source correlation against a summary file like `dr.ini`,
  variance maps, pre/post partition flags). Public docs alone rate "medium";
  corpus + cross-source agreement rates "high". Version-guard layout-dependent
  indices (demote honestly when the layout differs).

### 2. A truth builder (`<game>_truth.py`)
Produce a **SaveTruth-compatible** dict — the engine's lingua franca:
`play_state` (name/love/gold/room/…), `kills`, `route {route, confidence, reasons}`,
`confidence`, `warnings`, plus `game: "<id>"` and a game-specific block
(e.g. `deltarune: {party, dark_dollars, jevil_state}`). Rules:
- Map your game's concepts onto the shared seats where honest (Dark Dollars ride
  `gold`); leave seats `None` where the concept doesn't exist (Deltarune has no
  LOVE — never asserted, even though "it's always 1" is lore).
- **Route honesty**: if your game's moral fork isn't derivable from corroborated
  flags, `route = "undetermined"` with the reason stated. Ship that. Upgrade later
  with evidence.

### 3. Characters (entries in `character_config.py`)
ADD-only registry entries with `game: "<id>"`: `tone`, `personality`, `speaks_of`,
`cares_about`, and `route_demeanor` **in your game's own route vocabulary**. All
text is original — reinterpretations in our own accent, never copied dialogue.
Cross-game faces (the same soul in two worlds) use a persona block on the base
entry (see the `deltarune` overlays on Toriel/Asgore/Alphys/Sans) — this is what
powers "Across Two Worlds" recognition.

### 4. A guide chapter (`guide_kb.py`)
Original, spoiler-tiered hints (nudge / hint / tell), anchored ONLY to facts the
parser proves: Undertale anchors on the derived area; Deltarune anchors on party
composition + the Jevil flag. When the save shows too little, the honest answer is
"save again and ask me" — never a guess. No copied walkthrough text, ever.

### 5. Assets (all gitignored — the repo stays asset-free)
- **Emblems**: an original abstract crest per character →
  `static/assets/emblems/<slug>.png` (slug = lowercase, non-alnum → `-`).
- **Music**: a world bed + per-character themes → `static/audio/` following the
  naming seams (`<world-bed>.mp3`, `char-<slug>.mp3`). Missing files fall back
  silently, so packs can ship before their soundtrack. Loop + normalize recipe:
  crossfade the tail into the head (~3-4s) + `loudnorm I=-14` (see the audio memory).
- **Voices**: a synthesized blip profile per character in `static/js/voices.js`
  (waveform/pitch/envelope/quirks — keep fundamentals above ~330 Hz for phones).

### 6. Wiring checklist (what the first two packs touched)
- Upload/watch detection (`/api/upload` + `guided.discover_saves`).
- `list_characters(game)` filtering; prompt persona resolution comes free
  (`build_system_prompt` reads `truth.game`).
- Frontend: shelf badge + world mode class (a scoped CSS-variable re-theme, like
  `body.world-dark`), roster/facts/starters/flavour-card swaps.
- Tests: pure parser tests on real fixtures, truth honesty tests, an end-to-end
  upload test, and a frontend-smoke section. **Both CI gates must stay green.**

## The extraction roadmap
Today the engine and packs share one repo (deliberately — the framework is being
extracted FROM a working product, not designed in the abstract). The planned split:
1. `vera-core` — the engine (wall, truth schema, features, Guided, audio seams).
2. `packs/undertale`, `packs/deltarune-ch1` — the first extractions.
3. `fft-psx` realigned as a pack — the proof the interface generalises.
A pack then becomes: **parser + truth + registry + guide + assets + wiring manifest**.

## Porting checklist (copy me)
- [ ] Save-file detection + read-only parser (warnings, never crashes)
- [ ] Corpus collected at labelled progression points; fields promoted with evidence
- [ ] Truth builder (SaveTruth-compatible; unknowns null; route honest)
- [ ] Character registry entries (original voice; route demeanors; cross-game personas)
- [ ] Guide chapter (3-tier hints, progress-gated, original text)
- [ ] Emblems + music + blip profiles (gitignored; silent-safe fallbacks)
- [ ] Upload + Guided watcher detection wired
- [ ] World mode styling (scoped variables) + shelf badge
- [ ] Tests + smoke section; CI green
