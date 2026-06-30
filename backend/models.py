#!/usr/bin/env python3
"""SQLAlchemy models for undertale-vera (minimal Spine-0 surface).

Ported shape from fft-psx-vera/backend/models.py, trimmed to the two tables the
scaffold needs:

  - Project        : an uploaded save (Bucket A — save_data is SACRED).
  - CharacterMemory: per-character Living Memory (Bucket B — FREE).

The two-bucket wall is enforced at the application layer (see the regression
test): memory endpoints write only CharacterMemory.*; they never touch
Project.save_data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    """One uploaded Undertale save. `save_data` holds the normalized SaveTruth
    (Bucket A, SACRED — never mutated by chat or memory endpoints)."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, default="Untitled Save")
    save_data = Column(JSON)  # the SaveTruth dict — SACRED
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)


class SaveSnapshot(Base):
    """The remembrance ledger — Bucket A, SACRED, ADD-only ("the save remembers").

    One immutable row per save reading (upload / refresh). Never overwritten,
    never wiped. `counter` is the per-project visit sequence; load order
    (created_at / id) is the chronology. Mirrors the FFT spine's SaveSnapshot.
    """

    __tablename__ = "save_snapshots"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    counter = Column(Integer, nullable=False, default=1)  # per-project visit number
    name = Column(String(255))
    love = Column(Integer)
    route = Column(String(32))
    route_confidence = Column(String(16))
    total_kills = Column(Integer)
    save_fingerprint = Column(String(64))  # sha256 of the source file(s), when known
    created_at = Column(DateTime, nullable=False, default=_now)  # load order = chronology


class Conversation(Base):
    """Persisted chat transcript per (project, character).

    The grounded chat log so a conversation survives a page reload. This is a
    RECORD of what was said — distinct from CharacterMemory (the curated Bucket-B
    bond) and from SaveSnapshot (the SACRED ledger). `messages` is
    [{role, content, at}].
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    character_key = Column(String(255), nullable=False, index=True)
    messages = Column(JSON)  # [{role, content, at}]
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)


class JournalEntry(Base):
    """The Keepsake Journal — the object the player carries between worlds (ADD-only).

    A persistent, append-only book the characters fill: each row is one immutable
    inscription, written in a character's voice, grounded in the save's truth at the
    time. Never edited, never deleted (DB ADD-only). `counter` is the per-project
    page number; load order is the book's order. It survives sessions and exports to
    markdown — a thing you take with you.
    """

    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    counter = Column(Integer, nullable=False, default=1)   # per-project page number
    author = Column(String(255), nullable=False)           # character display name
    kind = Column(String(32), nullable=False, default="inscription")
    text = Column(String, nullable=False)
    route_context = Column(String(32))                     # the route when written
    created_at = Column(DateTime, nullable=False, default=_now)


class CharacterMemory(Base):
    """Per-(project, character) Living Memory. Bucket B — FREE.

    `personality` JSON holds {base, drift, memories, budget}; `relationship` holds
    [{id, text, at}]. Mirrors the FFT spine's CharacterMemory exactly so the
    ported living_memory.py functions slot in unchanged.
    """

    __tablename__ = "character_memory"

    id = Column(Integer, primary_key=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    character_key = Column(String(255), nullable=False, index=True)  # 'name:<slug>'
    personality = Column(JSON)   # {base, drift, memories, budget}
    relationship = Column(JSON)  # [{id, text, at}]
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)
