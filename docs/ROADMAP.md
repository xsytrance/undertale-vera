# Roadmap — undertale-vera

## Spine 0 (this build) — "The Save Remembers"
Parser + route detection (unknowns→null) · grounded character chat (facts sacred,
Living Memory reused) · Determination Chronicle style layer + 2–3 sample relic
portraits · Inspector inherited & sweeping. **Scaffold + chat only** — no scope creep.

## NEXT beats
1. **Route-aware CONSCIENCE.** Companion demeanor shifts by route. The seam is
   already in place: `character_config.py` is the ADD-only registry to extend with
   per-route demeanor, and `prompt_builder` already receives the SaveTruth route.
   Wire demeanor into the FREE bucket while keeping the wall intact (route is
   SACRED; demeanor is free).
2. **The "it remembers" save-aware angle.** Lean into the morally-loaded save: a
   character that references the player's *actual* recorded choices across sessions
   (Living Memory already persists per-character; extend the save-snapshot ledger).
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
