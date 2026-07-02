#!/usr/bin/env python3
"""Living Memory — the per-character bond (Bucket B, FREE).

Ported from fft-psx-vera/living_memory.py. The two-bucket wall is identical:

  - Bucket A = SAVE-FACTS (save_truth): SACRED, parser-truth, never invented.
  - Bucket B = RELATIONSHIP-MEMORY (this module): FREE — what the player told a
    character out-of-game, plus the inquisitive ask/remember/recall loop.

Bucket B is injected into grounding ONLY when clearly labeled as out-of-game and
NEVER able to override or substitute for a save-fact (see format_memory_grounding).

DROPPED from the FFT port: seed_personality_base / derive_mood — those read FFT's
Brave/Faith/zodiac/ledger stats, which Undertale does not have. Everything else
(the ask/remember/recall loop and recall-for-grounding) is game-agnostic and ports
verbatim.

This module is PURE (no DB, no network, no clock) — callers pass `now_iso` and ids
in — so the wall and ops are unit-testable and resume-safe.
"""
from __future__ import annotations

import re

# ── relationship memories: what the player told them ─────────────────────────

def normalize_key(name: str | None, slot: int | None = None) -> str:
    """Hybrid character key: 'name:<normalized>' or 'slot:<n>'."""
    n = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    if n and not n.startswith("unknown"):
        return f"name:{n}"
    return f"slot:{slot if slot is not None else 0}"


def add_memory(relationship: list | None, text: str, now_iso: str, new_id: int) -> list:
    """Append a relationship-memory entry (what the player told them)."""
    rel = list(relationship or [])
    t = (text or "").strip()
    if not t:
        return rel
    rel.append({"id": new_id, "text": t[:500], "at": now_iso})
    return rel[-100:]   # bounded growth: keep the most recent 100


def forget(relationship: list | None, mem_id) -> list:
    """Forget one memory by id, or ALL when mem_id == 'all'."""
    rel = list(relationship or [])
    if mem_id == "all":
        return []
    try:
        mid = int(mem_id)
    except (TypeError, ValueError):
        return rel
    return [m for m in rel if m.get("id") != mid]


def next_memory_id(relationship: list | None) -> int:
    rel = relationship or []
    return max((m.get("id", 0) for m in rel), default=0) + 1


# ── inquisitive loop: ask · remember · recall ────────────────────────────────
# Question banks are reinterpreted in our own accent (not copied from Undertale),
# and are route-agnostic so they never assert a save-fact.

QUESTIONS_OPENING = [
    "What made you come down here, of all places?",
    "Is there something you've been wanting to say out loud?",
    "What keeps you walking when the path gets dark?",
    "What do you wish more people understood about you?",
]

QUESTIONS_BUILDING = [
    "What has this place changed in you so far?",
    "Is there a choice you keep turning over in your mind?",
    "What do you want, when all of this is over?",
    "Is there something you've told no one else?",
]

QUESTIONS_DEEP = [
    "Is there something you've never told anyone?",
    "What are you most afraid of finding down here?",
    "Do you trust me?",
    "What do you think I still don't understand about you?",
]

_QUESTION_BANKS: dict[str, list[str]] = {
    "opening": QUESTIONS_OPENING,
    "building": QUESTIONS_BUILDING,
    "deep": QUESTIONS_DEEP,
}


def resolve_tier(bond_depth: int) -> str:
    """Escalate question intimacy as the bond grows."""
    if bond_depth < 3:
        return "opening"
    if bond_depth < 8:
        return "building"
    return "deep"


def pick_question(tier: str, asked_qs: list[str] | None) -> str | None:
    """Next unasked question for a tier; None when exhausted. Deterministic."""
    asked = set(asked_qs or [])
    bank = _QUESTION_BANKS.get(tier) or QUESTIONS_OPENING
    for q in bank:
        if q not in asked:
            return q
    return None


def should_ask(budget: dict | None, now_iso: str, bond_depth: int = 0) -> bool:
    """Should the character pose a question this visit? Anti-clingy valve."""
    b = budget or {}
    used = int(b.get("used", 0))
    max_q = int(b.get("max", 3))
    if used >= max_q:
        return False
    last_asked = b.get("last_asked")
    if last_asked:
        try:
            from datetime import datetime, timedelta
            if (datetime.fromisoformat(now_iso) - datetime.fromisoformat(last_asked)) < timedelta(hours=8):
                return False
        except (ValueError, TypeError):
            pass
    return True


