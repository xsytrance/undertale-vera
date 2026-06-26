#!/usr/bin/env python3
"""undertale-vera — FastAPI app (Spine 0: scaffold + grounded character chat).

Ports the PORTABLE MultiVera spine from fft-psx-vera, fenced of all FFT-specific
logic. The pipeline mirrors GAME_VERA_BLUEPRINT.md:

    save files → parser → SaveTruth (with ROUTE) → storage
              → prompt builder (two-bucket wall) → grounded chat
              → automated truth verification (Inspector)

Two buckets, never blurred:
  - Project.save_data  = SACRED parser truth.
  - CharacterMemory.*  = FREE relationship memory.

This is SCAFFOLD + CHAT, deliberately not the whole app (no scope creep).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import judgment as judgment_mod
import ledger
import living_memory as lm
from avatar_resolver import resolve_avatar
from backend.models import Base, CharacterMemory, Project, SaveSnapshot
from character_config import get_character, list_characters, normalize_key
from llm_client import LLMUnavailable, generate_reply
from prompt_builder import build_system_prompt
from save_parser import parse_undertale_save
from save_truth import build_save_truth, validate_save_truth

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DB_URL = os.environ.get("UNDERTALE_VERA_DB", "sqlite:///./undertale_vera.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

app = FastAPI(title="undertale-vera", version="0.1.0-spine0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_snapshot(db: Session, project_id: int, save_truth: dict[str, Any]) -> SaveSnapshot:
    """Append one immutable remembrance-ledger row (Bucket A, ADD-only).

    Never overwrites prior snapshots — the player's history accrues across visits.
    """
    import hashlib
    import json

    fields = ledger.snapshot_fields_from_truth(save_truth)
    prior = (
        db.query(SaveSnapshot)
        .filter(SaveSnapshot.project_id == project_id)
        .count()
    )
    fingerprint = hashlib.sha256(
        json.dumps(fields, sort_keys=True, default=str).encode()
    ).hexdigest()
    snap = SaveSnapshot(
        project_id=project_id,
        counter=prior + 1,
        name=fields["name"],
        love=fields["love"],
        route=fields["route"],
        route_confidence=fields["route_confidence"],
        total_kills=fields["total_kills"],
        save_fingerprint=fingerprint,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def _snapshots_for(db: Session, project_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(SaveSnapshot)
        .filter(SaveSnapshot.project_id == project_id)
        .order_by(SaveSnapshot.counter.asc(), SaveSnapshot.id.asc())
        .all()
    )
    return [
        {
            "counter": r.counter,
            "name": r.name,
            "love": r.love,
            "route": r.route,
            "route_confidence": r.route_confidence,
            "total_kills": r.total_kills,
            "save_fingerprint": r.save_fingerprint,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ── health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "app": "undertale-vera", "spine": 0}


# ── save upload + truth ──────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_save(
    file0: Optional[UploadFile] = File(default=None),
    undertale_ini: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Parse an uploaded Undertale save (read-only) → SaveTruth → new Project.

    Accepts file0 and/or undertale.ini. Read-only: we never write a save back.
    """
    if file0 is None and undertale_ini is None:
        raise HTTPException(status_code=400, detail="Provide file0 and/or undertale.ini")

    file0_text = (await file0.read()).decode("utf-8", "replace") if file0 else None
    ini_text = (await undertale_ini.read()).decode("utf-8", "replace") if undertale_ini else None

    parsed = parse_undertale_save(file0_text=file0_text, ini_text=ini_text)
    truth = build_save_truth(parsed)
    validation = validate_save_truth(truth)

    project = Project(name=truth["play_state"].get("name") or "Fallen Human", save_data=truth)
    db.add(project)
    db.commit()
    db.refresh(project)

    # First remembrance-ledger entry (the save begins to remember).
    _record_snapshot(db, project.id, truth)

    return {"project_id": project.id, "save_truth": truth, "validation": validation}


