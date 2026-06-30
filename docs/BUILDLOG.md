# BUILDLOG — undertale-vera

## Spine 0 — "The Save Remembers" (scaffold + grounded character chat)

New MultiVera instantiation for Undertale, mirroring fft-psx-vera's architecture.
Borrowed the portable spine; did **not** copy FFT-specific logic.

### STEP 0 — Recon + port plan
Read fft-psx-vera (read-only). Identified portable spine vs FFT-only parts.
Reported the plan + repo structure before writing code → `docs/PORT_PLAN.md`.

### STEP 1 — Undertale save parser (parser-truth, read-only)
- `save_parser.py`: parses `file0` (line-indexed) + `undertale.ini` (sections).
  Only documented, version-stable fields get meaning (name, LOVE, max HP, named
  `[General]` keys); everything else preserved raw and left `null`. Unexpected
  structure → warnings, never a crash. No mutation helpers by design.
- `route_detection.py`: route derived from real signals (LOVE, kills). Ambiguous
  → `undetermined`, never guessed. Honest scope note re: version-dependent flags.
- `save_truth.py`: normalized `undertale-savetruth-v1` schema with `route` block +
  `prompt_contract` (`save_truth_wins`, high-risk fields). `validate_save_truth`
  collects problems without throwing.
- Verified against synthetic fixtures (Pacifist/Neutral/Genocide/ambiguous).

### STEP 2 — Grounded character chat
- `prompt_builder.py`: the two-bucket wall — SaveTruth hard-facts block (SACRED)
  anchored above the free personality/voice and Living-Memory recollections. Rules
  forbid inventing name/LOVE/route/kills; `undetermined` must be voiced as such.
- `character_config.py`: Undertale character registry (Sans/Toriel/Papyrus/Flowey/
  Undyne) in our own accent — flagged for canonical-voice review.
- `living_memory.py`: ask/remember/recall ported near-verbatim (pure fns); FFT
  Brave/Faith stat-seeding dropped. `format_memory_grounding` returns "" at zero
  memories → byte-identical baseline (regression-tested).
- `llm_client.py`: Anthropic Claude (`claude-opus-4-8`), adaptive thinking +
  effort, fully mockable; graceful degradation when no model is reachable.
- `undertale_vera_app.py`: FastAPI spine — upload→truth, save-truth, characters,
  grounded chat, Living-Memory endpoints, static/SPA serving.

### STEP 3 — Determination Chronicle style layer
- `static/css/determination.css`: obsidian field + ember/brass/crimson, the
  reinterpreted ember-gem SOUL sigil (not the red heart), engraved-plate dialogue
  vessel with typewriter ink-reveal, relic-framed museum-lit portraits,
  Determination-red as a rare accent.
- `comfy_workflows/portrait_undertale.json` + `tools/generate_sample_portraits.py`:
  the pixel-portrait pipeline (new style LoRA) + a placeholder renderer. Generated
  2–3 sample relic portraits (gitignored) as proof for Egi's review.
- `static/js/music.js`: global music layer ported React→vanilla, with a
  route-aware seed (`setRoute`) for the next beat.

### STEP 4 — Inspector (inherited QA harness)
- `inspector.py`: ported wholesale. Registered undertale-vera surfaces + required
  assets. Playwright engine when available; pure-HTTP fallback so it runs day one.
  Deterministic sweep passes against the live app.

### STEP 5 — Docs + roadmap
- `docs/SAVE_FORMAT.md`, `docs/ART_DIRECTION.md`, `docs/PORT_PLAN.md`, this log,
  `docs/ROADMAP.md`.

### Verification
- `pytest -q`: **19 passed** (parser, route, save-truth, two-bucket wall, chat).
- Live smoke: app boots, Inspector sweep passes, `/api/health` + `/api/characters`
  respond, both static assets serve.

### Hygiene
Committed: scaffold + parser + chat + style layer + Inspector + sample asset
references + docs. Generated art is gitignored (never batch-committed).
fft-psx-vera left untouched (read-only reference).

## Beat 1 — Route-aware CONSCIENCE
Companion demeanor now shifts by route (the first roadmap next-beat).
- `character_config.py`: added a `route_demeanor` map per character (ADD-only) —
  how each carries themselves under Pacifist / Neutral / Genocide / undetermined.
- `prompt_builder.py`: `build_demeanor_block` injects demeanor into the FREE
  bucket, shaped by the SACRED route (the same way FFT disposition was shaped by
  Brave/Faith). Tone only — it never asserts a new save-fact, and an absent/
  unknown route yields "" so the zero-demeanor grounding stays byte-identical.
