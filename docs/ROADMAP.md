# Roadmap — undertale-vera

## Spine 0 (this build) — "The Save Remembers"
Parser + route detection (unknowns→null) · grounded character chat (facts sacred,
Living Memory reused) · Determination Chronicle style layer + 2–3 sample relic
portraits · Inspector inherited & sweeping. **Scaffold + chat only** — no scope creep.

## NEXT beats
1. ~~**Route-aware CONSCIENCE.**~~ ✅ **Shipped (Beat 1).** Per-route demeanor lives
   in `character_config.py` (`route_demeanor`, ADD-only) and is injected by
   `prompt_builder.build_demeanor_block` into the FREE bucket, shaped by the SACRED
   route. Wall intact; covered by `tests/conscience_test.py`.
2. ~~**The "it remembers" save-aware angle.**~~ ✅ **Shipped (Beat 2).** An additive,
   parser-truth `SaveSnapshot` ledger (`ledger.py` + `backend/models.py`) records
   the player's state per visit; `refresh-save` appends a snapshot, `save-memory`
   returns the chronology, and chat injects a SACRED remembrance block so
   characters speak to the player's *actual* recorded changes. Covered by
   `tests/ledger_test.py`.
3. **Route-aware music.** `MusicLayer.setRoute()` is stubbed; bind the ambient bed
   to `SaveTruth.route` (ember-field / obsidian-calm / determination).
4. **A Judgment beat.** A Sans-style judgment surface that reads back the route +
   kills from SaveTruth — sacred facts only, delivered in-voice.

## Needs human review
- **Canonical character voices** (Sans/Toriel/Papyrus/Flowey/Undyne) — Spine-0
  personalities are our reinterpretation and flagged in `character_config.py`.
- **The Undertale style LoRA** for the ComfyUI pipeline (placeholders stand in).
- **Route-detection scope:** confirming completed Genocide / True Pacifist
  canonically needs version-dependent area/befriend flags — see `docs/SAVE_FORMAT.md`.
- **Any JP localization** — deferred.