@app.post("/api/projects/{project_id}/refresh-save")
async def refresh_save(
    project_id: int,
    file0: Optional[UploadFile] = File(default=None),
    undertale_ini: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Re-read a later save for the SAME project (a return visit).

    Read-only re: the save files. Updates the project's current SaveTruth and
    APPENDS a new remembrance snapshot — prior snapshots are never touched.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if file0 is None and undertale_ini is None:
        raise HTTPException(status_code=400, detail="Provide file0 and/or undertale.ini")

    file0_text = (await file0.read()).decode("utf-8", "replace") if file0 else None
    ini_text = (await undertale_ini.read()).decode("utf-8", "replace") if undertale_ini else None
    parsed = parse_undertale_save(file0_text=file0_text, ini_text=ini_text)
    truth = build_save_truth(parsed)

    project.save_data = truth
    db.commit()
    snap = _record_snapshot(db, project_id, truth)

    return {
        "project_id": project_id,
        "save_truth": truth,
        "visit": snap.counter,
        "remembrance": ledger.build_remembrance_grounding(_snapshots_for(db, project_id)),
    }


@app.get("/api/projects/{project_id}/save-memory")
def save_memory(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The remembrance ledger: the chronological snapshots ('the save remembers')."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    snaps = _snapshots_for(db, project_id)
    return {
        "project_id": project_id,
        "snapshots": snaps,
        "remembrance": ledger.build_remembrance_grounding(snaps),
    }


@app.get("/api/projects/{project_id}/save-truth")
def get_save_truth(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project_id": project_id, "save_truth": project.save_data}


# ── the Judgment beat ────────────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/judgment")
def get_judgment(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Deterministic sacred judgment: route / LOVE / kills read off SaveTruth."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    snaps = _snapshots_for(db, project_id)
    return {"project_id": project_id, "judgment": judgment_mod.build_judgment(project.save_data or {}, snaps)}


class JudgmentSpeakRequest(BaseModel):
    character: str = "sans"


@app.post("/api/projects/{project_id}/judgment/speak")
def speak_judgment(project_id: int, req: JudgmentSpeakRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The judgment delivered IN-VOICE, grounded in the sacred readout.

    The structured judgment is the sacred core; the spoken line is free voice over
    it. Degrades to the deterministic verdict line when no model is reachable.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")

    save_truth = project.save_data or {}
    snaps = _snapshots_for(db, project_id)
    judgment = judgment_mod.build_judgment(save_truth, snaps)
    remembrance = ledger.build_remembrance_grounding(snaps)
    system_prompt = build_system_prompt(req.character, save_truth, remembrance=remembrance)
    judge_msg = (
        "Deliver your judgment of this player now. Read back what the save shows — "
        "their route, their LOVE, their kills — in your own voice. State only what "
        "is in the save; name the unknowns honestly; invent nothing."
    )

    grounding_source = "llm"
    try:
        result = generate_reply(system_prompt, judge_msg)
        spoken = result.get("text") or ""
        model = result.get("model")
    except LLMUnavailable:
        grounding_source = "deterministic_fallback"
        spoken = judgment["verdict"]["line"]
        model = None

    return {
        "project_id": project_id,
        "character": get_character(req.character)["name"],
        "judgment": judgment,
        "spoken": spoken,
        "model": model,
        "grounding": {"source": grounding_source, "system_prompt": system_prompt},
    }


# ── characters ───────────────────────────────────────────────────────────────

@app.get("/api/characters")
def get_characters() -> dict[str, Any]:
    chars = list_characters()
    for c in chars:
        c["avatar_url"] = resolve_avatar(c)
    return {"characters": chars}


# ── grounded character chat ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    character: str
    message: str
    history: Optional[list[dict[str, str]]] = None


def _memory_grounding_for(db: Session, project_id: int, character: str, message: str) -> str:
    """Pull Bucket-B recollections and format them as labeled grounding."""
    key = normalize_key(character)
    row = (
        db.query(CharacterMemory)
        .filter(CharacterMemory.project_id == project_id, CharacterMemory.character_key == key)
        .one_or_none()
    )
    if not row:
        return ""
    personality = row.personality or {}
    qa = lm.select_memories(personality.get("memories"), message, k=5)
    return lm.format_memory_grounding(qa, row.relationship)


@app.post("/api/projects/{project_id}/chat")
def chat(project_id: int, req: ChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")

    save_truth = project.save_data or {}
    memory_grounding = _memory_grounding_for(db, project_id, req.character, req.message)
    remembrance = ledger.build_remembrance_grounding(_snapshots_for(db, project_id))
    system_prompt = build_system_prompt(
        req.character, save_truth,
        memory_grounding=memory_grounding,
        remembrance=remembrance,
    )

    grounding_source = "llm"
    try:
        result = generate_reply(system_prompt, req.message, history=req.history)
        text = result.get("text") or ""
        model = result.get("model")
    except LLMUnavailable:
        # Graceful degradation: stay honest and grounded even with no model.
        grounding_source = "deterministic_fallback"
        route = (save_truth.get("route") or {}).get("route", "undetermined")
        text = (
            f"(No model is reachable right now.) I can only speak to what your save "
            f"shows: your route reads as {route}. I won't pretend to more than that."
        )
        model = None

    return {
        "response": text,
        "character": get_character(req.character)["name"],
        "model": model,
        "grounding": {"source": grounding_source, "system_prompt": system_prompt},
        "route": (save_truth.get("route") or {}).get("route"),
    }


# ── Living Memory (Bucket B) — never touches Project.save_data ────────────────

def _get_or_create_memory(db: Session, project_id: int, character: str) -> CharacterMemory:
    key = normalize_key(character)
    row = (
        db.query(CharacterMemory)
        .filter(CharacterMemory.project_id == project_id, CharacterMemory.character_key == key)
        .one_or_none()
    )
    if row is None:
        row = CharacterMemory(
            project_id=project_id,
            character_key=key,
            personality={"base": None, "drift": {}, "memories": [], "budget": {}},
            relationship=[],
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@app.get("/api/projects/{project_id}/memory/{character}")
def get_memory(project_id: int, character: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = _get_or_create_memory(db, project_id, character)
    return {
        "character_key": row.character_key,
        "personality": row.personality,
        "relationship": row.relationship,
    }


class RememberRequest(BaseModel):
    text: str


@app.post("/api/projects/{project_id}/memory/{character}/remember")
def remember(project_id: int, character: str, req: RememberRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = _get_or_create_memory(db, project_id, character)
    rel = row.relationship or []
    new_rel = lm.add_memory(rel, req.text, _now_iso(), lm.next_memory_id(rel))
    row.relationship = new_rel
    db.commit()
    return {"character_key": row.character_key, "relationship": new_rel}


class ForgetRequest(BaseModel):
    mem_id: Any = "all"


@app.post("/api/projects/{project_id}/memory/{character}/forget")
def forget(project_id: int, character: str, req: ForgetRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    row = _get_or_create_memory(db, project_id, character)
    row.relationship = lm.forget(row.relationship, req.mem_id)
    db.commit()
    return {"character_key": row.character_key, "relationship": row.relationship}


# ── static + SPA fallback ────────────────────────────────────────────────────

@app.get("/")
def index() -> Any:
    idx = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(idx):
        return FileResponse(idx)
    return JSONResponse({"app": "undertale-vera", "status": "no static index yet"})


@app.get("/{full_path:path}")
def static_or_spa(full_path: str) -> Any:
    candidate = os.path.normpath(os.path.join(STATIC_DIR, full_path))
    if candidate.startswith(os.path.realpath(STATIC_DIR)) and os.path.isfile(candidate):
        return FileResponse(candidate)
    idx = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(idx):
        return FileResponse(idx)
    raise HTTPException(status_code=404, detail="not found")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9092)
