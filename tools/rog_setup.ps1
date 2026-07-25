<#
.SYNOPSIS
    One-shot setup for undertale-vera on a Windows handheld (ROG Xbox Ally X).

.DESCRIPTION
    Sets the app up to run ENTIRELY on the handheld: Python + uvicorn + Ollama,
    Guided Mode watching the handheld's own save. No network, no home server —
    it works on a car ride with the wifi off.

    Steps, each skipped if already satisfied:
      1. Python 3 (winget)
      2. virtualenv + requirements.txt
      3. Ollama (winget) + the chat model
      4. Extract art from the handheld's OWN game install → the authentic skin
      5. Write start-ember.ps1 + a Start Menu shortcut

    Re-runnable. Run it again after a `git pull` to re-sync deps and art.

.PARAMETER Model
    Ollama model to pull. Default llama3.1:8b — comfortable on 24 GB with room
    to spare. Try a larger model if you want more from the characters.

.PARAMETER Port
    Local port. Default 9092.

.PARAMETER SkipArt
    Skip art extraction (keeps the committed original look).

.PARAMETER Tv
    Launch in TV mode: larger type for across-the-room reading, plus an inset
    so nothing lands in the band TVs overscan away. Use when the handheld is
    docked to a television over HDMI. Toggleable any time with the controller's
    Options button, so this only sets the default.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File tools\rog_setup.ps1

.NOTES
    The extracted art is gitignored and stays on this device — see
    docs/LOCAL_SKIN_MANIFEST.md. Never copy static/assets/local/ off the machine.
#>
[CmdletBinding()]
param(
    [string]$Model = "llama3.1:8b",
    [int]$Port = 9092,
    [switch]$SkipArt,
    [switch]$Tv
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot

function Step($n, $msg) { Write-Host "`n[$n] $msg" -ForegroundColor Cyan }
function Ok($msg)       { Write-Host "    OK  $msg" -ForegroundColor Green }
function Warn($msg)     { Write-Host "    !   $msg" -ForegroundColor Yellow }

function Have($cmd) { $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue) }

Write-Host "undertale-vera — handheld setup" -ForegroundColor Magenta
Write-Host "repo: $repo"

# ── 1. Python ────────────────────────────────────────────────────────────────
Step 1 "Python 3"
if (Have "python") {
    Ok (python --version 2>&1)
} else {
    if (-not (Have "winget")) {
        throw "winget not available — install Python 3.12 manually, then re-run."
    }
    Warn "installing Python 3.12 via winget …"
    winget install --id Python.Python.3.12 --silent --accept-package-agreements `
                   --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not (Have "python")) {
        throw "Python installed but not on PATH — open a new terminal and re-run."
    }
    Ok (python --version 2>&1)
}

# ── 2. venv + dependencies ───────────────────────────────────────────────────
Step 2 "virtualenv + dependencies"
$venv = Join-Path $repo ".venv"
$py   = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $py)) {
    python -m venv $venv
    Ok "created .venv"
} else {
    Ok ".venv exists"
}
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r (Join-Path $repo "requirements.txt") --quiet
& $py -m pip install Pillow --quiet     # required by the art pipeline
Ok "dependencies installed"

# ── 3. Ollama + the model ────────────────────────────────────────────────────
Step 3 "Ollama"
if (Have "ollama") {
    Ok "ollama present"
} else {
    if (-not (Have "winget")) { throw "winget unavailable — install Ollama manually." }
    Warn "installing Ollama via winget …"
    winget install --id Ollama.Ollama --silent --accept-package-agreements `
                   --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

# the server must be up before a pull will work
$running = $false
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing `
                      -TimeoutSec 3 | Out-Null
    $running = $true
} catch { $running = $false }
if (-not $running) {
    Warn "starting the Ollama server …"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing `
                              -TimeoutSec 2 | Out-Null
            $running = $true; break
        } catch { }
    }
}
if ($running) {
    Ok "ollama server responding"
    $tags = (Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" `
                               -UseBasicParsing).Content
    if ($tags -like "*$Model*") {
        Ok "model $Model already pulled"
    } else {
        Warn "pulling $Model (several GB — one time, needs network) …"
        ollama pull $Model
        Ok "model ready"
    }
} else {
    Warn "Ollama not responding. The app still runs — it degrades to Spark,"
    Warn "the model-less voice, which is grounded but terser."
}

# ── 4. the authentic local skin ──────────────────────────────────────────────
Step 4 "art extraction (authentic skin)"
if ($SkipArt) {
    Warn "skipped (-SkipArt) — keeping the committed original look"
} else {
    # find_game_dir reads Steam's libraryfolders.vdf, so a game on the microSD
    # is found without hardcoding a drive letter.
    & $py (Join-Path $repo "tools\extract_undertale_assets.py")
    if ($LASTEXITCODE -ne 0) {
        Warn "extraction failed — is the game installed on this device?"
        Warn "the app still runs; it keeps the original art."
    } else {
        & $py (Join-Path $repo "tools\map_local_skin.py")
        Ok "authentic skin ready (art stays on this device — never copy it off)"
    }
}