- `tests/conscience_test.py`: demeanor shifts by route, undetermined stays honest,
  the block is framed tone-only, and no-demeanor preserves the baseline.
- Verified: `pytest -q` → **23 passing**. The two-bucket wall still holds.

Route-aware music is already functional at the layer level (`MusicLayer.setRoute`
+ per-route bed); binding it to a live save is a frontend task for a later UI beat.

## Beat 2 — "It Remembers" (the save-aware ledger)
Characters now reference the player's ACTUAL recorded state across visits — the
morally-loaded save-aware angle. Bucket A (SACRED), ADD-only.
- `ledger.py` (pure): `snapshot_fields_from_truth`, `summarize_change` (honest
  deltas only — never claims a change when a value is unknown or equal), and
  `build_remembrance_grounding` (SACRED block; "" below two visits so the
  single-visit baseline is byte-identical).
- `backend/models.py`: `SaveSnapshot` table — one immutable row per reading,
  `counter` = per-project visit number, never overwritten/wiped.
- `undertale_vera_app.py`: record snapshot #1 on `/api/upload`; new
  `POST /api/projects/{id}/refresh-save` (a return visit — re-read, update current
  truth, APPEND a snapshot) and `GET /api/projects/{id}/save-memory` (the ledger).
  Chat injects the remembrance grounding (SACRED) into the prompt.
- `prompt_builder.build_system_prompt`: new `remembrance` slot, placed with the
  facts (after the save block), not the free voice.
- `tests/ledger_test.py`: real deltas, no-claim-when-unknown, additivity across
  visits (prior snapshot untouched), chat grounding includes remembrance, and a
  memory write never writes the Bucket A ledger.
- Verified: `pytest -q` → **30 passing**.

## Beat 4 — The Judgment beat
A Sans-style judgment surface reads the morally-loaded save back to the player.
The most SACRED-leaning surface — facts verbatim, unknowns named, nothing invented.
- `judgment.py` (pure): `build_judgment` returns `facts` (verbatim from SaveTruth),
  a `verdict` tone classification derived from the route (free flavour in our own
  accent, asserts no new fact), `honest_gaps` (the unknowns, named explicitly), and
  the SACRED remembrance deltas. `undetermined` → the open verdict, never guessed.
- `undertale_vera_app.py`: `GET /api/projects/{id}/judgment` (deterministic) and
  `POST /api/projects/{id}/judgment/speak` (in-voice via the LLM, grounded; degrades
  to the deterministic verdict line when no model is reachable).
- `tests/judgment_test.py`: verdict tracks route, facts verbatim, unknowns named,
  structured + spoken endpoints, graceful degradation.
- Verified: `pytest -q` → **36 passing**.

## Beat 3 + Frontend UI — the visible end-to-end app
A dependency-free, no-build frontend on the static shell ties every beat together
and binds route-aware music to the live save.
- `static/index.html` + `static/js/app.js`: upload (`file0`/`undertale.ini`) →
  SaveTruth summary with the route badge → character roster (relic portraits) →
  grounded chat (dialogue vessel + typewriter ink-reveal) → the Judgment screen
  (deterministic readout + "let them say it") → return-visit refresh-save showing
  the remembrance deltas. Reuses the Determination Chronicle CSS (extended with
  in-palette panels/buttons/inputs).
- Route-aware music (Beat 3) now bound: `app.js` calls `MusicLayer.setRoute(route)`
  from the live SaveTruth route, and tints the header soul-sigil Determination-red
  on the Genocide beat.
