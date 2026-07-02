#!/usr/bin/env python3
"""Lore retrieval eval — recall@k over a fixed query → expected-doc set.

As the knowledge base grows from dozens to hundreds of docs, this catches
retrieval regressions (the same discipline the corpus-audit tool brings to saves).
Cases live in knowledge/eval.json:
  - `expect`: every listed doc id must appear in the top-k.
  - `expect_absent`: none of the listed ids may appear (route/spoiler gating).
  - optional `route` / `character` exercise gated, character-aware retrieval.

Usage:
  python3 tools/lore_eval.py            # uses the active backend (vector if built)
  python3 tools/lore_eval.py --min 1.0  # exit nonzero if pass-rate < threshold
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rag_engine  # noqa: E402

EVAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "knowledge", "eval.json")

Retriever = Callable[..., list[dict[str, Any]]]


def load_cases(path: str = EVAL_PATH) -> tuple[list[dict[str, Any]], int]:
    data = json.load(open(path, encoding="utf-8"))
    return data.get("cases", []), int(data.get("_meta", {}).get("k", 4))


def run(cases: list[dict[str, Any]], retriever: Optional[Retriever] = None, k: int = 4) -> dict[str, Any]:
    """Evaluate each case. `retriever(query, character, route, k)` defaults to the
    active backend; tests can pass a keyword-only retriever for determinism."""
    retriever = retriever or rag_engine.retrieve
    results: list[dict[str, Any]] = []
    for c in cases:
        hits = retriever(c["query"], character=c.get("character"), route=c.get("route"), k=k)
        ids = [h["id"] for h in hits]
        expect = c.get("expect", [])
        absent = c.get("expect_absent", [])
        missing = [e for e in expect if e not in ids]
        leaked = [a for a in absent if a in ids]
        ok = not missing and not leaked
        results.append({
            "query": c["query"], "route": c.get("route"),
            "top_k": ids, "missing": missing, "leaked": leaked, "ok": ok,
        })
    passed = sum(1 for r in results if r["ok"])
    return {"total": len(results), "passed": passed,
            "pass_rate": (passed / len(results)) if results else 1.0, "results": results}


def format_report(rep: dict[str, Any]) -> str:
    lines = []
    for r in rep["results"]:
        tag = "PASS" if r["ok"] else "FAIL"
        extra = ""
        if r["missing"]:
            extra += f"  missing={r['missing']}"
        if r["leaked"]:
            extra += f"  LEAKED={r['leaked']}"
        rt = f" [route={r['route']}]" if r["route"] else ""
        lines.append(f"  {tag} {r['query'][:48]!r}{rt}{extra}")
    lines.append(f"\nrecall@k pass-rate: {rep['passed']}/{rep['total']} = {rep['pass_rate']:.0%}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Lore retrieval eval (recall@k)")
    ap.add_argument("--min", type=float, default=0.0, help="fail (exit 1) if pass-rate below this")
    args = ap.parse_args()
    cases, k = load_cases()
    rep = run(cases, k=k)
    print(f"backend: {rag_engine.backend_in_use()}")
    print(format_report(rep))
    return 1 if rep["pass_rate"] < args.min else 0


if __name__ == "__main__":
    sys.exit(main())
