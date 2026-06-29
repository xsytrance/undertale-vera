# Undertale Save Format — what undertale-vera parses (and what it refuses to guess)

Undertale persists two files. undertale-vera reads both **read-only** and never
writes a save.

## `file0` — the main save slot
A newline-delimited list of values. Only these indices are version-stable and
community-documented enough for us to assign meaning; everything else is preserved
raw (`ParsedUndertaleSave.file0_lines`) but left semantically `null`:

| Line index | Field | Confidence | Notes |
|---|---|---|---|
| 0 | `name` | confirmed | the fallen human's entered name |
| 1 | `love` (LV) | confirmed | LOVE — "Level Of ViolencE"; 1 means zero EXP/kills |
| 2 | `max_hp` | medium | default 20 at LV 1; grows with LOVE — range-validated |
| 11 | `kills` | high | kill counter; mirrors `[General].Kills` — range-validated |
| 35 | `fun` | high | the "Fun value" RNG flag (1–100); mirrors `[General].Fun` |
| 547 | `room` | high | current room id; mirrors `[General].Room` |

Out-of-range or unparseable values become `None` with confidence `unknown`, and a
warning is recorded — **never** a guessed value.

### How indices 11 / 35 / 547 were promoted (data-driven, not guessed)
These three were `unknown` until `tools/parser_expand.py` corroborated each against
a documented `[General]` key across a **real 64-save corpus** (Pacifist + Genocide)
at **100% agreement, 64/64 saves** — evidence, not assumption. The same run
reconfirmed `file0[1] ↔ Love` (64/64) and, crucially, **refused** `[General].Time`
(only 58% — it drifts between the file0 snapshot and the ini write), so it stays
unmapped. A candidate is promoted only at 100% over a meaningful sample; one
counterexample means we don't claim it. Re-run the engine on any corpus:
`python3 tools/parser_expand.py <corpus_dir>`.

### Cross-source corroboration (the wall at parse time)
`love`, `kills`, `room`, and `fun` are recorded in **both** `file0` and
`undertale.ini`. When both are present the parser checks them against each other
(`save_parser.corroborate`): agreement promotes the field to **confirmed** (two
independent recordings concur — our strongest evidence); disagreement keeps the
`file0` (save-slot) value, drops confidence to **low**, and emits a warning (a
likely edited save). It never silently picks a side or averages. Across the real
corpus this held at **256/256** field-checks in agreement — the conflict path stays
dormant on legitimate saves and fires only on tampered ones.

## `undertale.ini` — flags
Standard INI (`[section]` + `key=value`, values double-quoted). We parse it into
lowercased `{section: {key: value}}` and read a curated allow-list of documented
`[General]` keys **by name** (case-insensitive), returning `None` when absent:
`Name`, `Love`, `Kills`, `Room`, `RoomName`, `Time`, `Gold`, `Fun`. Unknown keys
are preserved but not interpreted.

## Route detection — the moral spine
The route (Pacifist / Neutral / Genocide) is **derived** from real signals, never
assumed. See `route_detection.py`:

| Observed | Route | Confidence |
|---|---|---|
| LOVE 20 (the ceiling) | Genocide | high |
| LOVE 1 and 0 kills | Pacifist | medium* |
| LOVE > 1 and/or recorded kills | Neutral | medium |
| no readable LOVE and no kills | undetermined | unknown |

\* Pacifist is capped at **medium** on purpose: a no-kill run is *necessary* but not
*sufficient* for True Pacifist — confirming that additionally needs befriend/date
flags whose exact ini indices vary across game versions. We say so in the grounding
rather than over-claiming.

### Verified against a real save corpus
The parser's field mapping was confirmed against a real corpus of Undertale saves
(file0 line 0 = name, line 1 = LOVE, line 2 = max HP; `[General]` keys `Love` /
`Kills` / `Room`). Two findings shaped the detector:

1. **Save-editor files are often internally contradictory.** Many community saves
   are positioned at a scene with maxed stats, so LOVE and the recorded kill count
   can disagree (e.g. a save labelled "True Pacifist" carrying **LOVE 20 + Kills 0**).
2. **The `[General] Kills` value is unreliable** — it can be an edited/garbage value
   (e.g. `99999999999`, `37.000000`) or a per-area counter — so it is treated as a
   *co-signal*, never as definitive on its own.

**Contradiction guard:** when LOVE and the recorded kills point in opposite
directions — LOVE 20 (max, implies near-total killing) with Kills 0, or LOVE 1
(no EXP) with Kills > 0 — the route is `undetermined`. We refuse to guess a route
over self-contradicting facts. This is the north star applied to messy real data:
a wrong route is worse than an honest "I can't tell."

A consequence worth stating plainly: a curator's **folder label** (their intended
scene) is *not* always derivable from the save's bytes. The detector reports what
the save actually says and declines when that is ambiguous — it does not infer the
author's intent.

### Honest scope note
Confirming a *completed* Genocide run canonically depends on per-area "clear" flags
whose indices are version-dependent. This detector uses the conservative documented
subset (LOVE, total kills, named ini keys) and is explicit about confidence. When
signals are absent or contradictory it returns **`undetermined`** — it will never
fabricate a route to fill a blank, because a wrong route breaks immersion and trust
faster than an honest "I can't tell yet."

## Fixtures
The test fixtures under `tests/fixtures/` are **synthetic, hand-authored to follow
this format** — not real game saves, no copyrighted data. See that folder's README.
