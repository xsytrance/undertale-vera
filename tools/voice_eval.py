#!/usr/bin/env python3
"""Canonical-voice adversarial eval — red-teams THE WALL.

Where lore_eval guards retrieval, this guards the two-bucket wall under attack.
Each case (knowledge/adversarial.json) pairs a save's SACRED facts with a
provocation engineered to bait fabrication, then checks two enforceable,
deterministic dimensions — no live model required:

  A. GUARD  — `check_response` MUST flag the 'bait_reply' (a weak model's
     fabrication) AND MUST pass the 'grounded_reply' (which honours the save).
     A wall that only catches bait but also cries wolf on honest replies is
     useless, so both halves must hold.
  B. PROMPT — the assembled system prompt MUST carry the sacred facts (the
     attacked field) and the anti-invention RULES, and the provocation text
     MUST NOT leak into it (the user's bait never becomes part of the wall).

Pure + dependency-injectable (mirrors tools/lore_eval.py): `run(cases, ...)`
takes the guard and prompt builders so tests stay deterministic and offline.

Usage:
  python3 tools/voice_eval.py            # full report
  python3 tools/voice_eval.py --min 1.0  # exit nonzero if pass-rate < threshold
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EVAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "knowledge", "adversarial.json")

GuardFn = Callable[[str, dict[str, Any]], dict[str, Any]]
PromptFn = Callable[..., str]


def load_cases(path: str = EVAL_PATH) -> list[dict[str, Any]]:
    data = json.load(open(path, encoding="utf-8"))
    return data.get("cases", [])


def make_truth(save: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal SaveTruth dict from a case's compact `save` block.

    Synthetic by design — these are adversarial scenarios, not parsed files — so
    we assemble the truth shape directly rather than round-tripping the parser.
    """
    return {
        "play_state": {"name": save.get("name"), "love": save.get("love")},
        "route": {"route": save.get("route"), "confidence": "medium"},
        "kills": {"total": save.get("kills")},
    }


# What "the sacred fact is present in the prompt" means, per attacked field.
def _prompt_carries_fact(prompt: str, fabrication: str, save: dict[str, Any]) -> bool:
    p = prompt.lower()
    if fabrication == "love":
        return f"love (lv): {save.get('love')}".lower() in p
    if fabrication == "kills":
        k = save.get("kills")
        token = "unknown" if k is None else str(k)
        return f"recorded kills: {token}".lower() in p
    if fabrication == "route":
        route = save.get("route") or "undetermined"
        return f"route: {route}".lower() in p
    return False


def run(cases: list[dict[str, Any]],
        guard: Optional[GuardFn] = None,
        build_prompt: Optional[PromptFn] = None) -> dict[str, Any]:
    """Evaluate each adversarial case across the GUARD and PROMPT dimensions.

    `guard(reply, save_truth)` and `build_prompt(character, save_truth)` default
    to the real implementations; tests inject them for full determinism.
    """
    if guard is None:
        from hallucination_guard import check_response as guard  # noqa: E402
    if build_prompt is None:
        from prompt_builder import build_system_prompt
        build_prompt = lambda character, truth: build_system_prompt(character, truth)

    results: list[dict[str, Any]] = []
    for c in cases:
        truth = make_truth(c["save"])

        # A. GUARD — bait flagged (with the right fabrication type) + grounded clean.
        bait = guard(c["bait_reply"], truth)
        grounded = guard(c["grounded_reply"], truth)
        bait_caught = (not bait["clean"]) and any(
            i["type"] == c["fabrication"] for i in bait["issues"])
        grounded_clean = grounded["clean"]

        # B. PROMPT — sacred fact present, RULES present, provocation absent.
        prompt = build_prompt(c["character"], truth)
        low = prompt.lower()
        fact_present = _prompt_carries_fact(prompt, c["fabrication"], c["save"])
        rules_present = "never violate" in low or "never invent" in low
        provocation_absent = c["provocation"].lower() not in low

        ok = bait_caught and grounded_clean and fact_present and rules_present and provocation_absent
        results.append({
            "id": c["id"], "character": c["character"], "fabrication": c["fabrication"],
            "bait_caught": bait_caught, "grounded_clean": grounded_clean,
            "fact_present": fact_present, "rules_present": rules_present,
            "provocation_absent": provocation_absent, "ok": ok,
        })

    passed = sum(1 for r in results if r["ok"])
    return {"total": len(results), "passed": passed,
            "pass_rate": (passed / len(results)) if results else 1.0, "results": results}


_FAIL_FLAGS = [
    ("bait_caught", "BAIT-NOT-CAUGHT"),
    ("grounded_clean", "GROUNDED-FALSE-FLAG"),
    ("fact_present", "FACT-MISSING"),
    ("rules_present", "RULES-MISSING"),
    ("provocation_absent", "PROVOCATION-LEAKED"),
]


def format_report(rep: dict[str, Any]) -> str:
    lines = []
    for r in rep["results"]:
        tag = "PASS" if r["ok"] else "FAIL"
        why = "" if r["ok"] else "  " + " ".join(
            label for key, label in _FAIL_FLAGS if not r[key])
        lines.append(f"  {tag} {r['id']:<34} [{r['fabrication']}]{why}")
    lines.append(f"\nadversarial wall pass-rate: {rep['passed']}/{rep['total']} = {rep['pass_rate']:.0%}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Canonical-voice adversarial eval (the wall under attack)")
    ap.add_argument("--min", type=float, default=0.0, help="fail (exit 1) if pass-rate below this")
    args = ap.parse_args()
    rep = run(load_cases())
    print(format_report(rep))
    return 1 if rep["pass_rate"] < args.min else 0


if __name__ == "__main__":
    sys.exit(main())
