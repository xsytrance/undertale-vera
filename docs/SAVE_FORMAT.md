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
| LOVE 20 **and** a boss-kill flag set | Genocide | **confirmed** |
| LOVE 20 (the ceiling) | Genocide | high |
| LOVE 1, 0 kills, **and a befriend/date flag** | Pacifist | **high** |
| LOVE 1 and 0 kills (no befriend flags yet) | Pacifist | medium* |
| LOVE > 1, recorded kills, **and/or a boss-kill flag** | Neutral | medium |
| boss-kill flag set **but** LOVE 1 (no EXP) | undetermined | low (contradiction) |
| same character **spared AND killed** | undetermined | low (contradiction) |
| no readable LOVE and no kills | undetermined | unknown |

\* Pacifist without befriend flags stays **medium**: a no-kill run is *necessary* but
not *sufficient* for True Pacifist — and is indistinguishable from a no-kill Neutral
until the dating begins.

### Befriend/date flags (True Pacifist requirements)
A no-kill run alone can't tell a budding True Pacifist from a passive no-kill Neutral.
The date/befriend flags settle it — they're reachable **only** on a no-kill path
(the Undyne date is gated behind killing nothing), so their presence is decisive.
Allow-list `route_detection.BEFRIEND_FLAGS`:

| Flag | Meaning | Corpus (set in) |
|---|---|---|
| `[Papyrus] PD` | Papyrus dated | 37/49 Pacifist, **0/15 Genocide** |
| `[Undyne] UD` | Undyne dated/befriended | 27/49 Pacifist, **0/15 Genocide** |
| `[Alphys] AD` | Alphys dated | 9/49 Pacifist, **0/15 Genocide** |

With any present (and LOVE 1 + 0 kills), Pacifist is reported at **high**; an early
no-kill save with none stays **medium**. These never *create* a Pacifist call — kills
or a kill flag still override — they only grade an already-no-kill run. The flags and
their meanings were mined by `tools/flag_mine.py` and cross-checked against the
[True Pacifist Route](https://undertale.fandom.com/wiki/True_Pacifist_Route) docs
(date Papyrus → Undyne → Alphys, having killed no one).

**Spare/kill contradiction:** the same character marked both spared (`TS`/`PS`) and
killed (`TK`/`PK`) is impossible in a real run, so it resolves to `undetermined` —
the mercy-side mirror of the LOVE/kills contradiction guard.

### Per-character disposition (SACRED chat grounding)
The same flags drive `character_disposition.py`, which derives a per-character
outcome — **killed / spared / befriended / unknown** — for each major character
(`DISPOSITION_FLAGS`: Toriel `tk`/`ts`, Papyrus `pk`/`ps`/`pd`, Undyne `ud`,
Alphys `ad`). It feeds a SACRED "WHO YOU'VE MET" block into the chat prompt so a
character can speak to a *real* outcome ("you befriended my brother" / "you killed
Toriel") — never a guess. `befriended` outranks `spared`; a character flagged both
killed and spared is `contradicted` and is **not** asserted as any outcome. No flag
→ `unknown` → simply not listed. Surfaced in `SaveTruth.dispositions` and the
provenance overlay.

### Boss-kill flags (a hard "violence occurred" signal)
`undertale.ini` records binary kill flags per major character. We use a conservative,
corpus-corroborated allow-list (`route_detection.KILL_FLAGS`):

| Flag | Meaning | Corpus (set in) |
|---|---|---|
| `[Toriel] TK` | Toriel killed | 14/15 Genocide, **0/49 Pacifist** |
| `[Papyrus] PK` | Papyrus killed | 12/15 Genocide, **0/49 Pacifist** |

A set kill flag cannot coexist with a true no-kill run, so it: confirms killing
beyond doubt (a Neutral floor); **promotes LOVE 20 to a `confirmed` Genocide** (two
independent records of total slaughter); and, if it somehow appears with LOVE 1,
exposes a **contradiction** (killing a boss raises LOVE) → `undetermined`. It never
*upgrades* a mid-run save to Genocide — killing some bosses is not the full clearance
Genocide demands, so those stay Neutral. The allow-list was derived by
`tools/flag_mine.py` (the ini analog of `tools/parser_expand.py`), which also
surfaced the Pacifist-side spare flags `[Toriel] TS` / `[Papyrus] PS` for future use.

### Cross-checked against community documentation
The corpus findings were independently corroborated against community references
([pcy.ulyssis.be/undertale/flags](https://pcy.ulyssis.be/undertale/flags),
[CYBERPEDIA flags](https://cyberpedia.miraheze.org/wiki/User:Emeryradio-fduser/Flags),
[Undertale Wiki: SAVE](https://undertale.fandom.com/wiki/SAVE)). They agree on
`TK = Toriel killed`, `PK = Papyrus killed`, and on the file0 indices we promoted —
**line 36 = Fun, line 548 = room, line 549 = time** (1-indexed; our 0-indexed
`fun@35` / `room@547` / refused `time@548`). One community claim (line 3 = *current*
HP) did **not** survive corpus verification: index 2 tracks `16 + 4·LV` exactly
across all 64 saves (LV1→20, LV13→68, LV19→92) while index 3 is a constant 20 — so
index 2 is **max HP** (now confidence `high`), and we trusted the data over the
forum note. Verification beats deference.

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
