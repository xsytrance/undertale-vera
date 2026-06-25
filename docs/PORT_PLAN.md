# Port Plan — undertale-vera Spine 0 "The Save Remembers"

STEP 0 deliverable: the portable MultiVera spine borrowed from **fft-psx-vera**
(read-only reference), with all FFT-specific logic fenced out.

## Portable spine (ported the PATTERN, not FFT content)
| fft-psx-vera reference | undertale-vera | What carried over |
|---|---|---|
| `save_parser.py` | `save_parser.py` | null-guard reads, warnings-not-crashes, unknown→null honesty |
| `save_truth.py` | `save_truth.py` + `route_detection.py` | normalized schema, confidence enum, `prompt_contract` wall |
| `prompt_builder.py` | `prompt_builder.py` | two-bucket wall: SaveTruth sacred + personality free |
| `lore_kb.py`/`character_config.py` | `character_config.py` | character registry dict |
| `living_memory.py` | `living_memory.py` | ask/remember/recall pure fns (FFT stat-seeding dropped) |
| Ollama chat (httpx) | `llm_client.py` (Anthropic, `claude-opus-4-8`) | grounded, mockable chat call |
| `tools/autopilot_probe.py` | `inspector.py` | QA sweep reused wholesale; undertale surfaces registered |
| `_get_character_avatar` | `avatar_resolver.py` | resolver fallback chain (FFT name-maps dropped) |
| frontend music layer | `static/js/music.js` | global ambient music (React→vanilla) |
| `comfy_workflows/portrait.json` | `comfy_workflows/portrait_undertale.json` | ComfyUI pixel-portrait pipeline, new style |
| `tests/two_bucket_wall_test.py` | `tests/two_bucket_wall_test.py` | regression: facts sacred vs personality free |

## FFT-only — deliberately NOT ported
Party roster, job classes, Brave/Faith/Zodiac, War Council, Dream Team,
equipment/inventory grounding, gold, Commander reunion, campfire-as-party, FFT
name maps.

## Undertale-specific (the chosen first hook)
- `route_detection.py` — the moral spine; route derived from real flags,
  `undetermined` when ambiguous, never guessed.
- SaveTruth's `route` block + `play_state` (name/LOVE/HP) replace FFT's
  party/equipment.

## Standing rules honored
Parser-truth (unknowns→null, read-only saves) · commit allow-list only · DB
ADD-only · portable spine fenced from game logic · no scope creep (this is
**scaffold + chat**, not the whole app).
