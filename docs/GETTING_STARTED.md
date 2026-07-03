# Getting Started — from a blank computer to talking with your save

This guide assumes **nothing**. If you've never opened a terminal, never
installed Python, and aren't sure what "clone a repo" means, you're exactly who
it's written for. Follow it top to bottom and you'll end with Ember running on
your own machine, reading your Undertale or Deltarune save, with the cast
talking back.

**The three tiers, so you know where you're headed:**

| Tier | What it needs | What you get |
|---|---|---|
| 🕯 **Spark** | nothing past Step 4 | every feature, scripted save-grounded voices — works instantly |
| 🖥 / 🔌 **Local model** | a model runtime (Step 6) | free, private, full-personality chat on your own hardware |
| 🔑 **OpenRouter** | an account + API key (Step 6-alt) | hosted models, some free — no downloads, needs internet |

Ember is **fully usable at Spark**. Everything past Step 5 is optional polish.

---

## Step 0 — open a terminal

The terminal is just a window you type commands into. Every step below is
"type this, press Enter."

- **Windows** — press the Windows key, type `powershell`, press Enter.
  ("Windows PowerShell", the blue window, is the one you want.)
- **macOS** — press ⌘-Space, type `terminal`, press Enter.
- **Linux** — you probably know, but: Ctrl-Alt-T on most desktops.

Keep this window open for the whole guide.

## Step 1 — install Python (3.11 or newer)

Check whether you already have it. Type:

```
python3 --version
```

(On Windows, try `python --version` if that says "not found".)

If it prints `Python 3.11.x` or higher → skip to Step 2.

**Install it:**

