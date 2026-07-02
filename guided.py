#!/usr/bin/env python3
"""Guided Mode — the save-watching core (no game memory, ever).

Ember's Guided Mode rides ALONGSIDE the game: a watcher polls the game's save
directory; every time the game writes a save, the app re-reads it (read-only, the
same parsers as manual upload), appends a snapshot, and publishes a "beat" — the
honest delta between saves — to the UI over SSE. Characters then react to the beat.

Design rules:
  - READ-ONLY, file-based. We never touch game memory or the game window.
  - Polling (not inotify): robust everywhere, no extra deps; saves are tiny.
  - Debounce by digest: a beat fires only when the bytes actually changed AND the
    file has settled (two consecutive scans agree).

This module is the app-independent part: the SSE hub, save discovery, and digests.
The scan loop itself lives in the app (it needs the DB + truth builders).
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
from typing import Any, Optional

# The save files worth watching, per game. Slot files only — configs churn.
UNDERTALE_FILES = ("file0",)
DELTARUNE_RE = re.compile(r"^filech\d+_[0-2]$", re.IGNORECASE)


def discover_saves(directory: str) -> list[str]:
    """Watchable save files in a directory (absolute paths, stable order)."""
    out: list[str] = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return out
    for n in names:
        p = os.path.join(directory, n)
        if not os.path.isfile(p):
            continue
        if n in UNDERTALE_FILES or DELTARUNE_RE.match(n):
            out.append(p)
    return out


def sibling_ini(save_path: str) -> Optional[str]:
    """The corroborating ini beside a save file (undertale.ini / dr.ini), if any."""
    d = os.path.dirname(save_path)
    name = os.path.basename(save_path).lower()
    ini = os.path.join(d, "undertale.ini") if name == "file0" else os.path.join(d, "dr.ini")
    return ini if os.path.isfile(ini) else None


def digest_file(path: str) -> Optional[str]:
    """Content digest of a save (+ its sibling ini); None when unreadable."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read())
        ini = sibling_ini(path)
        if ini:
            with open(ini, "rb") as f:
                h.update(f.read())
    except OSError:
        return None
    return h.hexdigest()[:20]


class GuidedHub:
    """A tiny SSE broadcast hub: publish() fans a JSON-able event to every client."""

    def __init__(self) -> None:
        self.clients: list[asyncio.Queue] = []

    def register(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.clients.append(q)
        return q

    def unregister(self, q: asyncio.Queue) -> None:
        try:
            self.clients.remove(q)
        except ValueError:
            pass

    def publish(self, event: dict[str, Any]) -> None:
        for q in list(self.clients):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


class WatchState:
    """What the watcher knows: directories, and per-file digest/project/settle.

    Persisted to a small JSON sidecar (NOT the ADD-only DB — this is watcher
    plumbing, not history) so a server restart resumes watching the same
    directories and, crucially, REUSES each save file's existing project instead
    of adopting duplicates onto the shelf.
    """

    def __init__(self, store_path: Optional[str] = None) -> None:
        self.dirs: list[str] = []
        # path → {"digest": str, "pending": str|None, "project_id": int|None}
        self.files: dict[str, dict[str, Any]] = {}
        self.store_path = store_path

    def add_dir(self, directory: str) -> bool:
        d = os.path.abspath(os.path.expanduser(directory))
        if not os.path.isdir(d):
            return False
        if d not in self.dirs:
            self.dirs.append(d)
        self.save()
        return True

    def remove_dir(self, directory: str) -> None:
        d = os.path.abspath(os.path.expanduser(directory))
        self.dirs = [x for x in self.dirs if x != d]
        self.files = {p: v for p, v in self.files.items() if not p.startswith(d + os.sep)}
        self.save()

    def save(self) -> None:
        if not self.store_path:
            return
        try:
            import json
            slim = {p: {"digest": v.get("digest"), "project_id": v.get("project_id")}
                    for p, v in self.files.items()}
            with open(self.store_path, "w") as f:
                json.dump({"dirs": self.dirs, "files": slim}, f)
        except OSError:
            pass

    def load(self) -> None:
        if not self.store_path or not os.path.isfile(self.store_path):
            return
        try:
            import json
            with open(self.store_path) as f:
                data = json.load(f)
            self.dirs = [d for d in data.get("dirs", []) if os.path.isdir(d)]
            self.files = {p: {"digest": v.get("digest"), "pending": None,
                              "project_id": v.get("project_id")}
                          for p, v in (data.get("files") or {}).items()}
        except (OSError, ValueError):
            pass
