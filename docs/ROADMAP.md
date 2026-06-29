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
3. ~~**Route-aware music.**~~ ✅ **Shipped.** The frontend now drives
   `MusicLayer.setRoute()` from the live `SaveTruth.route` (ember-field / obsidian-
   calm / determination), via the new save-upload UI.
4. ~~**A Judgment beat.**~~ ✅ **Shipped (Beat 4).** `judgment.py` +
   `GET/POST /api/projects/{id}/judgment[/speak]` read route + LOVE + kills back to
   the player — sacred facts verbatim, unknowns named, verdict derived not guessed,
   in-voice delivery grounded. Covered by `tests/judgment_test.py`.

## RAG lore layer ✅ shipped
Characters now draw on a curated knowledge base of Underground lore (characters,
locations, events) via `rag_engine.py` — full **vector RAG** (ChromaDB + embeddings)
with a dependency-free keyword fallback, wired into the FREE bucket and walled from
SaveTruth. See `docs/KNOWLEDGE_SYSTEM.md`. Next: expand the collections, optional
`sentence-transformers` embeddings, and per-character phase gating.

## Further out
- The save-upload **frontend UI**, the **save shelf** (switch between read saves),
  and **persisted chat transcripts** are all live (vanilla JS, no build). Possible
  follow-ups: per-character avatars wired to real generated portraits, transcript
  export, and a dedicated Judgment-room screen.
- Canonical character-voice review and the Undertale style LoRA (see above) — still
  the main items needing a human.

## Needs human review
- **Canonical character voices** (Sans/Toriel/Papyrus/Flowey/Undyne) — Spine-0
  personalities are our reinterpretation and flagged in `character_config.py`.
- **The Undertale style LoRA** for the ComfyUI pipeline (placeholders stand in).
- **Route-detection scope:** confirming completed Genocide / True Pacifist
  canonically needs version-dependent area/befriend flags — see `docs/SAVE_FORMAT.md`.
- **Any JP localization** — deferred.