# ── 5. launcher ──────────────────────────────────────────────────────────────
Step 5 "launcher"
$start = Join-Path $repo "start-ember.ps1"
# ?tv=1 sets TV mode on first load; the controller's Options button toggles it
# afterwards and the choice persists, so this is only the default.
$tvQuery = if ($Tv) { "/?tv=1" } else { "" }
if ($Tv) { Ok "TV mode will be on by default" }
@"
# Launches undertale-vera locally and opens it as an app window.
# Generated by tools/rog_setup.ps1 — safe to edit.
`$repo = `$PSScriptRoot
`$py   = Join-Path `$repo ".venv\Scripts\python.exe"
`$port = $Port

# Ollama first, so the characters have their voice ready.
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
}

`$env:UNDERTALE_VERA_SKIN = "authentic"
`$env:UNDERTALE_VERA_BACKEND = "ollama"
`$env:OLLAMA_MODEL = "$Model"

# ── performance ──────────────────────────────────────────────────────────
# KEEP_ALIVE is the single biggest win in felt speed. By default Ollama
# evicts an idle model after ~5 minutes, so the next reply pays several
# seconds re-reading gigabytes from disk. Play is bursty — a beat fires, a
# character answers, then nothing for a while — which is exactly the pattern
# that keeps hitting a cold model. -1 pins it in RAM for the session; on
# 24 GB an 8B model is a small price for never paying that stall again.
`$env:OLLAMA_KEEP_ALIVE = "-1"
# Cheaper attention: less memory per token and faster long contexts.
`$env:OLLAMA_FLASH_ATTENTION = "1"
# One player, one conversation. Parallel slots would divide the context
# window between requests that never arrive.
`$env:OLLAMA_NUM_PARALLEL = "1"

Start-Process -FilePath `$py ``
    -ArgumentList "-m","uvicorn","undertale_vera_app:app","--host","127.0.0.1","--port","`$port" ``
    -WorkingDirectory `$repo -WindowStyle Hidden

# wait for it to answer before opening the window
for (`$i = 0; `$i -lt 40; `$i++) {
    Start-Sleep -Milliseconds 500
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:`$port/api/health" ``
                          -UseBasicParsing -TimeoutSec 2 | Out-Null
        break
    } catch { }
}

# If Ember has been INSTALLED as an app (Edge > ... > Apps > Install), Windows
# owns the window and this launcher only needs the server. Otherwise fall back
# to app mode, which looks the same but leaves no Start Menu identity behind.
# --start-fullscreen matters on a TV: browser chrome is wasted space there, and
# there is no pointer to dismiss it with.
Start-Process "msedge.exe" -ArgumentList "--app=http://127.0.0.1:`$port$tvQuery","--start-fullscreen"
"@ | Set-Content -Path $start -Encoding UTF8
Ok "wrote start-ember.ps1"

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Ember.lnk"
try {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($startMenu)
    $lnk.TargetPath = "powershell.exe"
    $lnk.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$start`""
    $lnk.WorkingDirectory = $repo
    $lnk.Description = "Ember — the save remembers"
    $lnk.Save()
    Ok "Start Menu shortcut created"
} catch {
    Warn "could not create the shortcut: $_"
}

# ── done ─────────────────────────────────────────────────────────────────────
Write-Host "`nSetup complete." -ForegroundColor Magenta
Write-Host @"

  Start it:   .\start-ember.ps1      (or the 'Ember' Start Menu entry)
  Then:       http://127.0.0.1:$Port

  ── Make it a real app (do this once) ──────────────────────────────────────

  In the Ember window: ... menu > Apps > "Install this site as an app".

  That gives a genuine Windows app — its own icon, its own Start Menu and
  taskbar entry, its own window with no browser chrome. It is NOT a wrapped
  browser copy: it reuses the WebView engine Windows already ships, so it adds
  no runtime and no memory beyond the page itself. An Electron-style bundle
  would ship a second copy of Chromium and be strictly slower.

  Pin it to the taskbar, or add it as a non-Steam game for the Xbox library.

  Guided Mode: open the app and it will offer the save folder it found on this
  device (%LOCALAPPDATA%\UNDERTALE). Point it there and it reacts as he plays.
  Read-only — the app never writes to a save.

  ── Playing on a TV with a controller ──────────────────────────────────────

  Pair the DualSense first: hold CREATE (left of the touchpad) + PS until the
  light bar double-flashes, then add it under Bluetooth settings. Over USB-C it
  just works, no pairing. Either way Windows reports it as a standard gamepad,
  which is what the app reads.

  Controls:
    D-pad / left stick   move between things
    Cross (X)            select
    Circle (O)           back, close a menu, leave a text box
    Options              toggle TV mode (bigger type + overscan inset)

  Run setup with -Tv to start in TV mode by default. If the edges of the app
  are cut off by the television, TV mode is the fix — most sets crop a few
  percent of every edge and never mention it.

  ── ──────────────────────────────────────────────────────────────────────────

  To add it to the Xbox full-screen experience, add start-ember.ps1 as a
  non-Steam game so it appears as a tile in the library.

  The extracted art lives in static\assets\local\ — gitignored, and it stays on
  this device.
"@
