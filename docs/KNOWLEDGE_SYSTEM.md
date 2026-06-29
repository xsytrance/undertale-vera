# Knowledge System — RAG lore layer

Gives characters **general world knowledge** about the Underground so they can
speak knowledgeably about places, events, and each other — *without* hallucinating.

## The wall (non-negotiable)
RAG lives entirely in the **FREE bucket**. Retrieved lore is general world
knowledge; it may **never** establish or contradict the player's save state
(route / LOVE / kills). Those come **only** from the SACRED SaveTruth block, which
is injected *above* the lore block in every prompt. The blueprint's hard rule:
*"RAG recommendations must never masquerade as current save state."*
`rag_engine.format_lore_grounding` states this in writing inside the prompt.

## Pieces
- `knowledge/collections/*.json` — the curated lore corpus (characters, locations,
  events/concepts), authored **in our own words** (paraphrased facts, not copied
  text). ADD-only. **Flagged for human review** for canonical accuracy.
- `rag_engine.py` — retrieval with two backends, chosen automatically:
  - **Vector (full RAG):** ChromaDB + embeddings (`all-MiniLM-L6-v2`), used when the
    deps are installed and an index exists.
  - **Keyword (fallback):** a pure, dependency-free overlap retriever over the same
    JSON. Always available — so the app runs and the **test suite passes with no
    heavy deps**, exactly like the LLM client degrades gracefully.
- `knowledge_ingest.py` — builds/rebuilds the vector index from the collections.
- `knowledge/chroma_db/` — the vector index (**gitignored**; rebuildable).

## Build the vector index (optional)
```bash
pip install -r requirements-rag.txt
python3 knowledge_ingest.py          # embeds knowledge/collections/*.json
python3 knowledge_ingest.py --stats  # show index size
```
Without this, retrieval transparently uses the keyword backend.

## How it's wired
On each chat turn, `undertale_vera_app` calls `rag_engine.retrieve(message,
character)` and injects the result via `prompt_builder`'s `lore_grounding` slot —
placed in the FREE bucket, after the sacred SaveTruth + remembrance blocks. Empty
results yield `""`, so the no-lore grounding is byte-identical to the baseline.

## Audit it
`GET /api/lore?q=<query>&character=<name>` returns the retrieved docs and the active
backend — so what the model would see is inspectable (if a fact can't be inspected,
don't trust the model to know it).

## Verified
- Keyword backend + the wall + chat injection: covered by `tests/rag_test.py`
  (runs with no heavy deps).
- Vector backend: built here with ChromaDB (ONNX MiniLM embeddings) and confirmed
  to do semantic retrieval — e.g. "who weighs my sins at the very end" → Sans (the
  judge); "glowing flowers that repeat what you whisper" → Waterfall.

## Next (if retrieval quality needs it)
- Expand the collections (items, more events, area-specific NPCs).
- Swap to `sentence-transformers` embeddings (preferred) once the env supports it.
- Per-character knowledge gating by story phase (the FFT reference pattern).