- `inspector.py`: registered `/js/app.js`; added a `UNDERTALE_VERA_CHROMIUM` pinned
  browser override (for PLAYWRIGHT_BROWSERS_PATH boxes) and filtered external-CDN
  console noise (font CDN failures aren't app defects; CSS ships serif fallbacks).
- Verified in a REAL browser (Chromium via Playwright): upload → route badge →
  roster → chat panel → judgment → refresh→remembrance all pass; Inspector
  Playwright sweep is green (0 failures, no console errors at mobile + desktop).

## Polish — save shelf + persisted transcripts
- `backend/models.py`: `Conversation` table (per project+character chat log — a
  RECORD, distinct from Bucket-B `CharacterMemory` and the SACRED `SaveSnapshot`).
- `undertale_vera_app.py`: `GET /api/projects` (the save shelf, newest first, with
  a route summary), `GET /api/projects/{id}/conversations/{character}` (load a
  persisted transcript), and `chat` now appends each turn so conversations survive
  a reload.
- Frontend: a "Your saves" shelf to switch between read saves; selecting a
  character loads its persisted transcript from the server.
- `inspector.py`: registered the `/api/projects` surface.
- `tests/projects_test.py`: shelf lists saves with route, transcripts persist
  across calls, transcripts are per-character.
- Verified: `pytest -q` → **39 passing**; Inspector green.

## RAG lore layer — world knowledge (FREE bucket)
Characters can now draw on curated Underground lore without hallucinating, behind
the two-bucket wall.
- `knowledge/collections/*.json`: curated lore (characters/locations/events) in our
  own words, ADD-only, flagged for human review.
- `rag_engine.py`: retrieval with two auto-selected backends — VECTOR (ChromaDB +
  `all-MiniLM-L6-v2` embeddings) when deps+index exist, else a pure KEYWORD fallback
  (so the app/tests run with no heavy deps). `format_lore_grounding` carries the
  wall in writing; "" on no hits keeps the baseline byte-identical.
- `knowledge_ingest.py` + `requirements-rag.txt`: build the vector index
  (gitignored, rebuildable). `GET /api/lore?q=` exposes retrieval for audit.
- Wiring: chat injects lore into the FREE bucket, AFTER the sacred SaveTruth +
  remembrance blocks; lore can never assert a save-fact.
- `tests/rag_test.py`: retrieval, the wall, chat injection, baseline preservation.
- Verified: `pytest -q` → **50 passing** (keyword path); the VECTOR index was built
  here with ChromaDB and confirmed to do semantic retrieval (e.g. "who weighs my
  sins at the very end" → Sans). See `docs/KNOWLEDGE_SYSTEM.md`.

## Corpus-audit tool + lore expansion
- `tools/corpus_audit.py`: a repeatable parser+route sweep over any save folder
  (real folder-per-save OR flat fixture layout) → coverage report (parse count,
  per-label route distribution, LOVE range, undetermined count, warnings/structure
  issues). Read-only; never commits/copies save data. `tests/corpus_audit_test.py`
  covers discovery + the report. Verified against a real 64-save corpus: 64/64
  parsed, 0 warnings, 0 structure issues; routes honest (Pacifist saves → Pacifist;
  mid-genocide-run saves → Neutral until the LOVE 20 ceiling → Genocide).
- Lore expansion: `knowledge/collections/items.json` (consumables/weapons/armor),
  `npcs.json` (Napstablook, Temmie, Muffet, the dogs, Monster Kid, …), and more
  `events.json` concepts (SAVE points, human SOULs, the True Lab, "stay
  determined"). 37 lore docs total; vector index rebuilt and confirmed semantic.
- Verified: `pytest -q` → **53 passing**.

## Route-gated lore + retrieval eval (#1 + #4)
- Route gating (#1): lore docs may carry `routes` / `spoiler`; `rag_engine.doc_allowed`
  gates visibility by the player's REAL route (from SaveTruth) — a doc shows only on
  its route, spoilers hide until the route is known, absent = universal. Chat passes
  `SaveTruth.route` into `retrieve()`; `/api/lore?route=` exposes it. This gates WHICH
  world-knowledge is visible, never asserting the route as a fact (wall intact).
  Demonstrable docs added: True Lab + dates (Pacifist), the empty-path resolve
  (Genocide). knowledge_ingest stores routes/spoiler in vector metadata.
- Eval harness (#4): `knowledge/eval.json` (query -> expected doc ids; `route` /
  `expect_absent` for gating) + `tools/lore_eval.py` (recall@k, `--min` gate). Guards
  against retrieval regressions as the KB grows.
- Tests: `tests/rag_test.py` route-gating cases; `tests/lore_eval_test.py` runs the
  eval on the deterministic keyword backend (100%).
- Verified: `pytest -q` → **58 passing**; `lore_eval` → 12/12 on BOTH the keyword and
  vector backends (route gating confirmed with real embeddings).

## Hallucination guard + provenance overlay (the wall, made visible)
The two-bucket wall is now enforced AND visible at the reply level.
- `hallucination_guard.py` (pure): `check_response(reply, save_truth)` scans the
  model's ACTUAL reply for claims that contradict the SACRED facts (route / LOVE /
  kills) and flags them. Conservative (clear second-person assertions only — no
  false positives on loose talk) and ADVISORY (it never rewrites the model; the
  prompt stays the primary wall). Closes the blueprint's loop: verify the fact
  survives live generation, not just prompt assembly.
- `provenance.py` (pure): `build_provenance(...)` reports, per reply, the SACRED
  facts in play vs the FREE sources that coloured it (voice, retrieved lore titles,
  memory, remembrance) — plus the guard verdict.
- Chat endpoint returns `guard` + `provenance`; `static/js/app.js` renders a
  provenance overlay under each reply (SACRED chips / FREE chips / ✓ grounded or
  ⚠ contradicts-save), styled in the Determination Chronicle palette.
- `tests/hallucination_guard_test.py`: route/LOVE/kills contradictions flagged,
  matching facts pass, undetermined-route assertions caught, provenance shape, and
  the chat response carries both (incl. a misbehaving-model case the guard catches).
- Verified: `pytest -q` → **67 passing**; browser-confirmed the overlay renders.

## Sans the save-aware judge — the "path turned" event (SACRED ledger history)
Sans is canonically aware of saving, loading, and resets. The ledger already
records every reading; now HE (and only he) can speak to it.
- `ledger.detect_route_turn(snapshots)` (pure): walks consecutive readings and
  returns the latest real route CHANGE (`{from, to, visit}`) — e.g. Pacifist →
  Genocide — or `None` when the route is stable, unknown, or there's one reading.
  Derived only from recorded routes; never inferred.
- `ledger.build_sans_awareness(snapshots)` (pure): a SACRED grounding block, Sans-
  only, surfacing the parser-confirmed reading count and any route turn, framed so
  he may notice them in his own voice. `""` with fewer than two readings (nothing
  to have noticed yet) — keeps the single-visit baseline byte-identical.
- Chat endpoint appends the Sans block to `remembrance` ONLY for `name:sans`; both
  chat and refresh-save responses now carry `path_turn` for the UI overlay.
- `static/js/app.js`: a SACRED "↳ path turned: X → Y" chip in the provenance row
  when a turn is recorded.
- `tests/sans_awareness_test.py`: pure detect_route_turn (none/stable/detected/
  latest/unknown-ignored) and build_sans_awareness (empty/visit-count/turn), plus
  app wiring (refresh surfaces path_turn; Sans chat carries the block, Toriel does
  not; path_turn rides every chat response).
- Verified: `pytest -q` → **78 passing**.

## Real CI — the wall as a merge gate (GitHub Actions)
Every prior PR shipped with `total_count: 0` checks — the suite was an honour
system. Now it gates merges.
- `.github/workflows/ci.yml`: on push/PR to `main`, sets up Python 3.11, installs
  ONLY `requirements.txt` + pytest (the suite mocks the LLM and the RAG layer
  falls back to a pure keyword retriever, so the heavy `requirements-rag.txt`
  vector deps are deliberately excluded — fast, deterministic, no network/model).
  Steps: `py_compile *.py backend/*.py` (syntax) → `pytest -q`. `ANTHROPIC_API_KEY`
  is empty by design; no chat test needs a live key. Concurrency-cancels superseded
  runs; least-privilege `contents: read`.
- README gets a CI status badge.
- Verified by reproducing CI exactly in a clean venv (core deps only): py_compile
  OK, **78 passed** — confirms the green path doesn't depend on the dev box's
  pre-installed chromadb/playwright.

## Canonical-voice adversarial eval — the wall under attack
A red-team harness that attacks the two-bucket wall directly, then gates on it.
- `knowledge/adversarial.json`: a corpus pairing each save's SACRED facts with a
  provocation engineered to bait fabrication, the `bait_reply` a weak/jailbroken
  model might emit (the guard MUST flag it), and a `grounded_reply` that honours
  the save (the guard MUST pass it). Spans every fabrication type (route on
  Pacifist/Genocide/undetermined, LOVE inflation, kill inflation) across the cast.
  All wording is ours — no Undertale script is reproduced.
- `tools/voice_eval.py` (pure, dependency-injectable like `lore_eval`): scores two
  enforceable, offline dimensions per case — (A) GUARD: bait flagged with the right
  type AND grounded reply clean; (B) PROMPT: the assembled system prompt carries the
  attacked sacred fact + the anti-invention RULES, and the provocation never leaks
  into it. `--min` gate; `python -m tools.voice_eval --min 1.0`.
- **The eval earned its keep immediately**: it surfaced a real guard evasion —
  "your LOVE has climbed to 20" slipped past the adjacent-only LOVE regex. Closed
  with a tightly-bounded connector pattern (`_LOVE_RE3`: a `to/now/reached/hit/at`
  must sit right before the number, no digit/sentence-break intervening) so the
  clear fabrication is caught WITHOUT false-flagging "LOVE is 1, but room 20…".
- Tests: `tests/voice_eval_test.py` (100% gate + a planted-lie negative control
  proving the harness has teeth) and two new `hallucination_guard_test` cases (the
  evasion is caught; the separated number is not).
- CI runs the adversarial + lore gates as their own steps (both 100% on the
  keyword backend, verified in a clean venv).
- Verified: `pytest -q` → **85 passing**; `voice_eval --min 1.0` → 8/8.

## Data-driven parser expansion — the real corpus as ground truth
Promoted three file0 indices from `unknown` → documented, justified by evidence
from a real 64-save corpus (re-uploaded by the user), never by guessing.
- `tools/parser_expand.py`: the sanctioned expansion engine. For each documented
  `[General]` key it scans every file0 index across the corpus and proposes a
  mapping ONLY at 100% agreement over a meaningful sample (whitespace/quote/float
  tolerant compare). On the 64-save corpus it PROMOTED `kills↔file0[11]`,
  `fun↔file0[35]`, `room↔file0[547]` (all 64/64), reconfirmed `love↔file0[1]`
  (64/64), and correctly REFUSED `time` (58% — it drifts between the file0 snapshot
  and the ini write). One counterexample = no claim.
- `save_parser.py`: indices 11/35/547 added to `FILE0_KNOWN_FIELDS` (confidence
  "high"), decoded into new `kills`/`fun`/`room` fields with range validation
  (absent/implausible → None, no warning — same honest-silence policy as max_hp).
- Cross-source corroboration (`save_parser.corroborate`): for fields in BOTH
  file0 and the ini (love/kills/room/fun), the two independent reads are checked —
  AGREE → confidence promoted to "confirmed"; DISAGREE → keep the file0 (save-slot)
  value, drop to "low", warn (likely edited save). Never silently picks/averages.
  Validated across the corpus: 256/256 field-checks agree, zero conflicts.
- `save_truth.py`: additive `corroboration` block + kills/fun/room in
  `parser_confidence` (schema v1 unchanged; existing assertions intact).
- Synthetic genocide/neutral fixtures made internally consistent (file0[11] now
  matches their ini Kills) so they model real, un-edited saves.
- Tests: `tests/parser_expand_test.py` (engine promotes a corroborated index,
  refuses noisy/under-sampled ones) and `tests/corroboration_test.py` (new indices
  decode; agreement→confirmed; disagreement→edited-save warning; file0-only→no
  promotion; implausible→null). `docs/SAVE_FORMAT.md` documents all of it.
- Verified: `pytest -q` → **95 passing**; engine + corroboration re-run on the
  live 64-save corpus.

## More parse mining — boss-kill flags confirm Genocide (corpus + the Internet)
Mined the undertale.ini plot-flag space, cross-checked it against community docs,
and turned the result into a sharper, still-honest route detector.
- `tools/flag_mine.py`: the ini analog of `parser_expand.py`. Groups a
  route-labelled corpus and tags flags that separate routes. On the 64-save corpus
  it found `[Toriel] TK` and `[Papyrus] PK` set in Genocide saves and **0/49**
  Pacifist runs (plus the Pacifist-side spare flags `TS`/`PS`/`PD`).
- Internet cross-check (pcy.ulyssis.be, CYBERPEDIA, Undertale Wiki) CONFIRMED
  `TK = Toriel killed`, `PK = Papyrus killed`, and independently confirmed the
  file0 indices promoted in the previous PR (line 36 = Fun, 548 = room, 549 = time).
  A community claim that file0 line 3 = current HP did NOT survive corpus checking:
  index 2 follows `16+4·LV` across all 64 saves (LV1→20…LV19→92) while index 3 is a
  constant 20 — index 2 is max HP. Promoted `max_hp` medium→**high**; trusted the
  data over the forum.
- `route_detection.py`: `KILL_FLAGS` allow-list + `extract_kill_flags`. A set kill
  flag is a hard "violence occurred" signal — it forms a Neutral floor, promotes
  LOVE 20 to a **confirmed** Genocide (two independent records of total slaughter),
  and if it appears with LOVE 1 exposes a contradiction → undetermined. It never
  upgrades a mid-run save to Genocide (killing some bosses ≠ full clearance), so
  those honestly stay Neutral.
- Corpus effect: the one complete Genocide save → Genocide **confirmed** (was high);
  14 mid-run Genocide saves stay Neutral with explicit kill-flag evidence; **0/49**
  Pacifist saves affected. No over-claiming.
- Tests: `tests/flag_mine_test.py` (discriminative detection, both-route flags
  rejected, leakage threshold, fixture read) + kill-flag cases in
  `route_detection_test.py`. `docs/SAVE_FORMAT.md` documents the flags, the
  community cross-check, and the max_hp correction.
- Verified: `pytest -q` → **105 passing**; flag_mine + detector re-run on the live corpus.

## More mining, mercy side — befriend/date flags grade Pacifist confidence
The kill-flag work had a mirror: the Pacifist signals the old code admitted it
couldn't read. Mined and wired them, still without over-claiming.
- `tools/flag_mine.py` surfaced the date/befriend flags in Pacifist scene order:
  `[Papyrus] PD` (37/49), `[Undyne] UD` (27/49), `[Alphys] AD` (9/49) — all **0/15
  Genocide**. Cross-checked against the True Pacifist Route docs: the dates require
  having killed no one (the Undyne date is gated on it), so these are Pacifist-only.
- `route_detection.py`: `BEFRIEND_FLAGS` + `extract_befriend_flags`. A no-kill run
  (LOVE 1 + 0 kills, no kill flag) WITH a befriend/date flag is reported Pacifist
  **high** — the flags separate a TRUE Pacifist path from a passive no-kill Neutral,
  resolving the exact ambiguity that forced the old medium cap. Early no-kill saves
  with no befriend flags honestly stay **medium**. Befriend flags never *create* a
  Pacifist call (kills / kill flags still override) — they only grade one.
- `SPARE_KILL_PAIRS` + `find_spare_kill_conflicts`: the same character marked BOTH
  spared (TS/PS) and killed (TK/PK) is impossible → `undetermined`. The mercy-side
  mirror of the LOVE/kills contradiction guard (0 such conflicts in the real corpus;
  fires only on edits).
- Corpus effect: Pacifist now splits 37 **high** / 12 **medium** (was 49 medium);
  Genocide unchanged; no route flips, no Genocide/Pacifist cross-contamination.
- Tests: befriend extraction, Pacifist high vs medium, spare/kill contradiction in
  `route_detection_test.py`. `docs/SAVE_FORMAT.md` documents the flags + the wiki
  cross-check + the contradiction guard.
- Verified: `pytest -q` → **109 passing**; detector re-run on the live corpus.

## Per-character disposition — who you killed, spared, or befriended (SACRED)
The flag mining paid its biggest dividend in the chat layer: characters can now
speak to a *real* per-person outcome instead of a generic route.
- `character_disposition.py` (pure): `DISPOSITION_FLAGS` maps each major character
  to its documented, corpus-validated outcome flags — Toriel (tk/ts),
  Papyrus (pk/ps/pd), Undyne (ud), Alphys (ad). `derive_dispositions` returns
  killed / spared / befriended / unknown per character, with precedence (killed +
  mercy both set → `contradicted`, never asserted; befriended outranks spared).
- SACRED grounding: `build_disposition_grounding` / `grounding_from_truth` render a
  "WHO YOU'VE MET" block listing only definite outcomes; "" when nothing is recorded
  (baseline byte-identical). Lives in the SACRED bucket of the prompt (section 2a,
  with the save-facts) — `prompt_builder` gained a `disposition_grounding` param and
  the chat endpoint feeds it from the stored SaveTruth.
- `save_truth` carries an additive `dispositions` block; `provenance` surfaces the
  definite outcomes on the SACRED side and `app.js` renders them as chips.
- Verified on the live corpus: a late Genocide save grounds "Toriel: killed,
  Papyrus: killed" (Sans's brother — he'd know); a late Pacifist grounds everyone
  befriended/spared. No flag → not listed, never guessed.
- Tests: `tests/character_disposition_test.py` (derivation incl. contradiction,
  grounding text, truth-based grounding, provenance, and chat-prompt wiring —
  present with flags, absent without). `docs/SAVE_FORMAT.md` documents the flags.
- Verified: `pytest -q` → **119 passing**.

## Deep cuts — save texture + the Fun-value anomaly (blow their minds)
The richest, most surprising grounding yet — what a save records BEYOND route/stats.
- `save_flavor.py` (pure): derives SACRED "texture" — current **area** (from the
  documented `[General].RoomName`, never from fragile room numbers; None when
  absent), **play time** (frames@30fps → "about N hours"), and Toriel's **pie
  flavour** (`Bscotch` 1=butterscotch/2=cinnamon) — plus the crown jewel, the **Fun
  value** event detector. At documented exact values the Fun value silently gates the
  Gaster Followers (61–63), the Sound Test Room (65), the gray-door Mystery Man (66),
  and the Goner Kid (90+); thresholds cross-checked against the Undertale Wiki +
  CYBERPEDIA. Most values have no event → silent, never invented.
- Grounding: `build_texture_grounding` (area/time/pie, SACRED, for everyone) and
  `build_anomaly_grounding` (the eerie Fun-value truth, gated in the chat layer to
  the save/meta-aware characters Sans & Flowey). Both "" when nothing applies
  (baseline byte-identical). `prompt_builder` gains `texture_grounding` +
  `anomaly_grounding` params (SACRED sections 2c/2d).
- `save_truth` carries `toriel_pie`; `provenance` surfaces area/playtime/fun_event on
  the SACRED side; `app.js` renders area/time chips and a "⌖ anomaly" chip.
- Live-corpus validated: the genocide run's Fun 13 correctly fires the Wrong Number
  Song; the pacifist run's Fun 88 is correctly silent; pie reads cinnamon.
- Tests: `tests/save_flavor_test.py` (area from name only, pie, playtime, every Fun
  tier, anomaly gating to Sans vs Papyrus, texture for all). `docs/SAVE_FORMAT.md`
  documents the Fun table + sources.
- Verified: `pytest -q` → **130 passing**.

## Flowey remembers the RESETS (the other meta-aware voice)
Sans notices repeated readings; Flowey is the original keeper of SAVE/LOAD and
remembers runs no one else can.
- `ledger.build_flowey_awareness(snapshots)`: the Flowey-only mirror of
  `build_sans_awareness` — same parser-confirmed ledger facts (reading count + route
  turn), framed for Flowey's knowing, needling delight in having watched you before.
  "" with a single reading. Wired in the chat endpoint for `name:flowey` only.
- Tests in `tests/sans_awareness_test.py`: pure (empty on single visit; reports
  resets + turn in Flowey's framing) and app (Flowey chat carries the RESETS block;
  Sans's variant is not also present).
- Verified: `pytest -q` → **133 passing**.

## Area, everywhere — room-id fallback (corpus-derived, 64/64)
Area detection relied on [General].RoomName, which the real corpus saves don't carry
— so area was None for all 64. Added a room-id range fallback.
- save_flavor.ROOM_AREA_RANGES: Ruins 1-45, Snowdin 46-82, Waterfall 83-138,
  Hotland 139-195, the CORE 196-218, the King's castle 219-245, the True Lab 246-260.
  Boundaries derived from the corpus by cross-checking each room id against its scene
  label — matched 64/64. area_from_save now prefers the (version-robust) room name
  and falls back to the id ranges; ids outside the validated span -> None.
- Effect: all 64 corpus saves now resolve a sensible area (was 0); the fixture's
  RoomName still wins over its id. Tests in tests/save_flavor_test.py.
- Verified: pytest -q -> 135 passing.

## Pivot to Prime/art — route-reactive scenes + the art drop-in contract
Prepared the codebase to RECEIVE Prime's ComfyUI art with zero rework, and shipped
a route-reactive backdrop that works NOW (before any art).
- `scene_resolver.py` (pure, mirrors avatar_resolver): route → generated backdrop
  at static/assets/scenes/<route>.png, or "" → the frontend keeps its CSS gradient.
  `available_scenes()` + `GET /api/scenes` expose the route→url map.
- Frontend route-reactive backdrop: `static/js/scene.js` (`SceneLayer.setRoute`,
  fetches the art map once), a `#scene-backdrop` layer in index.html, and CSS
  `.scene-<route>` tints in determination.css (Pacifist warm gold, Genocide crimson,
  Neutral violet-grey, undetermined obsidian murk) under an obsidian wash for text
  legibility. Generated scene art fades in over the tint when present. Wired into
  `renderTruth` beside the route-aware music. Browser-verified: all 4 route tints
  render, 0 console errors.
- Generated scenes gitignored (same rule as portraits).
- Hand-off docs: `docs/ASSET_MANIFEST.md` (exact slugs/sizes/format → drop-in
  contract) and `docs/PRIME_BRIEF.md` (the magic prompts — per-character portrait
  prompts, per-route scene prompts, shared style token + negative, LoRA training note).
- Tests: `tests/scene_resolver_test.py` (resolve/normalize/tiny-file/endpoint).
- Verified: `pytest -q` → **141 passing**.

## Speaker portraits in the chat bubbles
Each character reply now carries the speaker's portrait beside it (not just on the
roster), so a face anchors every line.
- `app.js`: messages render as `.msg` rows — a `.bubble-avatar` (the speaker's
  `avatar_url` from /api/characters) beside the `.bubble`. `avatarFor()` looks it up
  from the loaded roster; provenance still rides the bubble. User messages stay
  right (no avatar), character replies left with their portrait.
- `determination.css`: `.msg` row layout + a small museum-lit `.bubble-avatar`
  (brass frame, pixelated) with an ember-gem crest fallback until art lands.
- Drop-in: when Prime's portraits arrive at static/assets/portraits/<slug>.png,
  `resolve_avatar` serves them and the face appears here automatically — no code
  change; crest until then.
- Browser-verified: portrait img renders beside the reply, 0 console errors.

## Scene legibility harness — judge backdrops behind the real text
A 4-up grid can't show how a backdrop fights the parchment ink; this does.
- `tools/preview_scenes.py`: drives the running app via Playwright — reads a fixture
  save so the actual panels + text render, then swaps `SceneLayer.setRoute(route)`
  per route and screenshots each. Tags `[ART]` vs `[gradient]` so we know whether a
  generated scene is in play. Honors `$UNDERTALE_VERA_CHROMIUM`; output to `preview/`
  (gitignored). The real legibility test for each new scene drop from Prime.
- Verified end-to-end against the current gradient state (4 screenshots written).

## Frosted panels — let the route scene read through
With Prime's V3 scene art tested in situ (`tools/preview_scenes.py`), all four
routes are legible behind the live UI — the obsidian wash even tames the bright
Neutral. To stop the panels from fully hiding the scene's central composition, the
app-shell panels are now translucent obsidian + a 3px backdrop blur, so the route
backdrop bleeds THROUGH them for depth while parchment text stays readable. Verified
across all four routes behind real text (title + facts panel + chips). Scene art
itself stays gitignored (delivered out-of-band); only the CSS is committed.

## The scene breathes — slow Ken Burns drift
The route backdrop now drifts slowly (a 52s scale+translate Ken Burns loop, with
overscan so no edge ever shows), so the approved scene art feels alive and its
centred composition wanders gently into view around the frosted panels. Pure CSS,
honours `prefers-reduced-motion`. Browser-verified: animation applies, the texture
visibly shifts between frames, text stays legible, 0 console errors.

## The Chronicle — a save's whole story, exportable (SACRED, facts-only)
The payoff for all the mining: one shareable narrated artifact.
- `chronicle.py` (pure): `build_chronicle(save_truth, snapshots)` renders the save
  into Markdown — the route + confidence, the journey (area, play time, pie), the
  numbers (LOVE, kills), Those You Met (definite dispositions only), What the Save
  Remembers (visit count + path turn, ≥2 readings), the Fun-value Anomaly, and the
  Verdict. Reuses save_flavor / character_disposition / ledger / judgment. Invents
  NOTHING — unknowns render "not recorded" or omit their section; undetermined route
  is named, never filled in.
- `GET /api/projects/{id}/chronicle` → {markdown, title, route}.
- Frontend: an "⤓ Export Chronicle" button in the truth panel downloads it as
  `<title>.md` (vanilla Blob download). Browser-verified end-to-end.
- Tests: `tests/chronicle_test.py` (sections, sacred facts, definite-dispositions-
  only, anomaly gating, unknowns-left-unwritten, remembrance across visits, endpoint
  + 404). Verified on a real corpus genocide save (route confirmed, dispositions,
  Fun anomaly, verdict all rendered).
- Verified: `pytest -q` → **151 passing**.

## The Underground reacts to you — cast, relationships, affinity, Chronicle
A whole batch making the companion deeper and more alive.
- **Expanded cast** (`character_config`, ADD-only): Alphys, Asgore, Mettaton,
  Napstablook join the five — 9 characters, each with tone/personality/route_demeanor
  and a `cares_about` web. Napstablook lore added to the knowledge base.
- **Relational awareness** (`relationships.py`): a speaker is given the SACRED
  recorded fate of those they care about (Sans←Papyrus, Undyne←Alphys, …) and reacts
  in voice — never invented. Injected into chat (prompt section 2a²).
- **Affinity** (`affinity.py`): each character's STANCE toward you —
  warm/wary/grieving/hostile/unreadable — derived from route + self/loved-one fate
  (a tone, never a new fact). `GET /api/projects/{id}/affinities`; the roster shows
  a live stance chip per character ("how the Underground regards you").
- **Chronicle, deepened**: a "How the Underground Regards You" section lists every
  character's stance; the Chronicle now also renders **in-app** (a parchment viewer,
  tiny md→html) alongside the markdown download.
- Tests: `tests/relationships_affinity_test.py` (cast, fates, grounding, affinity by
  route + escalation, endpoints, chat wiring) + chronicle regard-section cases.
  Browser-verified: 9-card roster with stance chips + the in-app Chronicle viewer.
- Verified: `pytest -q` → **164 passing**; lore_eval 12/12.
