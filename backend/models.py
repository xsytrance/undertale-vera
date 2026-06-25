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
