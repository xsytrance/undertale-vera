#!/usr/bin/env python3
"""RAG lore engine — world knowledge for the FREE bucket.

Ported pattern from fft-psx-vera (rag_query_engine.py + knowledge collections),
adapted to undertale-vera and held behind the two-bucket wall:

  - This retrieves GENERAL WORLD LORE (characters, areas, events) so a character
    can speak knowledgeably about the Underground.
  - It is BUCKET B (FREE). Retrieved lore may NEVER assert the player's save state
    (route / LOVE / kills). The blueprint's hard rule: "RAG recommendations must
    never masquerade as current save state." `format_lore_grounding` says so in
    writing, and lore is injected AFTER the sacred SaveTruth block.

Two backends, chosen automatically:
  - VECTOR (full RAG): ChromaDB + embeddings, when the libs are installed and an
    index has been built (`python3 knowledge_ingest.py`).
  - KEYWORD (fallback): a pure, dependency-free overlap retriever over the same
    JSON collections. Always available — so the app runs and the tests pass with
    NO heavy deps, exactly like the LLM client degrades gracefully.

Collections live in knowledge/collections/*.json (committed). The vector index in
knowledge/chroma_db/ is gitignored (rebuildable from the collections).
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Any, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTIONS_DIR = os.environ.get(
    "UNDERTALE_VERA_KB", os.path.join(HERE, "knowledge", "collections")
)
CHROMA_DIR = os.path.join(HERE, "knowledge", "chroma_db")
CHROMA_COLLECTION = "undertale_lore"
EMBED_MODEL = os.environ.get("UNDERTALE_VERA_EMBED_MODEL", "all-MiniLM-L6-v2")

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_WORD.findall((s or "").lower()))


def load_documents(collections_dir: str = COLLECTIONS_DIR) -> list[dict[str, Any]]:
    """Flatten every knowledge/collections/*.json into a list of lore docs."""
    docs: list[dict[str, Any]] = []
    for path in sorted(glob.glob(os.path.join(collections_dir, "*.json"))):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for d in data.get("docs", []):
            if d.get("id") and d.get("text"):
                docs.append({
                    "id": d["id"],
                    "type": d.get("type", "lore"),
                    "title": d.get("title", d["id"]),
                    "character": d.get("character"),
                    "tags": list(d.get("tags", [])),
                    "text": d["text"],
                })
    return docs


# ── keyword backend (always available) ───────────────────────────────────────

def keyword_retrieve(
    query: str,
    character: Optional[str] = None,
    k: int = 4,
    docs: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """Pure overlap retriever. Deterministic; no external deps."""
    docs = docs if docs is not None else load_documents()
    q = _tokens(query)
    if character:
        q |= _tokens(character)
    if not q:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    for d in docs:
        tag_tokens = set()
        for t in d["tags"]:
            tag_tokens |= _tokens(t)
        text_tokens = _tokens(d["text"]) | _tokens(d["title"])
        score = 2.0 * len(q & tag_tokens) + 1.0 * len(q & text_tokens)
        if character and d.get("character") and _tokens(d["character"]) <= q:
            score += 3.0  # boost the character's own lore
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [d for _, d in scored[:k]]


# ── vector backend (full RAG; lazy, optional) ────────────────────────────────

def _vector_collection():
    """Return a populated Chroma collection, or None if unavailable/empty."""
    try:
        import chromadb  # lazy: the core app/tests never require it
    except ImportError:
        return None
    if not os.path.isdir(CHROMA_DIR):
        return None
    try:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        col = client.get_collection(CHROMA_COLLECTION)
        if col.count() == 0:
            return None
        return col
    except Exception:  # noqa: BLE001 - any backend hiccup → fall back to keyword
        return None


def vector_retrieve(query: str, character: Optional[str] = None, k: int = 4):
    """Embed-and-query via Chroma. Returns None when the vector backend isn't ready."""
    col = _vector_collection()
    if col is None:
        return None
    q = query if not character else f"{character}: {query}"
    try:
        res = col.query(query_texts=[q], n_results=k)
    except Exception:  # noqa: BLE001
        return None
    out: list[dict[str, Any]] = []
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    texts = (res.get("documents") or [[]])[0]
    for i, doc_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        out.append({
            "id": doc_id,
            "type": meta.get("type", "lore"),
            "title": meta.get("title", doc_id),
            "character": meta.get("character"),
            "tags": (meta.get("tags") or "").split(",") if meta.get("tags") else [],
            "text": texts[i] if i < len(texts) else "",
        })
    return out


def retrieve(query: str, character: Optional[str] = None, k: int = 4) -> list[dict[str, Any]]:
    """Retrieve top-k lore docs. Prefers the vector backend; falls back to keyword."""
    v = vector_retrieve(query, character, k)
    if v is not None:
        return v
    return keyword_retrieve(query, character, k)


def backend_in_use() -> str:
    return "vector" if _vector_collection() is not None else "keyword"


# ── grounding render (the wall, in writing) ──────────────────────────────────

def format_lore_grounding(docs: list[dict[str, Any]] | None) -> str:
    """Render retrieved lore as a labeled FREE-bucket block. '' when no docs.

    Returns '' for an empty result so the no-lore grounding is byte-identical to
    the baseline (same regression discipline as memory/remembrance).
    """
    docs = list(docs or [])
    if not docs:
        return ""
    lines = [
        "── WORLD KNOWLEDGE (general lore about the Underground — NOT this player's save) ──",
        "Background you may draw on to speak knowledgeably about the world. This is "
        "general lore, not a record of what THIS player did: it can NEVER establish "
        "or contradict the save's route, LOVE, or kills — those come only from the "
        "SAVE FILE block above. Use it for colour and context, not as save-fact.",
    ]
    for d in docs:
        lines.append(f"• {d['title']}: {d['text']}")
    return "\n".join(lines)