def record_answer(memories: list | None, question: str, answer: str, tier: str, now_iso: str) -> list:
    """Append a Q&A memory (Bucket B only). Bounded to 50 most recent."""
    mems = list(memories or [])
    new_id = max((m.get("id", 0) for m in mems), default=0) + 1
    mems.append({
        "id": new_id,
        "q": (question or "").strip(),
        "a": (answer or "").strip()[:500],
        "ts": now_iso,
        "tier": tier,
    })
    return mems[-50:]


def forget_answer(memories: list | None, mem_id) -> list:
    mems = list(memories or [])
    if mem_id == "all":
        return []
    try:
        mid = int(mem_id)
    except (TypeError, ValueError):
        return mems
    return [m for m in mems if m.get("id") != mid]


def bump_budget(budget: dict | None, question: str, now_iso: str) -> dict:
    b = dict(budget or {"used": 0, "max": 3, "last_asked": None, "tier": "opening", "asked_qs": []})
    b["used"] = int(b.get("used", 0)) + 1
    b["last_asked"] = now_iso
    asked = list(b.get("asked_qs") or [])
    if question not in asked:
        asked.append(question)
    b["asked_qs"] = asked
    return b


def touch_budget_cooldown(budget: dict | None, now_iso: str) -> dict:
    b = dict(budget or {"used": 0, "max": 3, "last_asked": None, "tier": "opening", "asked_qs": []})
    b["last_asked"] = now_iso
    return b


# ── recall for chat grounding (Bucket B → labeled grounding) ──────────────────

def select_memories(memories: list | None, user_message: str, k: int = 5) -> list:
    """Select ≤k most relevant Q&A memories: recency 0.6 + keyword overlap 0.4."""
    mems = list(memories or [])
    if not mems or k <= 0:
        return []
    msg_words = set(re.sub(r"[^a-z0-9 ]", " ", (user_message or "").lower()).split())
    n = len(mems)

    def _score(i: int, m: dict) -> float:
        recency = i / max(n - 1, 1)
        if msg_words:
            q_words = set(re.sub(r"[^a-z0-9 ]", " ", (m.get("q") or "").lower()).split())
            a_words = set(re.sub(r"[^a-z0-9 ]", " ", (m.get("a") or "").lower()).split())
            overlap = len(msg_words & (q_words | a_words)) / len(msg_words)
        else:
            overlap = 0.0
        return recency * 0.6 + overlap * 0.4

    scored = sorted(enumerate(mems), key=lambda t: _score(t[0], t[1]), reverse=True)
    return [m for _, m in scored[:k]]


def format_memory_grounding(qa_memories: list | None, rel_memories: list | None = None) -> str:
    """Render selected memories as a labeled, fenced grounding section.

    Returns '' when both lists are empty — so the grounding is byte-identical to
    the zero-memory baseline (the regression-tested identity from the FFT spine).
    The header carries the two-bucket rule in writing.
    """
    qa = list(qa_memories or [])
    rel = list(rel_memories or [])
    if not qa and not rel:
        return ""

    entry_lines: list[str] = []
    for m in qa:
        q = (m.get("q") or "").strip()
        a = (m.get("a") or "").strip()
        if q and a:
            entry_lines.append(f'You once asked: "{q}" — they said: "{a}"')
    for m in rel:
        t = (m.get("text") or "").strip()
        if t:
            entry_lines.append(f'They once told you: "{t}"')
    if not entry_lines:
        return ""

    header = [
        "── WHAT THEY'VE TOLD YOU (out-of-game — kept apart from the save's facts) ──",
        "These were shared with you personally, outside the Underground's events. "
        "Reference them naturally, only when they fit. Reference ONLY what is listed "
        "here; never invent shared history. These out-of-game exchanges do NOT "
        "substitute for or contradict the save's parser-confirmed facts.",
    ]
    return "\n".join(header + entry_lines)
