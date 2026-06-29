# Test fixtures — SYNTHETIC saves

These `file0` / `undertale.ini` fixtures are **hand-authored to follow the
documented Undertale save format**. They are **not** real game saves and contain
no copyrighted game data — they exist solely to exercise the parser, route
detection, and the SaveTruth wall deterministically.

The parser only assigns meaning to version-stable, community-documented fields
(file0 line 0 = name, line 1 = LOVE, line 2 = max HP; named `[General]` ini keys).
Everything else is preserved raw and left `null` — never guessed.

| Fixture pair | Intended route signal |
|---|---|
| `file0_pacifist` + `undertale_pacifist.ini` | LOVE 1, 0 kills → Pacifist (medium) |
| `file0_genocide` + `undertale_genocide.ini` | LOVE 20 → Genocide (high) |
| `file0_neutral`  + `undertale_neutral.ini`  | LOVE 6, some kills → Neutral (medium) |
| `file0_ambiguous` (no ini)                  | unreadable LOVE → undetermined |
