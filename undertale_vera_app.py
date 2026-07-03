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

import asyncio
import json
import re

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import affinity as affinity_mod
import character_disposition
import chat_style
import chronicle as chronicle_mod
import constellation as constellation_mod
import deltarune_parser
import guided
import guide_kb
import power_config
import session_story
import spark
import workshop as workshop_mod
import divergence as divergence_mod
from deltarune_truth import build_deltarune_truth, deltarune_delta
import council
import crossave
import journal
import milestones
import proactive
import relationships
import reports as reports_mod
import agentmail_client
import save_flavor
import hallucination_guard
import judgment as judgment_mod
import ledger
import living_memory as lm
import provenance as provenance_mod
import rag_engine
import scene_resolver
from avatar_resolver import resolve_avatar, resolve_emblem, PORTRAIT_DIR, _slug as _portrait_slug
from backend.models import (
    Base, CharacterMemory, Conversation, JournalEntry, Project, ReportEntry, SaveSnapshot,
)
from character_config import get_character, list_characters, normalize_key
import llm_client
from llm_client import LLMUnavailable, generate_reply
from prompt_builder import build_system_prompt, emphasis_note
from save_parser import parse_undertale_save
from save_truth import build_save_truth, validate_save_truth

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
DB_URL = os.environ.get("UNDERTALE_VERA_DB", "sqlite:///./undertale_vera.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

# Existing DBs predate the visitor column (create_all won't add columns).
try:
    with engine.connect() as _c:
        cols = [r[1] for r in _c.exec_driver_sql("PRAGMA table_info(projects)")]
        if "visitor" not in cols:
            _c.exec_driver_sql("ALTER TABLE projects ADD COLUMN visitor VARCHAR(64)")
            _c.commit()
except Exception:
    pass

# ── public-visitor scoping (EMBER_VISITOR_SCOPE=1, for shared deployments) ───
# Each browser gets an opaque cookie; saves are visible only to the browser
# that uploaded them. Off by default: single-user installs are untouched.
import contextvars
import uuid as _uuid

VISITOR_SCOPE = os.environ.get("EMBER_VISITOR_SCOPE", "").strip() in ("1", "true", "yes")
_visitor_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("visitor", default=None)
MAX_SAVE_BYTES = 2 * 1024 * 1024          # no real save comes close
MAX_PROJECTS_PER_VISITOR = 25


def _visitor() -> Optional[str]:
    return _visitor_ctx.get() if VISITOR_SCOPE else None


def _scoped_project(db: Session, project_id: int) -> Optional[Project]:
    """db.get(Project, id) that respects visitor scoping (404-as-None on miss)."""
    project = db.get(Project, project_id)
    if project is None:
        return None
    v = _visitor()
    if v is not None and project.visitor is not None and project.visitor != v:
        return None
    return project


async def _read_capped(f) -> bytes:
    data = await f.read()
    if len(data) > MAX_SAVE_BYTES:
        raise HTTPException(status_code=413, detail="that file is far larger than any real save")
    return data


def _scoped_projects_query(db: Session):
    q = db.query(Project)
    v = _visitor()
    if v is not None:
        q = q.filter(Project.visitor == v)
    return q

app = FastAPI(title="undertale-vera", version="0.1.0-spine0")

@app.middleware("http")
async def _visitor_cookie(request, call_next):
    if not VISITOR_SCOPE:
        return await call_next(request)
    vid = request.cookies.get("ember_visitor")
    fresh = False
    if not vid or not (8 <= len(vid) <= 64) or not vid.isalnum():
        vid = _uuid.uuid4().hex
        fresh = True
    token = _visitor_ctx.set(vid)
    try:
        response = await call_next(request)
    finally:
        _visitor_ctx.reset(token)
    if fresh:
        response.set_cookie("ember_visitor", vid, max_age=60 * 60 * 24 * 365,
                            httponly=True, samesite="lax")
    return response



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


def _prior_save_summaries(db: Session, current_project_id: int) -> list[dict[str, Any]]:
    """Snapshot-fields of every OTHER save (project) the player has shown.

    Cross-save recognition material (Bucket A, SACRED): each entry is the current
    SaveTruth of a different project, reduced to the same honest fields the ledger
    uses. Ordered oldest-first by project id. In this single-player install all
    projects are the same hand on the keys.
    """
    rows = (
        _scoped_projects_query(db)
        .filter(Project.id != current_project_id)
        .order_by(Project.id.asc())
        .all()
    )
    return [ledger.snapshot_fields_from_truth(r.save_data or {}) for r in rows]


# ── health ───────────────────────────────────────────────────────────────────

# ── Guided Mode: the save watcher (READ-ONLY; no game memory, ever) ──────────

guided_hub = guided.GuidedHub()
GUIDED_STORE = os.environ.get("UNDERTALE_VERA_GUIDED_STORE", "./guided_watch.json")
guided_state = guided.WatchState(store_path=GUIDED_STORE)
guided_state.load()   # restarts resume watching and REUSE each file's project


def _guided_truth_for(path: str) -> dict[str, Any]:
    """Parse a watched save file into truth (same read-only parsers as upload)."""
    name = os.path.basename(path)
    with open(path, "rb") as f:
        data = f.read()
    if deltarune_parser.looks_like_deltarune(name):
        parsed = deltarune_parser.parse_deltarune_save(data, name)
        dr_ini = None
        ini_p = guided.sibling_ini(path)
        if ini_p:
            with open(ini_p, "rb") as f:
                dr_ini = deltarune_parser.parse_dr_ini(f.read())
        return build_deltarune_truth(parsed, dr_ini=dr_ini,
                                     source_meta={"filename": name, "watched": True})
    ini_p = guided.sibling_ini(path)
    ini_text = None
    if ini_p:
        with open(ini_p, "r", encoding="utf-8", errors="replace") as f:
            ini_text = f.read()
    parsed = parse_undertale_save(file0_text=data.decode("utf-8", "replace"), ini_text=ini_text)
    return build_save_truth(parsed)


def guided_scan_once(db: Session) -> list[dict[str, Any]]:
    """One watcher pass: adopt new saves, refresh settled changes, publish beats."""
    beats: list[dict[str, Any]] = []
    for d in list(guided_state.dirs):
        for path in guided.discover_saves(d):
            dg = guided.digest_file(path)
            if dg is None:
                continue
            st = guided_state.files.get(path)
            if st is not None and st.get("project_id") and db.get(Project, st["project_id"]) is None:
                st = None   # the stored project vanished — re-adopt honestly
                guided_state.files.pop(path, None)
            if st is None:
                # first sight → adopt as a fresh Guided project (no beat storm)
                try:
                    truth = _guided_truth_for(path)
                except Exception:
                    continue
                project = Project(
                    name=truth["play_state"].get("name")
                    or ("The Vessel" if truth.get("game") == "deltarune" else "Fallen Human"),
                    save_data=truth,
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                _record_snapshot(db, project.id, truth)
                if truth.get("game") != "deltarune":
                    _autofill_journal(db, project.id, truth, _snapshots_for(db, project.id))
                guided_state.files[path] = {"digest": dg, "pending": None, "project_id": project.id}
                beats.append({
                    "type": "adopted", "project_id": project.id, "file": os.path.basename(path),
                    "name": truth["play_state"].get("name"), "game": truth.get("game", "undertale"),
                    "route": (truth.get("route") or {}).get("route"),
                    "area": save_flavor.area_from_save(truth),
                })
                continue
            if dg == st["digest"]:
                st["pending"] = None
                continue
            if st["pending"] != dg:
                st["pending"] = dg      # changed — wait one tick for the write to settle
                continue
            # settled change → a save happened: refresh + append snapshot + delta beat
            project = db.get(Project, st["project_id"])
            if project is None:
                guided_state.files.pop(path, None)
                continue
            prev_truth = project.save_data or {}
            prev_fields = ledger.snapshot_fields_from_truth(prev_truth)
            try:
                truth = _guided_truth_for(path)
            except Exception:
                continue
            project.save_data = truth
            db.commit()
            snap = _record_snapshot(db, project.id, truth)
            if truth.get("game") != "deltarune":
                _autofill_journal(db, project.id, truth, _snapshots_for(db, project.id))
            changes = ledger.summarize_change(prev_fields, ledger.snapshot_fields_from_truth(truth))
            if truth.get("game") == "deltarune":
                # the Dark World speaks its own change language (dollars/party/jester/room)
                changes = deltarune_delta(prev_truth, truth) + [
                    c for c in changes if "route" in c or "name" in c
                ]
            st["digest"], st["pending"] = dg, None
            beats.append({
                "type": "save", "project_id": project.id, "file": os.path.basename(path),
                "name": truth["play_state"].get("name"), "game": truth.get("game", "undertale"),
                "route": (truth.get("route") or {}).get("route"), "visit": snap.counter,
                "changes": changes,
                "area": save_flavor.area_from_save(truth),
            })
    if beats:
        guided_state.save()
    for b in beats:
        guided_hub.publish(b)
    return beats


def _guided_scan_with_session() -> None:
    db = SessionLocal()
    try:
        guided_scan_once(db)
    finally:
        db.close()


@app.on_event("startup")
async def _guided_loop_start() -> None:
    async def loop() -> None:
        while True:
            await asyncio.sleep(2.0)
            if guided_state.dirs:
                try:
                    await asyncio.to_thread(_guided_scan_with_session)
                except Exception:
                    pass   # the watcher never takes the app down
    asyncio.create_task(loop())


class WatchRequest(BaseModel):
    path: str


@app.post("/api/guided/watch")
def guided_watch(req: WatchRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Watch a save directory (e.g. ~/.config/UNDERTALE or the DELTARUNE folder)."""
    if power_config.edition() == "lite" or VISITOR_SCOPE:
        raise HTTPException(status_code=403, detail="Guided Mode watches a save folder on the machine Ember runs on — run Ember locally to use it")
    if not guided_state.add_dir(req.path):
        raise HTTPException(status_code=400, detail="not a directory")
    beats = guided_scan_once(db)   # adopt what's already there, right away
    return {"watching": guided_state.dirs, "adopted": beats,
            "found": [os.path.basename(p) for d in guided_state.dirs
                      for p in guided.discover_saves(d)]}


@app.delete("/api/guided/watch")
def guided_unwatch(req: WatchRequest) -> dict[str, Any]:
    if power_config.edition() == "lite" or VISITOR_SCOPE:
        raise HTTPException(status_code=403, detail="not available on shared sites")
    guided_state.remove_dir(req.path)
    return {"watching": guided_state.dirs}


@app.get("/api/guided/status")
def guided_status() -> dict[str, Any]:
    return {
        "watching": guided_state.dirs,
        "files": [{"file": os.path.basename(p), "project_id": v.get("project_id")}
                  for p, v in guided_state.files.items()],
    }


@app.get("/api/guided/events")
async def guided_events() -> StreamingResponse:
    """SSE stream of Guided beats (adopted saves + save deltas)."""
    q = guided_hub.register()

    async def gen():
        yield "retry: 3000\n\n"
        try:
            while True:
                ev = await q.get()
                yield "data: " + json.dumps(ev) + "\n\n"
        finally:
            guided_hub.unregister(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


class GuidedReactRequest(BaseModel):
    character: str
    changes: list[str] = []


@app.post("/api/projects/{project_id}/guided-react")
def guided_react(project_id: int, req: GuidedReactRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """A party member reacts to WHAT JUST CHANGED between two saves (Guided beats).

    The delta lines are SACRED (they come from ledger.summarize_change); the voice
    is FREE. Persisted to the character's transcript like a reach-out.
    """
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")
    save_truth = project.save_data or {}
    character = get_character(req.character)["name"]

    system_prompt = build_system_prompt(
        character, save_truth,
        disposition_grounding=character_disposition.grounding_from_truth(save_truth),
        relational_grounding=relationships.build_relational_grounding(character, save_truth),
        texture_grounding=save_flavor.build_texture_grounding(save_truth),
    )
    changes = [c for c in (req.changes or []) if isinstance(c, str)][:6]
    if changes:
        system_prompt += (
            "\n\n═══ BETWEEN THEIR LAST TWO SAVES (HARD FACTS — NEVER OVERRIDE OR INVENT) ═══\n"
            + "\n".join("  - " + c for c in changes)
            + "\n═══ END ═══"
        )
        instruction = (
            "The human is playing RIGHT NOW, with you riding along. The block above "
            "records exactly what changed between their last two saves. In one or two "
            "sentences, in your own voice, react to what just changed — and nothing "
            "beyond it."
        )
    else:
        instruction = (
            "The human just saved their game with you riding along; the file shows no "
            "measured change since last time. In one short sentence, in your own voice, "
            "acknowledge the quiet save. Invent nothing."
        )
    source = "llm"
    try:
        result = generate_reply(system_prompt, instruction, history=[])
        text = (result.get("text") or "").strip()
    except LLMUnavailable:
        text = ""
    if not text:
        source = "deterministic_fallback"
        text = (f"— {character}: the save wrote it down: " + "; ".join(changes[:2]) + ". noted."
                if changes else f"— {character}: a quiet save. still here.")

    row = _get_or_create_conversation(db, project_id, character)
    msgs = list(row.messages or [])
    msgs.append({"role": "assistant", "content": text, "at": _now_iso(), "unprompted": True})
    row.messages = msgs[-200:]
    db.commit()

    guard = hallucination_guard.check_response(text, save_truth)
    return {"character": character, "message": text, "grounding_source": source, "guard": guard}


class GuidedHintRequest(BaseModel):
    level: str = "nudge"            # nudge | hint | tell  (the spoiler dial)
    character: Optional[str] = None  # deliver it in this voice (optional)


@app.post("/api/projects/{project_id}/guided-hint")
def guided_hint(project_id: int, req: GuidedHintRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """A progress-gated hint (never beyond the save), optionally delivered in voice."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    save_truth = project.save_data or {}
    hint = guide_kb.hint_for(save_truth, req.level)
    speaker = None
    text = hint["text"]
    if req.character and get_character(req.character):
        speaker = get_character(req.character)["name"]
        system_prompt = build_system_prompt(req.character, save_truth) + (
            "\n\n═══ THE HINT TO DELIVER (HARD FACT OF THE GUIDE — DO NOT ADD OR CHANGE ITS SUBSTANCE) ═══\n"
            f"  {hint['text']}\n═══ END ═══"
        )
        instruction = (
            "Deliver the hint above to the human in your own voice — one or two "
            "sentences, keeping its meaning exactly. Do not add new directions or facts."
        )
        try:
            result = generate_reply(system_prompt, instruction, history=[])
            spoken = (result.get("text") or "").strip()
            if spoken:
                text = spoken
        except LLMUnavailable:
            pass   # the plain hint is the honest fallback
    return {"speaker": speaker, "level": hint["level"], "where": hint["where"],
            "stage": hint["stage"], "text": text, "plain": hint["text"]}


class SessionStoryRequest(BaseModel):
    character: str
    since_visit: int = 1


@app.post("/api/projects/{project_id}/session-story")
def session_story_ep(project_id: int, req: SessionStoryRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """A character narrates the play session's arc (SACRED beats, FREE telling)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")
    character = get_character(req.character)["name"]
    save_truth = project.save_data or {}
    snaps = _snapshots_for(db, project_id)
    beats = session_story.session_beats(snaps, req.since_visit)
    block = session_story.story_block(snaps, req.since_visit)

    source = "llm"
    text = ""
    if block:
        system_prompt = build_system_prompt(
            character, save_truth,
            disposition_grounding=character_disposition.grounding_from_truth(save_truth),
        ) + "\n\n" + block
        try:
            result = generate_reply(system_prompt, session_story.instruction(len(beats)), history=[])
            text = (result.get("text") or "").strip()
        except LLMUnavailable:
            text = ""
    if not text:
        source = "deterministic_fallback"
        text = session_story.fallback(character, snaps, req.since_visit)

    guard = hallucination_guard.check_response(text, save_truth)
    return {"character": character, "text": text, "beats": beats,
            "visits": len(snaps), "grounding_source": source, "guard": guard}


# ── The Commons: the give-back page's data (music downloads) ──────────────────

AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
_MUSIC_TITLES = {
    "a-new-save-file": "A New Save File (main theme)",
    "main-theme": "Alternate Main Theme",
    "route-pacifist": "Mercy (Pacifist bed)",
    "route-neutral": "The In-Between (Neutral bed)",
    "route-genocide": "Dust (Genocide bed)",
    "dark-world": "The Dark World (Deltarune bed)",
}


def _music_files() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        names = sorted(os.listdir(AUDIO_DIR))
    except OSError:
        return out
    for n in names:
        if not n.endswith(".mp3"):
            continue
        p = os.path.join(AUDIO_DIR, n)
        if not os.path.isfile(p):
            continue
        stem = n[:-4]
        title = _MUSIC_TITLES.get(stem)
        if title is None and stem.startswith("char-"):
            who = stem[5:].replace("-", " ").title()
            title = f"{who} (character theme)"
        elif title is None:
            title = stem
        out.append({"file": n, "title": title, "bytes": os.path.getsize(p)})
    return out


@app.get("/api/community/music")
def community_music() -> dict[str, Any]:
    """The custom soundtrack, listed for download (only what's actually on disk)."""
    files = _music_files()
    return {"files": files, "count": len(files),
            "license": "CC BY 4.0 — free to use anywhere; credit appreciated."}


@app.get("/api/community/music.zip")
def community_music_zip():
    """Everything in one grab — a zip streamed from disk, never stored."""
    import io
    import zipfile

    files = _music_files()
    if not files:
        raise HTTPException(status_code=404, detail="no music on this install yet")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.writestr("LICENSE.txt",
                   "The Ember soundtrack\nLicense: CC BY 4.0 "
                   "(https://creativecommons.org/licenses/by/4.0/)\n"
                   "Free to use anywhere; credit appreciated.\n")
        for f in files:
            z.write(os.path.join(AUDIO_DIR, f["file"]), arcname="ember-soundtrack/" + f["file"])
    buf.seek(0)
    from fastapi.responses import Response
    return Response(content=buf.read(), media_type="application/zip",
                    headers={"Content-Disposition": "attachment; filename=ember-soundtrack.zip"})


# ── the power source: which brain (if any) Ember runs on ─────────────────────

class PowerRequest(BaseModel):
    source: str
    openrouter_key: Optional[str] = None
    openrouter_model: Optional[str] = None
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None
    custom_base_url: Optional[str] = None
    custom_model: Optional[str] = None
    custom_key: Optional[str] = None


def _valid_http_url(u: str) -> bool:
    """Only plain http(s) URLs may be dialed server-side (no file:, ftp:, etc.)."""
    from urllib.parse import urlparse
    try:
        p = urlparse(u)
    except ValueError:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


@app.get("/api/power")
def get_power() -> dict[str, Any]:
    """The active power source + curated suggestions (the key only ever masked)."""
    return power_config.public_state()


@app.post("/api/power")
def set_power(req: PowerRequest) -> dict[str, Any]:
    """Choose the power source. Persists to a local, owner-only config file."""
    src = (req.source or "").strip().lower()
    if power_config.locked():
        raise HTTPException(status_code=403,
                            detail="this shared site's power source is fixed — run Ember yourself to choose your own")
    if src not in power_config.SOURCES:
        raise HTTPException(status_code=400, detail=f"source must be one of {power_config.SOURCES}")
    cfg = power_config.load()
    cfg["source"] = src
    if req.openrouter_key is not None and req.openrouter_key.strip():
        cfg["openrouter_key"] = req.openrouter_key.strip()
    if req.openrouter_model is not None and req.openrouter_model.strip():
        cfg["openrouter_model"] = req.openrouter_model.strip()
    # GUI-configured hosts/models — only non-empty values overwrite saved ones,
    # and blank fields leave env fallbacks live.
    for field, wants_url in (("ollama_host", True), ("ollama_model", False),
                             ("custom_base_url", True), ("custom_model", False),
                             ("custom_key", False)):
        val = (getattr(req, field) or "").strip()
        if not val:
            continue
        if wants_url:
            val = val.rstrip("/")
            if not _valid_http_url(val):
                raise HTTPException(status_code=400, detail=f"{field} must be an http(s) URL")
        cfg[field] = val
    if src == "openrouter" and not (cfg.get("openrouter_key") or os.environ.get("OPENROUTER_API_KEY")):
        raise HTTPException(status_code=400, detail="openrouter needs a key")
    if src == "custom" and not (cfg.get("custom_base_url") or os.environ.get("EMBER_CUSTOM_BASE_URL")):
        raise HTTPException(status_code=400,
                            detail="custom backend needs a base URL (e.g. http://127.0.0.1:8000/v1)")
    power_config.save(cfg)
    return power_config.public_state()


class DetectRequest(BaseModel):
    host: Optional[str] = None


@app.post("/api/power/detect")
def detect_ollama_models(req: DetectRequest) -> dict[str, Any]:
    """List the models installed on an Ollama server, for the power picker.

    Refused on shared deployments: this makes a server-side request to a
    user-supplied host, which must never be steerable by visitors (SSRF).
    """
    if power_config.locked() or VISITOR_SCOPE:
        raise HTTPException(status_code=403, detail="model detection is disabled on shared sites")
    host = (req.host or "").strip().rstrip("/") or power_config.ollama_host()
    if not _valid_http_url(host):
        raise HTTPException(status_code=400, detail="host must be an http(s) URL")
    try:
        return {"ok": True, "models": llm_client.list_ollama_models(host)}
    except LLMUnavailable as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/power/test")
def test_power() -> dict[str, Any]:
    """One tiny real generation on the active source — proves the wiring."""
    try:
        r = generate_reply(
            "You are a terse test probe. Reply with exactly: ok",
            "say ok", history=[], max_tokens=8,
        )
        return {"ok": True, "model": r.get("model"), "sample": (r.get("text") or "")[:40]}
    except LLMUnavailable as e:
        # Spark mode reports itself honestly as working-by-design
        if power_config.source() == "none":
            return {"ok": True, "model": None,
                    "sample": "(Spark mode — no model, grounded scripted voice)"}
        return {"ok": False, "error": str(e)}


@app.get("/api/workshop")
def get_workshop() -> dict[str, Any]:
    """The Prompt Workshop's live-true content: the real assembled example
    prompt, the anatomy, and every feature instruction as the code holds it."""
    return workshop_mod.workshop_state()


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
    """Parse an uploaded save (read-only) → SaveTruth → new Project.

    Accepts Undertale's file0 and/or undertale.ini — or a Deltarune chapter slot
    (filech1_0 …) dropped in the file0 field, detected by filename. Read-only:
    we never write a save back.
    """
    if file0 is None and undertale_ini is None:
        raise HTTPException(status_code=400, detail="Provide file0 and/or undertale.ini")

    if _visitor() is not None and _scoped_projects_query(db).count() >= MAX_PROJECTS_PER_VISITOR:
        raise HTTPException(status_code=429, detail="this browser's save shelf is full")

    # Deltarune: a filech{N}_{slot} in the main slot takes the Dark World path.
    # dr.ini may ride the second slot as the corroborating summary (like undertale.ini).
    if file0 is not None and deltarune_parser.looks_like_deltarune(file0.filename):
        dr_parsed = deltarune_parser.parse_deltarune_save(await _read_capped(file0), file0.filename)
        dr_ini = None
        if undertale_ini is not None:
            ini_text = (await _read_capped(undertale_ini)).decode("utf-8", "replace")
            if deltarune_parser.looks_like_dr_ini(undertale_ini.filename, ini_text):
                dr_ini = deltarune_parser.parse_dr_ini(ini_text)
        truth = build_deltarune_truth(dr_parsed, dr_ini=dr_ini, source_meta={"filename": file0.filename})
        project = Project(name=truth["play_state"].get("name") or "The Vessel", save_data=truth, visitor=_visitor())
        db.add(project)
        db.commit()
        db.refresh(project)
        _record_snapshot(db, project.id, truth)
        return {"project_id": project.id, "save_truth": truth,
                "validation": {"ok": True, "issues": [], "warnings": truth.get("warnings", [])}}

    file0_text = (await _read_capped(file0)).decode("utf-8", "replace") if file0 else None
    ini_text = (await _read_capped(undertale_ini)).decode("utf-8", "replace") if undertale_ini else None

    parsed = parse_undertale_save(file0_text=file0_text, ini_text=ini_text)
    truth = build_save_truth(parsed)
    validation = validate_save_truth(truth)

    project = Project(name=truth["play_state"].get("name") or "Fallen Human", save_data=truth, visitor=_visitor())
    db.add(project)
    db.commit()
    db.refresh(project)

    # First remembrance-ledger entry (the save begins to remember).
    _record_snapshot(db, project.id, truth)
    _autofill_journal(db, project.id, truth, _snapshots_for(db, project.id))

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
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if file0 is None and undertale_ini is None:
        raise HTTPException(status_code=400, detail="Provide file0 and/or undertale.ini")

    file0_text = (await _read_capped(file0)).decode("utf-8", "replace") if file0 else None
    ini_text = (await _read_capped(undertale_ini)).decode("utf-8", "replace") if undertale_ini else None
    parsed = parse_undertale_save(file0_text=file0_text, ini_text=ini_text)
    truth = build_save_truth(parsed)

    project.save_data = truth
    db.commit()
    snap = _record_snapshot(db, project_id, truth)
    _autofill_journal(db, project_id, truth, _snapshots_for(db, project_id))

    return {
        "project_id": project_id,
        "save_truth": truth,
        "visit": snap.counter,
        "remembrance": ledger.build_remembrance_grounding(_snapshots_for(db, project_id)),
        "path_turn": ledger.detect_route_turn(_snapshots_for(db, project_id)),
    }


@app.get("/api/projects/{project_id}/save-memory")
def save_memory(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The remembrance ledger: the chronological snapshots ('the save remembers')."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    snaps = _snapshots_for(db, project_id)
    return {
        "project_id": project_id,
        "snapshots": snaps,
        "remembrance": ledger.build_remembrance_grounding(snaps),
    }


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)) -> dict[str, Any]:
    """The save shelf: every read save, newest first, with a route summary."""
    rows = _scoped_projects_query(db).order_by(Project.created_at.desc(), Project.id.desc()).all()
    out = []
    for p in rows:
        st = p.save_data or {}
        out.append({
            "project_id": p.id,
            "name": p.name,
            "route": (st.get("route") or {}).get("route"),
            "love": (st.get("play_state") or {}).get("love"),
            "game": st.get("game", "undertale"),      # deltarune saves ride the same shelf
            "chapter": st.get("chapter"),
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
    return {"projects": out}


@app.get("/api/projects/{project_id}/save-truth")
def get_save_truth(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project_id": project_id, "save_truth": project.save_data}


# ── the Judgment beat ────────────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/judgment")
def get_judgment(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Deterministic sacred judgment: route / LOVE / kills read off SaveTruth."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    snaps = _snapshots_for(db, project_id)
    return {"project_id": project_id, "judgment": judgment_mod.build_judgment(project.save_data or {}, snaps)}


# ── the Keepsake Journal (ADD-only; the book you carry between worlds) ────────

def _journal_entries(db: Session, project_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(JournalEntry)
        .filter(JournalEntry.project_id == project_id)
        .order_by(JournalEntry.counter.asc(), JournalEntry.id.asc())
        .all()
    )
    return [
        {"counter": r.counter, "author": r.author, "kind": r.kind,
         "text": r.text, "route_context": r.route_context,
         "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@app.get("/api/projects/{project_id}/journal")
def get_journal(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The Keepsake Journal: every inscription, plus a portable markdown export."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    entries = _journal_entries(db, project_id)
    return {"project_id": project_id, "entries": entries,
            "markdown": journal.build_journal_markdown(entries, project.name or "this save")}


class InscribeRequest(BaseModel):
    character: str


@app.post("/api/projects/{project_id}/journal/inscribe")
def inscribe_journal(project_id: int, req: InscribeRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """A character writes a grounded entry in the journal (FREE voice over SACRED facts)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")

    save_truth = project.save_data or {}
    # Ground the entry exactly like chat: sacred facts + who-you-met + the speaker's
    # relational stake. The journal entry is their voice over those facts.
    system_prompt = build_system_prompt(
        req.character, save_truth,
        disposition_grounding=character_disposition.grounding_from_truth(save_truth),
        relational_grounding=relationships.build_relational_grounding(req.character, save_truth),
    )
    instruction = journal.inscription_instruction(save_truth)
    try:
        result = generate_reply(system_prompt, instruction, history=[])
        text = (result.get("text") or "").strip()
    except LLMUnavailable:
        text = ""
    if not text:
        text = journal.fallback_inscription(req.character, save_truth)

    guard = hallucination_guard.check_response(text, save_truth)
    author = get_character(req.character)["name"]
    prior = db.query(JournalEntry).filter(JournalEntry.project_id == project_id).count()
    entry = JournalEntry(
        project_id=project_id, counter=prior + 1, author=author, kind="inscription",
        text=text, route_context=(save_truth.get("route") or {}).get("route"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {
        "entry": {"counter": entry.counter, "author": entry.author, "kind": entry.kind,
                  "text": entry.text, "route_context": entry.route_context},
        "guard": guard,
    }


# ── Report Cards (each character's after-action report on your run) ───────────

class ReportRequest(BaseModel):
    character: str
    to_journal: bool = False   # also inscribe the report into the Keepsake Journal


class EmailReportRequest(BaseModel):
    character: str
    to: Optional[str] = None      # override recipient; default = UNDERTALE_VERA_USER_EMAIL
    text: Optional[str] = None    # email THIS already-shown report; omit to generate fresh
    verdict: Optional[str] = None


class JournalAddRequest(BaseModel):
    author: str
    text: str
    kind: str = "report"          # inscribe an already-shown report into the journal verbatim


class ReportStatusRequest(BaseModel):
    status: str                   # 'active' | 'archived'


class EmailDigestRequest(BaseModel):
    to: Optional[str] = None      # override recipient; default = UNDERTALE_VERA_USER_EMAIL


def _make_report(save_truth: dict[str, Any], character: str) -> dict[str, Any]:
    """Generate one character's grounded report (FREE voice over SACRED facts)."""
    author = get_character(character)["name"]
    system_prompt = build_system_prompt(
        character, save_truth,
        disposition_grounding=character_disposition.grounding_from_truth(save_truth),
        relational_grounding=relationships.build_relational_grounding(character, save_truth),
    )
    instruction = reports_mod.report_instruction(save_truth)
    source = "llm"
    try:
        result = generate_reply(system_prompt, instruction, history=[])
        text = (result.get("text") or "").strip()
    except LLMUnavailable:
        text = ""
    if not text:
        text = reports_mod.fallback_report(author, save_truth)
        source = "deterministic_fallback"
    verdict, body = reports_mod.split_verdict(text)
    guard = hallucination_guard.check_response(text, save_truth)
    return {
        "author": author, "verdict": verdict, "body": body, "text": text,
        "route_context": (save_truth.get("route") or {}).get("route"),
        "grounding_source": source, "guard": guard,
    }


def _inscribe_report(db: Session, project_id: int, rep: dict[str, Any]) -> None:
    """Persist a report into the Keepsake Journal (ADD-only, kind='report')."""
    prior = db.query(JournalEntry).filter(JournalEntry.project_id == project_id).count()
    db.add(JournalEntry(
        project_id=project_id, counter=prior + 1, author=rep["author"], kind="report",
        text=rep["text"], route_context=rep["route_context"],
    ))
    db.commit()


def _report_json(r: ReportEntry) -> dict[str, Any]:
    verdict, body = reports_mod.split_verdict(r.text)
    return {
        "id": r.id, "author": r.author, "verdict": r.verdict or verdict, "body": body,
        "text": r.text, "route_context": r.route_context, "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@app.post("/api/projects/{project_id}/report")
def request_report(project_id: int, req: ReportRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """One character's grounded after-action report — saved to history; opt. to journal."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")
    rep = _make_report(project.save_data or {}, req.character)
    # persist to the managed reports history (the player can archive/delete later)
    row = ReportEntry(
        project_id=project_id, author=rep["author"], verdict=rep["verdict"],
        text=rep["text"], route_context=rep["route_context"], status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    rep["id"] = row.id
    rep["status"] = row.status
    rep["created_at"] = row.created_at.isoformat() if row.created_at else None
    if req.to_journal:
        _inscribe_report(db, project_id, rep)
        rep["inscribed"] = True
    return {"report": rep}


@app.get("/api/projects/{project_id}/reports")
def list_reports(project_id: int, character: Optional[str] = None, status: str = "active",
                 db: Session = Depends(get_db)) -> dict[str, Any]:
    """The reports history for a save — newest first; filter by character and status."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    q = db.query(ReportEntry).filter(ReportEntry.project_id == project_id)
    if status in ("active", "archived"):
        q = q.filter(ReportEntry.status == status)
    if character and get_character(character):
        q = q.filter(ReportEntry.author == get_character(character)["name"])
    rows = q.order_by(ReportEntry.created_at.desc(), ReportEntry.id.desc()).all()
    # counts drive the UI's per-character filter + archived toggle
    all_rows = db.query(ReportEntry).filter(ReportEntry.project_id == project_id).all()
    counts = {"active": 0, "archived": 0, "by_author": {}}
    for r in all_rows:
        counts[r.status] = counts.get(r.status, 0) + 1
        if r.status == "active":
            counts["by_author"][r.author] = counts["by_author"].get(r.author, 0) + 1
    return {"reports": [_report_json(r) for r in rows], "counts": counts}


@app.patch("/api/projects/{project_id}/reports/{report_id}")
def update_report(project_id: int, report_id: int, req: ReportStatusRequest,
                  db: Session = Depends(get_db)) -> dict[str, Any]:
    """Archive or restore a report (status = 'active' | 'archived')."""
    row = db.get(ReportEntry, report_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="report not found")
    if req.status not in ("active", "archived"):
        raise HTTPException(status_code=400, detail="status must be 'active' or 'archived'")
    row.status = req.status
    db.commit()
    db.refresh(row)
    return {"report": _report_json(row)}


@app.delete("/api/projects/{project_id}/reports/{report_id}")
def delete_report(project_id: int, report_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Delete a report from history (the player owns their reports)."""
    row = db.get(ReportEntry, report_id)
    if not row or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="report not found")
    db.delete(row)
    db.commit()
    return {"ok": True, "deleted": report_id}


@app.post("/api/projects/{project_id}/report/full")
def request_full_report(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Every character files a report — the whole Underground weighs in on your run."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    save_truth = project.save_data or {}
    out = [_make_report(save_truth, c["name"])
           for c in list_characters(save_truth.get("game") or "undertale")]
    markdown = reports_mod.build_report_markdown(out, project.name or "this save")
    return {"reports": out, "markdown": markdown}


@app.get("/api/email/status")
def email_status() -> dict[str, Any]:
    """Whether a character can email the player (drives the UI's email button)."""
    return agentmail_client.status()


@app.post("/api/projects/{project_id}/report/email")
def email_report(project_id: int, req: EmailReportRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Generate a report and email it to the player, in the character's voice (opt-in)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")
    author = get_character(req.character)["name"]
    if req.text:   # email the report the user is already looking at, verbatim
        rep = {"author": author, "verdict": req.verdict or "", "text": req.text}
    else:
        rep = _make_report(project.save_data or {}, req.character)
    subject = f"A report from {rep['author']}" + (f" — {rep['verdict']}" if rep["verdict"] else "")
    try:
        sent = agentmail_client.send(subject, rep["text"], to=req.to)
    except agentmail_client.EmailUnavailable as exc:
        return {"report": rep, "email": {"sent": False, "reason": str(exc)}}
    return {"report": rep, "email": sent}


@app.post("/api/projects/{project_id}/report/digest/email")
def email_digest(project_id: int, req: EmailDigestRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Email the whole cast's collected reports as one digest (opt-in, env-gated)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    rows = (
        db.query(ReportEntry)
        .filter(ReportEntry.project_id == project_id, ReportEntry.status == "active")
        .order_by(ReportEntry.created_at.asc(), ReportEntry.id.asc())
        .all()
    )
    if not rows:
        return {"count": 0, "email": {"sent": False, "reason": "no reports yet — request some first"}}
    reports = [{"author": r.author, "verdict": r.verdict, "text": r.text} for r in rows]
    body = reports_mod.build_report_markdown(reports, project.name or "your run")
    plural = "s" if len(reports) != 1 else ""
    subject = f"The Underground's report on your run — {len(reports)} voice{plural}"
    try:
        sent = agentmail_client.send(subject, body, to=req.to)
    except agentmail_client.EmailUnavailable as exc:
        return {"count": len(reports), "email": {"sent": False, "reason": str(exc)}}
    return {"count": len(reports), "email": sent}


@app.post("/api/projects/{project_id}/journal/add")
def journal_add(project_id: int, req: JournalAddRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Inscribe an already-shown report into the Keepsake Journal, verbatim (ADD-only)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.author):
        raise HTTPException(status_code=404, detail=f"unknown character {req.author!r}")
    save_truth = project.save_data or {}
    _inscribe_report(db, project_id, {
        "author": get_character(req.author)["name"],
        "text": req.text,
        "route_context": (save_truth.get("route") or {}).get("route"),
    })
    return {"ok": True}


# ── proactive contact (the characters reach out to YOU, unprompted) ───────────

class ReachOutRequest(BaseModel):
    character: Optional[str] = None   # omit → the app picks who has the most at stake


@app.post("/api/projects/{project_id}/reach-out")
def reach_out(project_id: int, req: ReachOutRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """A character messages the human first — grounded, in voice. Persisted to the chat."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    save_truth = project.save_data or {}

    if req.character:
        if not get_character(req.character):
            raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")
        character = get_character(req.character)["name"]
        basis = None
    else:
        pick = proactive.pick_reacher(save_truth)
        if not pick:
            raise HTTPException(status_code=404, detail="no character available")
        character, basis = pick["character"], pick["basis"]

    system_prompt = build_system_prompt(
        character, save_truth,
        disposition_grounding=character_disposition.grounding_from_truth(save_truth),
        relational_grounding=relationships.build_relational_grounding(character, save_truth),
    )
    instruction = proactive.reach_out_instruction(save_truth)
    try:
        result = generate_reply(system_prompt, instruction, history=[])
        text = (result.get("text") or "").strip()
    except LLMUnavailable:
        text = ""
    if not text:
        text = proactive.fallback_reach_out(character, save_truth)

    # Persist as an assistant-only turn so it surfaces when the human opens the chat.
    row = _get_or_create_conversation(db, project_id, character)
    msgs = list(row.messages or [])
    msgs.append({"role": "assistant", "content": text, "at": _now_iso(), "unprompted": True})
    row.messages = msgs[-200:]
    db.commit()

    guard = hallucination_guard.check_response(text, save_truth)
    return {"character": character, "message": text, "basis": basis, "guard": guard}


@app.get("/api/projects/{project_id}/affinities")
def get_affinities(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """How the whole cast REGARDS the player, derived from the save (SACRED-derived tone)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project_id": project_id, "affinities": affinity_mod.all_affinities(project.save_data or {})}


@app.get("/api/projects/{project_id}/council")
def get_council(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The Council: the whole Underground's reaction to the run, side by side (deterministic)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return {"project_id": project_id, "council": council.build_council(project.save_data or {})}


@app.get("/api/projects/{project_id}/recognition")
def get_recognition(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """New Game+: does anything here know you from ANOTHER save you've shown?

    Deterministic (no model). Surfaces the SACRED facts of your other saves and the
    save-aware characters' (Flowey / Sans) knowing recognition lines. `present` is
    false on a first/only save — nothing has seen you before yet.
    """
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    current = ledger.snapshot_fields_from_truth(project.save_data or {})
    priors = _prior_save_summaries(db, project_id)
    echo_flowey = crossave.build_echo_grounding(current, priors, voice="flowey")
    echo_sans = crossave.build_echo_grounding(current, priors, voice="sans")
    return {
        "project_id": project_id,
        "present": bool(priors),
        "count": len(priors),
        "priors": priors,
        "flowey": crossave.build_recognition_grounding(current, priors, voice="flowey"),
        "sans": crossave.build_recognition_grounding(current, priors, voice="sans"),
        # The Other's Echo: a darker prior run behind a gentler save in hand.
        "echo_present": bool(echo_flowey),
        "echo": {"flowey": echo_flowey, "sans": echo_sans},
        "darkest": crossave.darkest_prior(priors),
        # Across Two Worlds: has the player shown a save from the OTHER game?
        "two_worlds_present": bool(crossave.other_world_priors(current, priors)),
        "other_world": (crossave.other_world_priors(current, priors) or [None])[0],
        "current_game": current.get("game", "undertale"),
    }


@app.get("/api/constellation")
def get_constellation(db: Session = Depends(get_db)) -> dict[str, Any]:
    """The Constellation of You: the whole shape of the player across ALL saves shown.

    Aggregate (not pairwise): the route tally, kindest/darkest runs, peak LOVE, and
    Sans's FREE verdict over the SACRED tallies. Deterministic (no model). `present`
    is false until at least two saves have been shown — one save is not yet a shape.
    """
    saves = [
        ledger.snapshot_fields_from_truth(p.save_data or {})
        for p in _scoped_projects_query(db).order_by(Project.id.asc()).all()
    ]
    agg = constellation_mod.aggregate(saves)
    return {
        "present": agg["count"] >= 2,
        "count": agg["count"],
        "aggregate": agg,
        "verdict": constellation_mod.build_verdict(agg, voice="sans"),
        # The Divergence: the fork between the gentlest and cruelest runs, when both exist.
        "divergence": (
            constellation_mod.build_divergence(agg.get("kindest"), agg.get("darkest"))
            if agg.get("full_spectrum") else ""
        ),
    }


class DivergenceRequest(BaseModel):
    project_a: int
    project_b: int
    character: str


@app.post("/api/divergence")
def divergence(req: DivergenceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """A chosen character reflects on the fork between any TWO of the player's saves."""
    a, b = db.get(Project, req.project_a), db.get(Project, req.project_b)
    if not a or not b:
        raise HTTPException(status_code=404, detail="save not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")
    author = get_character(req.character)["name"]
    save_a, save_b = a.save_data or {}, b.save_data or {}
    fa, fb = ledger.snapshot_fields_from_truth(save_a), ledger.snapshot_fields_from_truth(save_b)
    # anchor the voice in file A, then hand the model BOTH files' sacred facts + the fork
    system_prompt = build_system_prompt(
        req.character, save_a,
        disposition_grounding=character_disposition.grounding_from_truth(save_a),
        relational_grounding=relationships.build_relational_grounding(req.character, save_a),
    ) + "\n\n" + divergence_mod.two_file_block(fa, fb)
    source = "llm"
    try:
        result = generate_reply(system_prompt, divergence_mod.instruction(), history=[])
        text = (result.get("text") or "").strip()
    except LLMUnavailable:
        text = ""
    if not text:
        text = divergence_mod.fallback(author, fa, fb)
        source = "deterministic_fallback"
    return {
        "author": author, "text": text, "grounding_source": source,
        "a": {"project_id": a.id, "name": fa.get("name"), "route": fa.get("route")},
        "b": {"project_id": b.id, "name": fb.get("name"), "route": fb.get("route")},
    }


def _autofill_journal(db: Session, project_id: int, save_truth: dict[str, Any],
                      snapshots: list[dict[str, Any]]) -> None:
    """Append milestone journal entries the save just earned (ADD-only, de-duped by kind)."""
    existing = {
        r.kind for r in db.query(JournalEntry).filter(JournalEntry.project_id == project_id).all()
    }
    fresh = [m for m in milestones.detect_milestones(save_truth, snapshots) if m["kind"] not in existing]
    if not fresh:
        return
    prior = db.query(JournalEntry).filter(JournalEntry.project_id == project_id).count()
    route = (save_truth.get("route") or {}).get("route")
    for i, m in enumerate(fresh, start=1):
        db.add(JournalEntry(project_id=project_id, counter=prior + i, author=m["author"],
                            kind=m["kind"], text=m["text"], route_context=route))
    db.commit()


@app.get("/api/projects/{project_id}/chronicle")
def get_chronicle(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The Chronicle: the save's whole story as shareable Markdown (SACRED, facts-only)."""
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    snaps = _snapshots_for(db, project_id)
    chron = chronicle_mod.build_chronicle(project.save_data or {}, snaps)
    return {"project_id": project_id, **chron}


class JudgmentSpeakRequest(BaseModel):
    character: str = "sans"


@app.post("/api/projects/{project_id}/judgment/speak")
def speak_judgment(project_id: int, req: JudgmentSpeakRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """The judgment delivered IN-VOICE, grounded in the sacred readout.

    The structured judgment is the sacred core; the spoken line is free voice over
    it. Degrades to the deterministic verdict line when no model is reachable.
    """
    project = _scoped_project(db, project_id)
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

@app.get("/api/lore")
def lore(q: str = "", character: Optional[str] = None, route: Optional[str] = None) -> dict[str, Any]:
    """Inspect what the RAG lore layer would retrieve for a query (FREE bucket).

    Optional `route` gates which world-knowledge is visible (route-specific and
    spoiler lore hide until the route is known). Exposed so retrieval is
    auditable — it is never save state.
    """
    docs = rag_engine.retrieve(q, character=character, route=route) if q else []
    return {
        "query": q,
        "character": character,
        "route": route,
        "backend": rag_engine.backend_in_use(),
        "results": docs,
    }


@app.get("/api/characters")
def get_characters(game: Optional[str] = None) -> dict[str, Any]:
    """The roster. ?game=deltarune → the Ch1 cast (Darkners + Hometown faces)."""
    chars = list_characters(game if game in ("undertale", "deltarune") else None)
    for c in chars:
        c["avatar_url"] = resolve_avatar(c)
        c["emblem_url"] = resolve_emblem(c)
    return {"characters": chars}


@app.post("/api/characters/{character}/portrait")
async def set_portrait(character: str, image: UploadFile = File(...)) -> dict[str, Any]:
    """Bring-your-own-art: store an image YOU supply as a character's portrait.

    Writes to the gitignored portraits folder the resolver already serves
    (static/assets/portraits/<slug>.png), so it persists and shows on every device
    you reach the app from. Not a save-file mutation — purely a local UI asset.
    The slug comes only from the known character registry, so no arbitrary paths.
    """
    char = get_character(character)
    if not char:
        raise HTTPException(status_code=404, detail=f"unknown character {character!r}")
    slug = _portrait_slug(char.get("name") or character)
    if not slug:
        raise HTTPException(status_code=400, detail="unusable character name")
    data = await image.read()
    if not data or len(data) < 100:
        raise HTTPException(status_code=400, detail="image missing or too small")
    if len(data) > 4_000_000:
        raise HTTPException(status_code=400, detail="image too large (max ~4MB)")
    os.makedirs(PORTRAIT_DIR, exist_ok=True)
    with open(os.path.join(PORTRAIT_DIR, f"{slug}.png"), "wb") as f:
        f.write(data)
    return {"character": char["name"], "avatar_url": resolve_avatar(char)}


@app.delete("/api/characters/{character}/portrait")
def clear_portrait(character: str) -> dict[str, Any]:
    """Remove a supplied portrait, reverting the character to the default crest."""
    char = get_character(character)
    if not char:
        raise HTTPException(status_code=404, detail=f"unknown character {character!r}")
    slug = _portrait_slug(char.get("name") or character)
    path = os.path.join(PORTRAIT_DIR, f"{slug}.png")
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
    return {"character": char["name"], "avatar_url": resolve_avatar(char)}


@app.get("/api/scenes")
def get_scenes() -> dict[str, Any]:
    """Route → backdrop URL for every generated scene on disk (empty until Prime
    delivers art). The frontend keeps its CSS route-tinted gradient as the fallback."""
    return {"scenes": scene_resolver.available_scenes()}


# ── grounded character chat ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    character: str
    message: str
    history: Optional[list[dict[str, str]]] = None
    options: Optional[dict[str, Any]] = None   # FREE style dials (verbosity/intensity/lore/meta)


def _get_or_create_conversation(db: Session, project_id: int, character: str) -> Conversation:
    key = normalize_key(character)
    row = (
        db.query(Conversation)
        .filter(Conversation.project_id == project_id, Conversation.character_key == key)
        .one_or_none()
    )
    if row is None:
        row = Conversation(project_id=project_id, character_key=key, messages=[])
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _append_turns(db: Session, project_id: int, character: str, user_msg: str, reply: str) -> None:
    """Persist the chat turn (a RECORD; distinct from Bucket-B memory + the ledger)."""
    row = _get_or_create_conversation(db, project_id, character)
    msgs = list(row.messages or [])
    msgs.append({"role": "user", "content": user_msg, "at": _now_iso()})
    msgs.append({"role": "assistant", "content": reply, "at": _now_iso()})
    row.messages = msgs[-200:]  # bounded
    db.commit()


@app.get("/api/projects/{project_id}/conversations/{character}")
def get_conversation(project_id: int, character: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Load the persisted transcript so a conversation survives a reload."""
    row = _get_or_create_conversation(db, project_id, character)
    return {"character_key": row.character_key, "messages": row.messages or []}


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
    project = _scoped_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if not get_character(req.character):
        raise HTTPException(status_code=404, detail=f"unknown character {req.character!r}")

    save_truth = project.save_data or {}
    snapshots = _snapshots_for(db, project_id)
    memory_grounding = _memory_grounding_for(db, project_id, req.character, req.message)
    remembrance = ledger.build_remembrance_grounding(snapshots)
    # Sans is canonically save/reset-aware — give HIM (only) the ledger-history
    # block so he can speak to repeated readings and route turns. Sacred-derived.
    if normalize_key(req.character) == "name:sans":
        sans_block = ledger.build_sans_awareness(snapshots)
        if sans_block:
            remembrance = (remembrance + "\n\n" + sans_block).strip()
    # Flowey remembers RESETS more than anyone — give him his own knowing block.
    elif normalize_key(req.character) == "name:flowey":
        flowey_block = ledger.build_flowey_awareness(snapshots)
        if flowey_block:
            remembrance = (remembrance + "\n\n" + flowey_block).strip()
    # The save/reset-aware pair also FEEL it when the numbers go backward (a load).
    if normalize_key(req.character) in ("name:sans", "name:flowey"):
        reset_block = ledger.build_reset_awareness(snapshots)
        if reset_block:
            remembrance = (remembrance + "\n\n" + reset_block).strip()
    # New Game+: the save/reset-aware pair also recognise the player ACROSS saves —
    # a different file shown before, a different face. SACRED (other projects' real
    # fields). Muted when the player sets the Options 'Save/reset talk' dial to off.
    if (req.options or {}).get("meta") != "off" and normalize_key(req.character) in (
        "name:sans", "name:flowey"
    ):
        voice = "flowey" if normalize_key(req.character) == "name:flowey" else "sans"
        cur_fields = ledger.snapshot_fields_from_truth(save_truth)
        priors = _prior_save_summaries(db, project_id)
        # The Other's Echo (a darker prior run behind a gentler save in hand) is the
        # sharper beat — it implies recognition, with dread — so it supersedes the
        # plain recognition block when it fires.
        rec_block = (
            crossave.build_echo_grounding(cur_fields, priors, voice=voice)
            or crossave.build_recognition_grounding(cur_fields, priors, voice=voice)
        )
        if rec_block:
            remembrance = (remembrance + "\n\n" + rec_block).strip()
    # Across Two Worlds: a returning face (Toriel/Asgore/Alphys/Sans) who has been
    # shown saves from BOTH games feels the other universe like a dream (facts of
    # the other world clearly labelled; never asserted as this world's).
    if (req.options or {}).get("meta") != "off" and normalize_key(req.character) in (
        "name:toriel", "name:asgore", "name:alphys", "name:sans"
    ):
        tw_block = crossave.build_two_worlds_grounding(
            ledger.snapshot_fields_from_truth(save_truth),
            _prior_save_summaries(db, project_id),
            voice=normalize_key(req.character).split(":", 1)[1],
        )
        if tw_block:
            remembrance = (remembrance + "\n\n" + tw_block).strip()
    # Route-gate the lore by the player's REAL route (from SaveTruth). This gates
    # which world-knowledge is visible — it never asserts the route as a fact.
    save_route = (save_truth.get("route") or {}).get("route")
    # FREE style dials: lore depth controls retrieval (None → skip the lore layer).
    k = chat_style.lore_k(req.options or {})
    lore_docs = rag_engine.retrieve(req.message, character=req.character, route=save_route, k=k) if k else []
    lore_grounding = rag_engine.format_lore_grounding(lore_docs)
    style_grounding = chat_style.build_style_directives(req.options or {})
    # SACRED: who the save records as killed/spared/befriended (parser-derived).
    disposition_grounding = character_disposition.grounding_from_truth(save_truth)
    # SACRED: the fate of those THIS speaker cares about (relational awareness).
    relational_grounding = relationships.build_relational_grounding(req.character, save_truth)
    # SACRED texture (area / play time / pie) for everyone; the Fun-value anomaly is
    # eerie meta-lore, so only the save/reset-aware characters (Sans, Flowey) get it.
    texture_grounding = save_flavor.build_texture_grounding(save_truth)
    anomaly_grounding = ""
    if normalize_key(req.character) in ("name:sans", "name:flowey"):
        anomaly_grounding = save_flavor.build_anomaly_grounding(save_truth)
    system_prompt = build_system_prompt(
        req.character, save_truth,
        memory_grounding=memory_grounding,
        remembrance=remembrance,
        lore_grounding=lore_grounding,
        disposition_grounding=disposition_grounding,
        relational_grounding=relational_grounding,
        texture_grounding=texture_grounding,
        anomaly_grounding=anomaly_grounding,
        style_grounding=style_grounding,
    )
    # Chat-only FREE display cue: allow one shaken word of emphasis (see prompt_builder).
    system_prompt += "\n\n" + emphasis_note()

    grounding_source = "llm"
    try:
        result = generate_reply(system_prompt, req.message, history=req.history)
        text = result.get("text") or ""
        model = result.get("model")
    except LLMUnavailable:
        # Graceful degradation: the Spark engine answers in-voice from the save
        # alone — intent-aware, grounded, deterministic (see spark.py).
        grounding_source = "deterministic_fallback"
        text = spark.spark_reply(req.character, req.message, save_truth, history=req.history)
        model = None

    # Second line of defense: check the model's ACTUAL reply against the sacred
    # SaveTruth, and build the per-reply provenance (sacred vs free) for the UI.
    guard = hallucination_guard.check_response(text, save_truth)
    prov = provenance_mod.build_provenance(
        save_truth,
        character=get_character(req.character)["name"],
        lore_docs=lore_docs,
        memory_used=bool(memory_grounding.strip()),
        remembrance_used=bool(remembrance.strip()),
        guard=guard,
    )

    # Persist the turn so the transcript survives a reload.
    _append_turns(db, project_id, req.character, req.message, text)

    return {
        "response": text,
        "character": get_character(req.character)["name"],
        "model": model,
        "grounding": {"source": grounding_source, "system_prompt": system_prompt},
        "route": (save_truth.get("route") or {}).get("route"),
        "path_turn": ledger.detect_route_turn(snapshots),
        "guard": guard,
        "provenance": prov,
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

# Version-stamp local js/css references (?v=<mtime>) so browsers and CDN edges
# fetch fresh copies the moment a deployed file changes — there is no build
# step, so the server is the only place that knows a file moved. The HTML
# itself goes out no-cache; the stamped assets may cache freely.
_ASSET_REF = re.compile(r'(src|href)="(/(?:js|css)/[^"?]+)"')


def _stamped_index(idx: str) -> HTMLResponse:
    with open(idx, encoding="utf-8") as f:
        html = f.read()

    def stamp(m: "re.Match[str]") -> str:
        path = os.path.join(STATIC_DIR, m.group(2).lstrip("/"))
        try:
            v = int(os.path.getmtime(path))
        except OSError:
            return m.group(0)
        return f'{m.group(1)}="{m.group(2)}?v={v}"'

    return HTMLResponse(_ASSET_REF.sub(stamp, html),
                        headers={"Cache-Control": "no-cache"})


@app.get("/")
def index() -> Any:
    idx = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(idx):
        return _stamped_index(idx)
    return JSONResponse({"app": "undertale-vera", "status": "no static index yet"})


@app.get("/{full_path:path}")
def static_or_spa(full_path: str) -> Any:
    candidate = os.path.normpath(os.path.join(STATIC_DIR, full_path))
    if candidate.startswith(os.path.realpath(STATIC_DIR)) and os.path.isfile(candidate):
        return FileResponse(candidate)
    idx = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(idx):
        return _stamped_index(idx)
    raise HTTPException(status_code=404, detail="not found")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9092)
