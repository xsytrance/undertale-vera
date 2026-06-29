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

Out-of-range or unparseable values become `None` with confidence `unknown`, and a
warning is recorded — **never** a guessed value.

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
