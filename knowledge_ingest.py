#!/usr/bin/env python3
"""Build the vector lore index for undertale-vera (full RAG).

Embeds knowledge/collections/*.json into a persistent ChromaDB collection at
knowledge/chroma_db/ (gitignored — rebuildable from the committed JSON).

Requires the optional RAG deps:  pip install -r requirements-rag.txt
The app and tests do NOT need this — without an index, rag_engine falls back to a
pure keyword retriever.

Usage:
  python3 knowledge_ingest.py            # (re)build the index
  python3 knowledge_ingest.py --stats    # show the current index size
"""
from __future__ import annotations

import argparse
import sys

from rag_engine import (
    CHROMA_COLLECTION,
    CHROMA_DIR,
    EMBED_MODEL,
    load_documents,
)


def _embedding_function():
    """Prefer sentence-transformers; fall back to Chroma's default embedder."""
    try:
        from chromadb.utils import embedding_functions
    except ImportError:
        return None
    try:
        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    except Exception:  # noqa: BLE001 - sentence-transformers/torch not present
        # Chroma's built-in default (ONNX MiniLM) needs no torch.
        return embedding_functions.DefaultEmbeddingFunction()


def ingest() -> int:
    try:
        import chromadb
    except ImportError:
        print("chromadb not installed. Run: pip install -r requirements-rag.txt", file=sys.stderr)
        return 2

    docs = load_documents()
    if not docs:
        print("no lore documents found in knowledge/collections/*.json", file=sys.stderr)
        return 1

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    # Rebuild cleanly so re-ingestion is idempotent.
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:  # noqa: BLE001 - first run: nothing to delete
        pass
    col = client.create_collection(CHROMA_COLLECTION, embedding_function=_embedding_function())

    col.add(
        ids=[d["id"] for d in docs],
        documents=[d["text"] for d in docs],
        metadatas=[{
            "type": d["type"],
            "title": d["title"],
            "character": d["character"] or "",
            "tags": ",".join(d["tags"]),
            "routes": ",".join(d["routes"]) if d.get("routes") else "",
            "spoiler": bool(d.get("spoiler", False)),
        } for d in docs],
    )
    print(f"ingested {len(docs)} lore documents into '{CHROMA_COLLECTION}' at {CHROMA_DIR}")
    return 0


def stats() -> int:
    try:
        import chromadb
        col = chromadb.PersistentClient(path=CHROMA_DIR).get_collection(CHROMA_COLLECTION)
        print(f"'{CHROMA_COLLECTION}': {col.count()} documents")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"no index available ({e}). Build it with: python3 knowledge_ingest.py", file=sys.stderr)
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Build/inspect the undertale-vera lore index")
    ap.add_argument("--stats", action="store_true", help="show index size instead of rebuilding")
    args = ap.parse_args()
    return stats() if args.stats else ingest()


if __name__ == "__main__":
    sys.exit(main())
