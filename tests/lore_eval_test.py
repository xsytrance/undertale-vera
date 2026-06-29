"""Lore retrieval eval harness (#4) — recall@k over the fixed eval set.

Runs against the deterministic KEYWORD backend so the result is identical in CI
(no heavy deps) and locally (where a vector index may exist).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import lore_eval  # noqa: E402

import rag_engine  # noqa: E402


def _keyword_retriever(query, character=None, route=None, k=4):
    return rag_engine.keyword_retrieve(query, character=character, route=route, k=k)


def test_eval_set_passes_on_keyword_backend():
    cases, k = lore_eval.load_cases()
    assert len(cases) >= 10
    rep = lore_eval.run(cases, retriever=_keyword_retriever, k=k)
    # Every case must pass: correct docs retrieved AND gated docs correctly hidden.
    failures = [r for r in rep["results"] if not r["ok"]]
    assert rep["pass_rate"] == 1.0, f"retrieval regressions: {failures}"


def test_report_renders():
    cases, k = lore_eval.load_cases()
    text = lore_eval.format_report(lore_eval.run(cases, retriever=_keyword_retriever, k=k))
    assert "pass-rate" in text