- **Windows** — download from [python.org/downloads](https://www.python.org/downloads/),
  run the installer, and **tick the "Add python.exe to PATH" checkbox** on the
  first screen — this is the single most common setup mistake; don't skip it.
  Then close and reopen PowerShell so it notices.
- **macOS** — download from [python.org/downloads](https://www.python.org/downloads/)
  and run the installer (or `brew install python` if you use Homebrew).
- **Linux** — `sudo apt install python3 python3-pip python3-venv` (Debian/Ubuntu/Mint)
  or `sudo dnf install python3 python3-pip` (Fedora).

Re-run the version check to confirm before moving on.

## Step 2 — install git

Git fetches the code. Check first:

```
git --version
```

Any version number → skip ahead. Otherwise:

- **Windows** — download from [git-scm.com](https://git-scm.com/downloads), run
  the installer, accept every default, reopen PowerShell.
- **macOS** — type `git --version` again; macOS offers to install its
  command-line tools. Say yes.
- **Linux** — `sudo apt install git` / `sudo dnf install git`.

## Step 3 — get Ember

Three commands: fetch the code, step inside, make a private Python sandbox
(a "virtual environment" — it keeps Ember's packages from touching anything
else on your machine):

```
git clone https://github.com/xsytrance/undertale-vera
cd undertale-vera
python3 -m venv .venv
```

(Windows: use `python` instead of `python3` throughout.)

Turn the sandbox on — this one differs per OS:

- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`
  - If PowerShell complains about "running scripts is disabled", run
    `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
    once, say yes, and try again.
- **macOS / Linux:** `source .venv/bin/activate`

Your prompt grows a `(.venv)` prefix — that's how you know it's on. Now
install Ember's packages into it:

```
pip install -r requirements.txt
```

A minute of scrolling text is normal.

> Coming back another day? You only need `cd undertale-vera` + the activate
> command again — the clone and install are one-time.

## Step 4 — run it

```
uvicorn undertale_vera_app:app --port 9092
```

When it settles on a line like `Uvicorn running on http://127.0.0.1:9092`,
open your browser at:

**http://127.0.0.1:9092**

Three things to know:

- **The terminal window IS the app.** Leave it open while you use Ember;
  Ctrl-C in it shuts Ember down.
- **It's private.** Ember listens on `127.0.0.1` — reachable only from the
  computer it's running on. It isn't visible to your network or the internet,
  and it never connects to the project's authors or any server of theirs.
  (Don't add `--host 0.0.0.0` unless you deliberately want other devices on
  your own network to reach it.)
- **First visit:** a "Choose your power source" window pops up. Pick
  🕯 **Just play** for now — you can upgrade any time from ⚙ Settings.

## Step 5 — you're done (Spark tier)

Tap **＋ Read a save**, point it at your `file0` (Undertale) or `filech1_0`
(Deltarune) — the app has a built-in "where is my save file" walkthrough per
OS — and the Underground starts talking about *your* run. Route detection,
Judgment, the Council, the soundtrack, Guided Mode: all of it works at Spark,
no AI required.

Everything below is optional.

---

## Step 6 (optional) — put a real model behind the voices

### Option A: Ollama — the recommended local path

[Ollama](https://ollama.com) is a free app that runs open-weight language
models on your own machine. Private (nothing leaves your computer), no
account, no fees.

**1. Install it** — grab the installer for your OS at
[ollama.com/download](https://ollama.com/download) (Windows/macOS installers;
Linux is one `curl` command shown on that page). On Windows/macOS the app runs
in the background after install; on Linux, `ollama serve` starts it if it
isn't already running.

**2. Download a model** — in your terminal (any terminal, the sandbox doesn't
matter for this one):

```
ollama pull llama3.1:8b
```

It's a ~5 GB download, one time. Pick your model by how much RAM the machine has:

| Your RAM | Pull this | Notes |
|---|---|---|
| 8 GB | `llama3.1:8b` | the tested default — good voices |
| 16 GB+ | `llama3.1:8b` or `qwen2.5:14b` | 14B is noticeably sharper, slower |
| 32 GB+ | anything up to `qwen2.5:32b` | luxury |
| less than 8 GB | stay on Spark, or use OpenRouter | small models get the facts wrong |

**3. Connect Ember to it** — in Ember: **⚙ Settings → Power source → 🖥 I run
local models**, then press **⌕ Detect installed**. Ember asks your Ollama
which models it has and lists them — pick one, press **Use this**, and watch
for **"✓ working"**. That's it. (Ollama on another machine on your network?
Type its address in the host box, e.g. `http://192.168.1.50:11434`, then
Detect.)

### Option B: vLLM, LM Studio, llama.cpp — any OpenAI-compatible server

Already running your own model server? "OpenAI-compatible" means it answers
`POST /v1/chat/completions` — the de-facto standard these all speak:

- **LM Studio** — the easiest GUI option: load a model, click the green
  **Start server** on the Developer tab; the URL is `http://127.0.0.1:1234/v1`.
- **vLLM** — `vllm serve Qwen/Qwen2.5-7B-Instruct` →
  `http://127.0.0.1:8000/v1`, model name as passed to serve.
- **llama.cpp** — `llama-server -m yourmodel.gguf --port 8080` →
  `http://127.0.0.1:8080/v1`.

In Ember: **⚙ Settings → Power source → 🔌 My own server**, paste the base
URL, type the model name your server expects, add an API key only if your
server requires one, **Use this** → "✓ working".

### Option 6-alt: OpenRouter — hosted, no downloads

Make a free account at [openrouter.ai](https://openrouter.ai), create an API
key (top-right menu → Keys), then in Ember: **⚙ Settings → Power source → 🔑 I
have an API key**, paste it, and pick a model — the list includes free-tier
options. Your key is stored only on the machine running Ember, in an
owner-only file, and the app never displays it again unmasked.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python3: command not found` / `not recognized` | Python isn't installed or isn't on PATH — redo Step 1; on Windows, the PATH checkbox |
| `pip: command not found` | your venv isn't active — redo the activate command in Step 3 |
| `uvicorn: command not found` | same cause: activate the venv, and re-run the `pip install` line if needed |
| `address already in use` | something else has port 9092 — run with `--port 9093` and browse to that instead |
| Browser shows nothing / "can't connect" | is the terminal still running uvicorn? Right URL (`http://127.0.0.1:9092`, not https)? |
| Power test says "✗ Ollama unreachable" | is Ollama actually running? (`ollama list` should answer; on Linux start `ollama serve`) |
| Detect finds 0 models | Ollama runs but has nothing pulled — `ollama pull llama3.1:8b` |
| Chat is slow or the machine swaps | the model is too big for your RAM — pull a smaller one and re-Detect |
| Windows Firewall asks about Python/Ollama | allow it — both only listen on your own machine by default |
| Replies feel scripted | you're in Spark mode — that's the honest fallback; check ⚙ → Power source says "✓ working" |

## Where the game keeps your saves

- **Windows** — `%LOCALAPPDATA%\UNDERTALE\` (paste that into Explorer's
  address bar) — `file0`, plus `undertale.ini`. Deltarune: `%LOCALAPPDATA%\DELTARUNE\`.
- **macOS** — `~/Library/Application Support/com.tobyfox.undertale/`
- **Linux (native/Proton)** — `~/.config/UNDERTALE/` (Proton installs keep it
  under the Steam prefix — the in-app guide shows the full path).

Ember only ever **reads** these files. It cannot change your save.

## Further up the ladder

`docs/PIPELINES.md` is the advanced recipe book — the full local-everything
tier (art generation, RAG lore, the works). `docs/GAME_PACKS.md` is how you
teach the engine a new game entirely.
