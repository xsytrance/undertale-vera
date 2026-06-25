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
