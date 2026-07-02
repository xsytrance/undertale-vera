# Testing brief — undertale-vera (Spine 0 + beats)

A self-contained guide for testing this project from a cold start. No prior context
assumed.

## What this is
A save-aware companion app for **Undertale**: it parses a player's save, normalizes
it into a `SaveTruth` (including the **route** — Pacifist / Neutral / Genocide), and
lets in-game characters chat *grounded in the real save*. Backend is FastAPI; the
frontend is dependency-free vanilla JS on a static shell.

**The governing principle — verify this above all:** *Facts are sacred, feelings are
free.* The save's facts (name, LOVE, route, kills) must never be invented or
overridden by the LLM; unknown fields are `null`, never guessed; an ambiguous route
is `"undetermined"`, never a guessed one. The "two-bucket wall" separates SACRED
parser truth from FREE character personality/memory.

## Where the code is
- Branch: `claude/sweet-darwin-0azp2z` (draft PR #1; base `main` is an intentionally
  empty initial commit — the repo had no prior history, so the whole scaffold is the
  diff).
- Backend modules at repo root: `undertale_vera_app.py`, `save_parser.py`,
  `route_detection.py`, `save_truth.py`, `prompt_builder.py`, `living_memory.py`,
  `ledger.py`, `judgment.py`, `llm_client.py`, `inspector.py`; plus
  `backend/models.py`, `static/` (UI), `tests/`, `docs/` (see the git history for
  the full feature map).

## Setup
```bash
git checkout claude/sweet-darwin-0azp2z
python3 -m venv .venv && . .venv/bin/activate   # Python 3.11+
pip install -r requirements.txt
```
**LLM key (optional):** real in-voice chat/judgment needs
`export ANTHROPIC_API_KEY=sk-ant-...` (model `claude-opus-4-8`). **Without a key,
everything still works** — chat and "Judgment → let them say it" degrade to a
deterministic, still-grounded fallback; all parsing/route/truth/ledger/judgment-
readout is key-free.

## Tier 1 — unit tests (start here)
```bash
pytest -q          # expect: 39 passed
```
Covers parser, route detection, the SaveTruth wall, the two-bucket wall regression,
grounded chat (LLM mocked), the remembrance ledger, the Judgment beat, and
shelf/persistence.

## Tier 2 — API smoke
```bash
python3 -m uvicorn undertale_vera_app:app --port 9092 &
sleep 2
curl -s localhost:9092/api/health
# Upload a synthetic save (no real game save needed — fixtures ship in the repo):
curl -s -F "file0=@tests/fixtures/file0_genocide" \
        -F "undertale_ini=@tests/fixtures/undertale_genocide.ini" \
        localhost:9092/api/upload | python3 -m json.tool
curl -s localhost:9092/api/projects/1/judgment | python3 -m json.tool
```

**Expected SaveTruth per fixture** (upload `file0_X` + `undertale_X.ini` together):

| fixture | name | LOVE | route (confidence) | kills |
|---|---|---|---|---|
| pacifist | Frisk | 1 | **Pacifist** (medium) | 0 |
| genocide | Chara | 20 | **Genocide** (high) | 9 |
| neutral | Frisk | 6 | **Neutral** (medium) | 3 |
| `file0_ambiguous` (upload **alone**, no ini) | Frisk | `null` | **undetermined** (unknown) | `null` |

A **real** Undertale save works too: its `file0` + `undertale.ini`
(Windows: `%LOCALAPPDATA%\UNDERTALE\`).

## Tier 3 — UI (browser)
Open `http://127.0.0.1:9092`. Flow: **Read a save** (pick fixtures) → SaveTruth panel
+ route badge → click a character → **chat** → **Judgment** button → then **"Read a
later save (return visit)"** with a *different* fixture → the **"WHAT THE SAVE
REMEMBERS"** box shows the delta (e.g. *Pacifist → Genocide*). The "Your saves" shelf
switches between saves; transcripts persist across reload.

## Tier 4 — Inspector (deterministic QA sweep)
```bash
python3 inspector.py --base http://127.0.0.1:9092      # exit 0 = pass
```
The HTTP engine always runs (status codes + asset existence). If Playwright is
installed it also captures console errors + screenshots. In restricted/headless
environments where the browser binary isn't auto-discoverable, set
`UNDERTALE_VERA_CHROMIUM=/path/to/chrome`. External-CDN (Google Fonts) console
failures are already filtered — the CSS ships serif fallbacks, so they are not
defects.

## Acceptance checklist (the invariants that matter)
- [ ] `pytest -q` → 39 passed.
- [ ] **Route honesty:** ambiguous/unreadable input → `route: "undetermined"`, never a
  guessed route.
- [ ] **Unknowns → null:** unreadable fields are `null`, not zero/guessed (try
  `file0_ambiguous`).
- [ ] **Wall holds:** `save_truth.prompt_contract.save_truth_wins == true`; a memory
  write (`POST .../memory/{char}/remember`) does **not** change `save_data`; the
  snapshot ledger is **additive** (`refresh-save` appends, never overwrites —
  `GET .../save-memory` count grows, prior rows unchanged).
- [ ] **Judgment is verbatim:** `GET .../judgment` `facts` match the SaveTruth
  exactly; `honest_gaps` names every unknown; verdict matches the route.
- [ ] **Graceful degradation:** with no `ANTHROPIC_API_KEY`, chat returns
  `grounding.source == "deterministic_fallback"` and still references only real save
  facts.
- [ ] Inspector exits 0.

## Endpoint reference
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| POST | `/api/upload` | parse `file0`/`undertale.ini` → SaveTruth → new project (snapshot #1) |
| GET | `/api/projects` | the save shelf (route summary per save) |
| GET | `/api/projects/{id}/save-truth` | the normalized SaveTruth |
| POST | `/api/projects/{id}/refresh-save` | a return visit — re-read + append a snapshot |
| GET | `/api/projects/{id}/save-memory` | the remembrance ledger (chronological snapshots) |
| GET | `/api/characters` | character roster (+ avatar URLs) |
| POST | `/api/projects/{id}/chat` | grounded character chat |
| GET | `/api/projects/{id}/conversations/{character}` | persisted transcript |
| GET | `/api/projects/{id}/judgment` | deterministic judgment readout |
| POST | `/api/projects/{id}/judgment/speak` | in-voice judgment (LLM, grounded) |
| GET/POST | `/api/projects/{id}/memory/{character}[...]` | Living Memory (Bucket B) |

## Known/expected non-issues
- `main` is an intentionally empty base commit (fresh repo).
- Generated art (`static/assets/portraits/*.png`) is gitignored; sample portraits are
  placeholders — the real pixel portraits need a ComfyUI run with the new style LoRA.
- Character voices (Sans/Toriel/Papyrus/Flowey/Undyne) are our reinterpretation
  pending canonical-voice review (flagged in `character_config.py`).
