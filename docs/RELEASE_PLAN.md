# Release Plan — private dev repo, public clean repo, two websites

*Written July 2 2026, from the maker's own words. This is the master checklist
for taking Ember public. The focus is the newbie version; the pro version gets
polished later.*

## The shape of it

1. **This repo stays the maker's — private.** (Done: flipped to private
   July 2 2026. It had been public since the MultiVera reveal.)
2. **A cleaned public copy** — thoroughly checked: no saves (except possibly
   one per route *with the original poster's blessing*), no private
   information, no keys, nothing personal. **Very very important.**
3. **Website #1 — the "instant" newbie version.** Immediately shareable,
   immediately usable: 🕯 Spark only, zero setup, heavily trimmed feature set,
   and a really good walkthrough of *how to find your save file, upload it,
   and play around*.
4. **Website #2 — the "pro" version.** For people who know what they're
   doing: local LLM (Ollama) or an OpenRouter key, with recommended models.
   All features. Polished **later** — pros can try the newbie site first and
   decide if the full thing is worth their time.

## Architecture decision (recommended)

**One codebase, two deployments** — an `EMBER_EDITION=lite|pro` switch, not a
fork. The lite site runs the same app with the power source locked to Spark
and the nav trimmed; the pro site runs everything. One bug fix lands on both;
the public repo is the single source for both sites.

## The lite feature cut (proposal — trim hard, newbies must not drown)

| Keeps (lite) | Why |
|---|---|
| **Read a save** (the lit front door + START HERE) | the entire point |
| The save facts panel / route badge | instant payoff, zero AI |
| **Chat** (Spark voices) | grounded, in-voice, works with no model |
| **Judgment** | deterministic verdict — a great "wow" for zero cost |
| **Sound Test** | pure fun, no LLM (audio ships with the site, not the repo) |
| **Credits** | non-negotiable |
| One small "About / how this works" page | trust + the pro-site pointer |

| Cut from lite (pro only) |
|---|
| Council · Timeline · Keepsake Journal · Chronicle · Report Cards |
| Across Your Saves · Constellation · Two-Save Divergence |
| Reach-outs (proactive) · Living Memory · chat style dials |
| Guided Mode · The Commons · Prompt Workshop · MultiVera page |
| The power picker itself (locked to 🕯; a "want more? → pro site" card instead) |

## The public-copy cleaning checklist

- [x] **Fresh git history** — a single initial commit. Never migrate history
      (the dev history contains the tailnet IP in 308 commits, session
      references, and evolution the world doesn't need).
- [x] Default `OLLAMA_HOST` → `127.0.0.1` (was the tailnet IP; fixed in dev
      first so it never re-leaks).
- [x] Remove/withhold private-context docs: `PRIME_BRIEF.md`, `BUILDLOG.md`,
      `ROADMAP.md`, `RELEASE_PLAN.md` (this file), anything agent-workflow-ish.
      Review every doc that ships.
- [x] **Fixtures**: `tests/fixtures/filech1_0*` are real corpus saves (they
      carry a real player's name). Replace with **synthetic fixtures we
      generate ourselves** (we know the format byte-for-byte) so the public
      repo needs nobody's permission.
- [ ] **Sample saves for users** (one per route, so newbies can play without
      owning a save): ONLY with permission — ask u/HylianAngel (Reddit) and
      NICKISBAD (GitHub issue). Until granted: ship none; the walkthrough
      carries the experience.
- [x] Sweep the tree before first push: tailnet IPs (`100.`), `/home/` paths,
      emails, `ember_power.json`, `guided_watch.json`, `saves/`, `workspace/`,
      generated art, audio (already gitignored — verify), AgentMail anything.
- [x] Automated guard: a CI job on the public repo greping for the same
      patterns, so a leak can't merge.
- [x] **LICENSE file** — MIT (maker approved); music is
      already CC BY 4.0.
- [x] README rewritten newbie-first (what it is → try it at the lite site →
      run it yourself → pro site).

## The newbie walkthrough (website #1's centerpiece)

"Where is my save file?" — per platform, with pictures, in the reading font:

- **Windows**: press `Win+R`, paste `%LOCALAPPDATA%\UNDERTALE` → `file0` +
  `undertale.ini`
- **Mac**: Finder → Go → Go to Folder →
  `~/Library/Application Support/com.tobyfox.undertale`
- **Linux**: `~/.config/UNDERTALE` (Steam/Proton:
  `steamapps/compatdata/391540/pfx/drive_c/users/steamuser/Local Settings/Application Data/UNDERTALE`)
- **Deltarune**: same places, `DELTARUNE` folder, `filech1_0`
- Reassure on every step: **read-only. Your save is never changed. Unknown
  things stay unknown — the characters never make your story up.**

## The pro page (later, but on record)

- Recommended local model: **Ollama + `llama3.1:8b`** (what the dev box runs;
  8B is plenty because the prompts carry the facts).
- Recommended BYOK: the curated OpenRouter list already in `power_config.py`
  (free Llama 3.1 8B → DeepSeek → Gemini Flash → Claude Haiku 4.5).
- Docs already written: PIPELINES.md (Ollama/ComfyUI/HeartMuLa/MusicGen),
  the Prompt Workshop, GAME_PACKS.md.

## Repo mechanics (the "do I need to create it myself?" answer)

No — the `gh` CLI on this box can create and push it. Recommended naming:

- Rename this private repo → **`undertale-vera-dev`** (private, full history,
  the maker's).
- Create fresh **`undertale-vera`** (public, single-commit history) — this
  preserves the GitHub URL already circulating from the MultiVera page.

## Open questions for the maker

1. ~~Public repo name~~ — done: public `undertale-vera` is live; this repo is `undertale-vera-dev`.
2. ~~Code license~~ — MIT, shipped.
3. ~~Lite feature cut~~ — approved and shipped (PR #95).
4. Hosting for the two sites (the box + a tunnel? a small VPS? a PaaS?) —
   needed before the sites are truly "shareable"; not needed to build them.
5. Sample-save permissions: maker DMs u/HylianAngel + opens the NICKISBAD
   issue when ready.

## Build order

1. ✅ Private flip + history sweep + IP default fix (July 2 2026)
2. ✅ `EMBER_EDITION` switch + lite trim + Spark lock + pro pointer (PR #95)
3. ✅ Newbie walkthrough in the saves view (PR #95)
4. ✅ Synthetic fixtures (PR #96)
5. ✅ Public repo live: github.com/xsytrance/undertale-vera (single-commit history, MIT, leak-guard + CI green July 2 2026)
6. Deploy lite site → share
7. Pro site polish (later, on the maker's word)
