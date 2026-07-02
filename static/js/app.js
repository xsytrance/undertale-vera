/* ════════════════════════════════════════════════════════════════════════
   undertale-vera frontend — vanilla JS, no build step.
   Drives the Spine-0 backend: upload -> SaveTruth -> roster -> grounded chat ->
   the remembrance ledger -> the Judgment beat. Reuses the Determination
   Chronicle CSS. Route-aware music binds to the live SaveTruth route.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var state = { projectId: null, character: null, characters: [], history: {}, view: "chat" };

  // Global audio master — the top-bar volume/mute every sound respects (the music
  // bed, typing/character voices, UI blips, and the Sound Test). gain() returns 0
  // when muted; each audio layer multiplies its own output by it.
  var AudioBus = {
    volume: 1, muted: false, _fns: [],
    load: function () {
      try { var s = JSON.parse(localStorage.getItem("uv_audio") || "{}");
        if (s.volume != null) this.volume = s.volume; if (s.muted != null) this.muted = s.muted; } catch (e) {}
    },
    save: function () { try { localStorage.setItem("uv_audio", JSON.stringify({ volume: this.volume, muted: this.muted })); } catch (e) {} },
    gain: function () { return this.muted ? 0 : this.volume; },
    setVolume: function (v) { this.volume = Math.max(0, Math.min(1, v)); if (this.volume > 0) this.muted = false; this.save(); this._notify(); },
    setMuted: function (m) { this.muted = !!m; this.save(); this._notify(); },
    onChange: function (fn) { this._fns.push(fn); },
    _notify: function () { var g = this.gain(); this._fns.forEach(function (fn) { try { fn(g); } catch (e) {} }); },
  };
  window.AudioBus = AudioBus;

  function $(id) { return document.getElementById(id); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  // ── the view router ───────────────────────────────────────────────────────
  // Exactly one stage view is .active at a time. Switching a character or a
  // feature swaps the stage only — the rails never move, nothing scrolls away.
  var VIEWS = ["chat", "council", "timeline", "journal", "constellation", "chronicle", "judgment", "reports", "soundtest", "guided", "commons", "howitworks", "multivera", "credits", "workshop", "saves"];

  // Original "Determination" aphorisms — OUR lines (not Undertale quotes) — for the
  // rail's quote-of-the-day and the chat empty state, so the shell never feels bare.
  var APHORISMS = [
    "Every save is a promise you make to yourself.",
    "The Underground remembers what the surface tries to forget.",
    "Numbers keep score. They don't keep the whole story.",
    "Determination is just refusing to let the story end.",
    "Mercy costs nothing and rewrites everything.",
    "A single choice can echo through every reload.",
    "The kindest run is rarely the easiest one.",
    "You can reset the save. You can't reset the memory.",
    "Dust settles, but it is never truly gone.",
    "To spare someone is to believe they can still change.",
    "Every ending was once a beginning you dared to reach.",
    "Even in the dark, a soul keeps its color.",
    "What you carry out matters more than what you leave behind.",
    "Curiosity opened the door; determination walked through it.",
    "The flowers remember the shape of your resolve.",
    "Kindness is a courage the Underground never forgets.",
  ];
  var DR_APHORISMS = [
    "The Dark needs the Light, and the Light needs the Dark.",
    "A prophecy is just a story until someone walks it.",
    "Your choices don't matter. (They matter enormously.)",
    "Every vessel is empty until somebody refuses to be.",
    "The door was always there. You just hadn't fallen through it yet.",
    "Kindness in a dark place shines twice as far.",
    "Some cages are called freedom by the ones outside them.",
    "A team is three people pretending they aren't scared alone.",
  ];
  var DR_LORE = [
    "Darkners are born of Lightners' things — a deck of cards, a keyboard, a door.",
    "In the Dark World, dollars are dark. The economy is honest about itself.",
    "TP replaces magic here: tension, spent on mercy as easily as violence.",
    "A Lightner's touch gives a Darkner purpose. Their absence gives them grief.",
    "Chapter 1's fork is simpler than it looks: fight, or don't.",
    "The prophecy names three heroes. It never says whose prophecy it is.",
    "Kris never chose the vessel. Neither did you.",
    "Some doors close at the end of the day. Some things stay behind them.",
  ];
  var _quoteIdx = null;
  function quoteOfDay() {
    if (_quoteIdx === null) {
      var d = new Date();
      _quoteIdx = (d.getFullYear() * 372 + d.getMonth() * 31 + d.getDate()) % APHORISMS.length;
    }
    var pool = ((state.truth || {}).game === "deltarune") ? DR_APHORISMS : APHORISMS;
    return pool[_quoteIdx % pool.length];
  }
  function renderQuote() {
    var el = $("quote-text"); if (el) el.textContent = "“" + quoteOfDay() + "”";
  }
  function nextQuote() {
    _quoteIdx = ((_quoteIdx === null ? 0 : _quoteIdx) + 1) % APHORISMS.length;
    renderQuote();
  }

  // Underground lore — our own compact framing of the world's rules, for flavour.
  var LORE = [
    "LOVE is an acronym — Level Of Violence — a measure of distance from mercy.",
    "EXP here stands for Execution Points: the more you kill, the more you gain.",
    "Monsters are made largely of magic; a human soul is, by comparison, staggeringly dense.",
    "SAVE points run on Determination — the will to bend the world by sheer refusal.",
    "Sparing an enemy ends a fight without ending a life.",
    "A monster's dust is said to settle on whoever loved them last.",
    "Seven human souls, it's said, are enough to bring a barrier down.",
    "Every reset, the world forgets. A rare few never do.",
    "The kindest path asks you to fight nothing — only to understand.",
    "A flower without a soul cannot feel love — only its absence.",
    "Determination lets a soul persist where a body would give out.",
    "Kill enough, and even the numbers start to feel like a choice.",
  ];
  var _loreIdx = null;
  function loreOfDay() {
    if (_loreIdx === null) {
      var d = new Date();
      _loreIdx = (d.getFullYear() * 181 + d.getMonth() * 29 + d.getDate() + 3) % LORE.length;
    }
    var pool = ((state.truth || {}).game === "deltarune") ? DR_LORE : LORE;
    return pool[_loreIdx % pool.length];
  }
  function renderLore() {
    var el = $("lore-text"); if (el) el.textContent = loreOfDay();
  }
  function nextLore() {
    _loreIdx = ((_loreIdx === null ? 0 : _loreIdx) + 1) % LORE.length;
    renderLore();
  }

  // The chat banner's epithet + "regards you" stance (re-run when affinities load).
  function renderHeroTitle() {
    if (!state.character) return;
    var el = $("chat-title"); if (!el) return;
    var a = (state.affinities || {})[state.character];
    var ep = ((state.truth && state.truth.game) === "deltarune" && EPITHETS_DR[state.character])
        || EPITHETS[state.character];
    el.innerHTML =
      (ep ? '<span class="hero-epithet">' + ep + "</span>" : "") +
      (a ? ' <span class="chip ' + (STANCE_CLASS[a.stance] || "free") + '" title="' + a.basis +
           '">regards you: ' + a.stance + "</span>" : "");
  }
  // A small epithet under each name in the chat banner (our own, in-world).
  var EPITHETS = {
    "Sans": "the judge", "Papyrus": "the great papyrus", "Flowey": "your best friend",
    "Toriel": "keeper of the ruins", "Undyne": "captain of the guard",
    "Alphys": "the royal scientist", "Asgore": "king of monsters",
    "Mettaton": "star of the underground", "Napstablook": "the quiet one",
    // Deltarune Ch1
    "Susie": "the bad guy (allegedly)", "Ralsei": "the lonely prince",
    "Lancer": "the littlest villain", "Noelle": "the girl from class",
    "King": "the throne's bitterness", "Rouxls Kaard": "duke of puzzles",
    "Jevil": "the free one", "Seam": "the seap... the shopkeeper",
  };
  // the Hometown faces wear different titles in the Dark World's story
  var EPITHETS_DR = {
    "Toriel": "your mom (drives you to school)", "Asgore": "the flower shop",
    "Alphys": "your teacher", "Sans": "new in town",
  };
  function showView(name) {
    if (state.view === "soundtest" && name !== "soundtest") leaveSoundTest();
    state.view = name;
    VIEWS.forEach(function (v) {
      var el = $("view-" + v); if (el) el.classList.toggle("active", v === name);
    });
    $$("[data-view]").forEach(function (b) {
      b.classList.toggle("sel", b.getAttribute("data-view") === name);
    });
    document.body.classList.toggle("on-chat", name === "chat");
    closeDrawers();
    updateModesBtn(name);
    var st = $("stage"); if (st) st.scrollTop = 0;
  }

  // the top-bar Modes control names where you are ("🎵 Sound Test ▾")
  function updateModesBtn(name) {
    var b = $("modes-btn"); if (!b) return;
    var m = null;
    for (var i = 0; i < MODES.length; i++) if (MODES[i].view === name) { m = MODES[i]; break; }
    b.innerHTML = (m ? m.label : "▦ Modes") + ' <span class="mcaret">▾</span>';
  }

  // Top-bar "Modes" menu — every mode, one click away, never buried under saves.
  var MODES = [
    { view: "chat", label: "💬 Chat" },
    { view: "council", label: "🗣 The Council" },
    { view: "timeline", label: "🕰 Timeline" },
    { view: "journal", label: "📖 Keepsake Journal" },
    { view: "constellation", label: "🌌 Across Your Saves", needsMulti: true },
    { view: "chronicle", label: "📜 The Chronicle" },
    { view: "judgment", label: "⚖ Judgment" },
    { view: "reports", label: "📋 Report Cards" },
    { view: "soundtest", label: "🎵 Sound Test" },
    { view: "guided", label: "🧭 Guided Mode" },
    { view: "commons", label: "📚 The Commons" },
    { view: "howitworks", label: "❓ How It Works" },
    { view: "workshop", label: "🛠 Prompt Workshop" },
    { view: "multivera", label: "🌌 MultiVera" },
    { view: "credits", label: "🏅 Credits" },
  ];
  var LITE_VIEWS = { chat: 1, judgment: 1, soundtest: 1, credits: 1, howitworks: 1, saves: 1 };
  function visibleModes() {
    if (!document.body.classList.contains("edition-lite")) return MODES;
    return MODES.filter(function (m) { return LITE_VIEWS[m.view]; });
  }
  // lite: the empty-state go-cards drop pro-only features; a pro pointer appears
  function renderLiteCards() {
    $$(".go-card").forEach(function (c) {
      if (!LITE_VIEWS[c.dataset.go]) c.style.display = "none";
    });
    if (state.proUrl && !document.getElementById("pro-pointer")) {  // re-render recreates .chat-empty-go, so the id check stays correct
      var host = document.querySelector(".chat-empty-go") || null;
      if (host) {
        var a = document.createElement("a");
        a.id = "pro-pointer"; a.className = "go-card pro-pointer";
        a.href = state.proUrl; a.target = "_blank"; a.rel = "noopener";
        a.innerHTML = "<b>🖥</b><span class='go-title'>Want the full experience?</span>" +
          "<span class='go-sub'>councils, reports, guided play, your own AI — the pro version</span>";
        host.appendChild(a);
      }
    }
  }
  function closeModesMenu() {
    var m = $("modes-menu"); if (m) m.parentNode.removeChild(m);
    var btn = $("modes-btn"); if (btn) btn.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", closeModesMenu, true);
  }
  function openModesMenu(anchor) {
    closeModesMenu();
    var m = document.createElement("div"); m.id = "modes-menu"; m.className = "modes-menu"; m.setAttribute("role", "menu");
    visibleModes().forEach(function (md) {
      if (md.needsMulti && !state.multiSave) return;
      var b = document.createElement("button");
      b.className = "modes-item" + (state.view === md.view ? " sel" : "");
      b.textContent = md.label;
      b.onclick = function (e) { e.stopPropagation(); closeModesMenu(); navTo(md.view); };
      m.appendChild(b);
    });
    document.body.appendChild(m);
    var r = anchor.getBoundingClientRect();
    m.style.top = (r.bottom + 8) + "px";
    var cx = r.left + r.width / 2 - m.offsetWidth / 2;   // centred under the control
    m.style.left = Math.max(6, Math.min(cx, window.innerWidth - m.offsetWidth - 6)) + "px";
    anchor.setAttribute("aria-expanded", "true");
    setTimeout(function () { document.addEventListener("click", closeModesMenu, true); }, 0);
  }

  // ── the power source: which brain (if any) Ember runs on ───────────────────
  var POWER_ICON = { none: "🕯", openrouter: "🔑", ollama: "🖥", anthropic: "☁" };
  var _powerSel = null;
  function refreshPowerChip() {
    api("/api/power").then(function (p) {
      state.power = p;
      state.edition = p.edition || "pro";
      state.proUrl = p.pro_url || "";
      if (state.edition === "lite") {
        document.body.classList.add("edition-lite");
        renderLiteCards();
      }
      var ico = $("power-ico"), word = $("power-word");
      if (ico) ico.textContent = POWER_ICON[p.source] || "⚡";
      if (word) word.textContent = "running on: " + p.source +
        (p.source === "openrouter" ? " (" + p.openrouter_model + ")" : "");
      // first run: no saved choice yet → offer the picker once
      var seen; try { seen = localStorage.getItem("uv_power_seen") === "1"; } catch (e) { seen = true; }
      if (!p.configured && !seen && state.edition !== "lite") openPowerModal();
    }).catch(function () {});
  }
  function openPowerModal() {
    try { localStorage.setItem("uv_power_seen", "1"); } catch (e) {}
    var p = state.power || {};
    _powerSel = p.source || "none";
    $$(".power-card").forEach(function (c) { c.classList.toggle("sel", c.dataset.source === _powerSel); });
    var sel = $("power-model");
    if (sel && !sel.options.length) {
      (p.suggestions || []).forEach(function (m) {
        var o = document.createElement("option"); o.value = m.id;
        o.textContent = m.label + " — " + m.note; sel.appendChild(o);
      });
      var custom = document.createElement("option"); custom.value = "__custom__";
      custom.textContent = "other (type a model id)…"; sel.appendChild(custom);
    }
    if (sel && p.openrouter_model) {
      var known = Array.prototype.some.call(sel.options, function (o) { return o.value === p.openrouter_model; });
      if (known) sel.value = p.openrouter_model;
      else { sel.value = "__custom__"; $("power-model-custom").value = p.openrouter_model; }
      $("power-model-custom").classList.toggle("hidden", sel.value !== "__custom__");
    }
    if ($("power-key")) $("power-key").placeholder = p.openrouter_key ? "saved (" + p.openrouter_key + ") — paste to replace" : "sk-or-…";
    $("power-or").classList.toggle("hidden", _powerSel !== "openrouter");
    $("power-status").textContent = "";
    $("power-modal").classList.remove("hidden");
    trapFocus($("power-modal"));
  }
  function closePowerModal() { $("power-modal").classList.add("hidden"); releaseFocus($("power-modal")); }
  function savePower() {
    var body = { source: _powerSel };
    if (_powerSel === "openrouter") {
      var k = $("power-key").value.trim(); if (k) body.openrouter_key = k;
      var m = $("power-model").value === "__custom__" ? $("power-model-custom").value.trim() : $("power-model").value;
      if (m) body.openrouter_model = m;
    }
    $("power-status").textContent = "saving…";
    api("/api/power", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function () {
        $("power-status").textContent = "testing…";
        return api("/api/power/test", { method: "POST" });
      })
      .then(function (t) {
        $("power-status").textContent = t.ok ? ("✓ working" + (t.model ? " · " + t.model : "") ) : ("✗ " + (t.error || "failed"));
        refreshPowerChip();
        if (t.ok) setTimeout(closePowerModal, 900);
      })
      .catch(function (e) { $("power-status").textContent = "✗ " + e.message; });
  }

  // Top-bar master volume + mute popover.
  function updateAudioBtn() {
    var b = $("audio-btn"); if (!b) return;
    b.textContent = (AudioBus.muted || AudioBus.volume === 0) ? "🔇" : (AudioBus.volume < 0.5 ? "🔉" : "🔊");
    b.setAttribute("aria-label", AudioBus.muted ? "Muted" : "Volume");
  }
  function closeAudioMenu() {
    var m = $("audio-menu"); if (m) m.parentNode.removeChild(m);
    var btn = $("audio-btn"); if (btn) btn.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", closeAudioMenu, false);
  }
  function openAudioMenu(anchor) {
    closeAudioMenu();
    var m = document.createElement("div"); m.id = "audio-menu"; m.className = "audio-menu";
    m.innerHTML =
      '<button class="audio-mute" id="audio-mute" type="button"></button>' +
      '<label class="audio-slider">Volume <input type="range" id="audio-vol" min="0" max="100" /></label>';
    m.addEventListener("click", function (e) { e.stopPropagation(); });   // don't close on inner clicks
    document.body.appendChild(m);
    var r = anchor.getBoundingClientRect();
    m.style.top = (r.bottom + 6) + "px";
    m.style.right = Math.max(6, window.innerWidth - r.right) + "px";
    anchor.setAttribute("aria-expanded", "true");
    function refresh() {
      var mu = $("audio-mute"), v = $("audio-vol"); if (!mu || !v) return;
      mu.textContent = AudioBus.muted ? "🔇 Unmute all" : "🔊 Mute all";
      v.value = Math.round(AudioBus.volume * 100); v.disabled = AudioBus.muted;
    }
    refresh();
    $("audio-mute").onclick = function () { AudioBus.setMuted(!AudioBus.muted); updateAudioBtn(); refresh(); };
    $("audio-vol").oninput = function () { AudioBus.setVolume(this.value / 100); updateAudioBtn(); };
    setTimeout(function () { document.addEventListener("click", closeAudioMenu, false); }, 0);
  }

  // First-time explainers — a one-shot modal the first time you open each feature.
  var FEATURES = {
    council: { icon: "🗣", title: "The Council",
      body: "The whole Underground reacts to your run at once — every character's stance and in-voice line, side by side. The contrast is the story: who grieves, who gloats. Tap a face to hear them, or “talk” to jump into a chat." },
    timeline: { icon: "🕰", title: "The Timeline",
      body: "Every reading of your save, in order, tinted by the route each time. Where the numbers went backward, a ↩ marks a reset — so you can see the whole shape of your journey, changes and all." },
    journal: { icon: "📖", title: "The Keepsake Journal",
      body: "A book the characters fill in their own voice, grounded in what your save actually shows. Ask someone to write you a page, keep reports here, and carry it out as markdown." },
    constellation: { icon: "🌌", title: "Across Your Saves",
      body: "The whole shape of you across every save you've shown — your moral range, and where your paths diverge. It appears once you've read more than one save." },
    chronicle: { icon: "📜", title: "The Chronicle",
      body: "The full written record of your journey so far, assembled from your save's truth — readable here and exportable as markdown to keep." },
    judgment: { icon: "⚖", title: "Judgment",
      body: "You'll be judged for your every action. The verdict is grounded in exactly what your save shows — nothing invented — and you can ask a character to say it to your face." },
    reports: { icon: "📋", title: "Report Cards",
      body: "Each character files an after-action report on your run: how you did, what you might've done differently, and what THEY would have done. Keep a history, save favourites to your Journal, or have them emailed to you." },
    guided: { icon: "🧭", title: "Guided Mode",
      body: "Play the game beside Ember. Point it at your save folder (read-only — it never touches the game itself), pick a party of companions, and every time you save in-game the run's beats land here: what changed, where you are, and the party's reactions. Ask them anything as you go." },
    multivera: { icon: "🌌", title: "The MultiVera Project",
      body: "The idea behind this app, introduced properly: a Vera is a companion for a game you love, grounded in your actual save. Meet the family — Ember, FFT PSX Vera, and the tiny MGS codec sketch — then take the recipe and build one for your game." },
    workshop: { icon: "🛠", title: "The Prompt Workshop",
      body: "Every AI feature here runs on prompts you can read — and this page shows the real ones, pulled live from the code: the anatomy of a grounded system prompt, each feature's exact instruction, the Suno prompts behind the whole soundtrack, and the knobs to bend when you build your own. Tap any dark block to copy it." },
    soundtest: { icon: "🎵", title: "Sound Test",
      body: "Play the whole soundtrack — the main theme, the three route beds, and every character's theme. Switch to Jam mode to layer any characters together (all, some, or none) and let them collide. A visualizer reacts to whatever's playing." },
  };
  // ── modal focus management (accessibility): trap Tab inside, restore on close ─
  var _modalReturnFocus = null;
  function focusables(root) {
    return Array.prototype.slice.call(root.querySelectorAll(
      "button:not([disabled]), a[href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex='-1'])"
    )).filter(function (el) { return el.offsetParent !== null; });
  }
  function trapFocus(scrim) {
    _modalReturnFocus = document.activeElement;
    var f = focusables(scrim); if (f.length) f[0].focus();
    scrim._trap = function (e) {
      if (e.key !== "Tab") return;
      var els = focusables(scrim); if (!els.length) return;
      var first = els[0], last = els[els.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    scrim.addEventListener("keydown", scrim._trap);
  }
  function releaseFocus(scrim) {
    if (scrim && scrim._trap) { scrim.removeEventListener("keydown", scrim._trap); scrim._trap = null; }
    if (_modalReturnFocus && _modalReturnFocus.focus) { try { _modalReturnFocus.focus(); } catch (e) {} }
    _modalReturnFocus = null;
  }

  function maybeIntro(key) {
    var f = FEATURES[key]; if (!f) return;
    var seen; try { seen = localStorage.getItem("uv_seen_" + key) === "1"; } catch (e) { seen = false; }
    if (seen) return;
    try { localStorage.setItem("uv_seen_" + key, "1"); } catch (e) {}
    $("feature-modal-icon").textContent = f.icon;
    $("feature-modal-title").textContent = f.title;
    $("feature-modal-body").textContent = f.body;
    $("feature-modal").classList.remove("hidden");
    trapFocus($("feature-modal"));
  }
  function closeFeatureModal() { $("feature-modal").classList.add("hidden"); releaseFocus($("feature-modal")); }

  // nav button → fetch+render the feature, then reveal its view (or just switch)
  var NEEDS_SAVE = { council: 1, timeline: 1, journal: 1, constellation: 1, chronicle: 1, judgment: 1, reports: 1 };
  function navTo(name) {
    // these modes need a save; without one, guide the player to read one first
    if (NEEDS_SAVE[name] && !state.projectId) {
      miniToast("Read a save first to open " + name.charAt(0).toUpperCase() + name.slice(1) + ".");
      return showView("saves");
    }
    maybeIntro(name);   // one-shot explainer the first time (no-op for chat/saves)
    switch (name) {
      case "council": return showCouncil();
      case "timeline": return showTimeline();
      case "journal": return showJournal();
      case "constellation": return showConstellation();
      case "chronicle": return showChronicle();
      case "judgment": return showJudgment();
      case "reports": return showReports();
      case "soundtest": return showSoundTest();
      case "guided": return showGuided();
      case "commons": return showCommons();
      case "howitworks": return showView("howitworks");
      case "workshop": return showWorkshop();
      case "multivera": return showView("multivera");
      case "credits": return showView("credits");
      case "saves": return showView("saves");
      default: return showView("chat");
    }
  }

  // mobile drawers (rails slide in); no-op visuals on desktop where rails persist
  function openDrawer(side) {
    document.body.classList.remove("drawer-left", "drawer-right");
    document.body.classList.add("drawer-" + side);
  }
  function closeDrawers() { document.body.classList.remove("drawer-left", "drawer-right"); }

  function api(path, opts) {
    return fetch(path, opts).then(function (r) {
      // Read text first: a server error body may be plain text (e.g. "Internal
      // Server Error"), not JSON — parsing it blindly would throw a cryptic
      // "Unexpected token" instead of a clean message.
      return r.text().then(function (raw) {
        var body = null;
        try { body = raw ? JSON.parse(raw) : null; } catch (e) { body = null; }
        if (!r.ok) {
          throw new Error((body && body.detail) ? body.detail : ("HTTP " + r.status));
        }
        if (body === null) throw new Error("HTTP " + r.status + " (non-JSON response)");
        return body;
      });
    });
  }

  // ── upload / refresh ──────────────────────────────────────────────────────
  function saveFormData() {
    var fd = new FormData();
    var f0 = $("file0-input").files[0];
    var ini = $("ini-input").files[0];
    // keep the real filename — the backend detects Deltarune slots (filech1_0…) by name
    if (f0) fd.append("file0", f0, f0.name || "file0");
    if (ini) fd.append("undertale_ini", ini, "undertale.ini");
    return (f0 || ini) ? fd : null;
  }

  function uploadSave() {
    var fd = saveFormData();
    if (!fd) { $("upload-status").textContent = "Choose file0 and/or undertale.ini first."; return; }
    $("upload-status").textContent = "reading…";
    api("/api/upload", { method: "POST", body: fd })
      .then(function (res) {
        state.projectId = res.project_id;
        state.character = null;
        state.history = {};
        $("refresh-btn").classList.remove("hidden");
        $("upload-status").textContent = "Save read. Project #" + res.project_id + ".";
        renderTruth(res.save_truth, null, "");
        loadRoster();
        loadShelf();
        renderTranscript();
        showView("chat");
      })
      .catch(function (e) { $("upload-status").textContent = "Error: " + e.message; });
  }

  function refreshSave() {
    if (!state.projectId) return;
    var fd = saveFormData();
    if (!fd) { $("upload-status").textContent = "Choose the later save's file0/undertale.ini."; return; }
    $("upload-status").textContent = "reading the return visit…";
    api("/api/projects/" + state.projectId + "/refresh-save", { method: "POST", body: fd })
      .then(function (res) {
        $("upload-status").textContent = "Return visit recorded (visit #" + res.visit + ").";
        renderTruth(res.save_truth, res.visit, res.remembrance || "");
        loadAffinities();   // the cast's regard can change with the new reading
        if (state.view === "journal") loadJournal();
      })
      .catch(function (e) { $("upload-status").textContent = "Error: " + e.message; });
  }

  // ── SaveTruth summary + route-aware music ────────────────────────────────
  function renderTruth(truth, visit, remembrance) {
    state.truth = truth;   // kept for save-aware conversation starters
    var play = truth.play_state || {};
    var route = (truth.route || {}).route || "undetermined";
    var conf = (truth.route || {}).confidence || "unknown";
    var kills = (truth.kills || {}).total;

    var darkWorld = truth.game === "deltarune";
    document.body.classList.toggle("world-dark", darkWorld);   // the console falls into the Dark World

    function fmt(v) { return (v === null || v === undefined || v === "") ? "—" : v; }
    var drParty = ((truth.deltarune || {}).party || []).join(" · ");
    $("truth-facts").innerHTML = darkWorld
      ? row("Name", fmt(play.name)) +
        row("Party", drParty || "—") +
        row("Dark $", fmt(play.gold)) +
        row("Chapter", fmt(truth.chapter)) +
        ((truth.deltarune || {}).jevil_defeated ? row("Secret", "the jester, freed & bested") : "")
      : row("Name", fmt(play.name)) +
        row("LOVE (LV)", fmt(play.love)) +
        row("Kills", kills === null || kills === undefined ? "—" : kills) +
        row("Room", fmt(play.room_name));

    var badge = $("route-badge");
    badge.className = "route-badge " + (darkWorld ? "dark-world" : route.toLowerCase());
    badge.innerHTML = '<span class="soul-sigil ' + (route === "Genocide" ? "determined" : "") +
      '" style="width:14px;height:14px;"></span> ' +
      (darkWorld ? "path: " + route + " (" + conf + ")" : "route: " + route + " (" + conf + ")");

    $("visit-label").textContent = visit ? ("· visit #" + visit) : "";
    var rbox = $("remembrance-box");
    if (remembrance) { rbox.textContent = remembrance; rbox.classList.remove("hidden"); }
    else { rbox.classList.add("hidden"); }

    // reflect the current save in the top-bar pill
    var pill = $("save-pill");
    if (pill) pill.textContent = (fmt(play.name) === "—" ? "Save" : play.name) + " · " +
      (darkWorld ? "Dark World" : route) + " ▾";

    // world/route-aware music: the Dark World brings its own bed (silent-safe fallback).
    if (window.MusicLayer && $("music-toggle").checked) {
      if (darkWorld) window.MusicLayer.setWorld("dark"); else window.MusicLayer.setRoute(route);
    }
    // route-reactive backdrop: tint (always) + generated scene art (when present).
    if (window.SceneLayer) window.SceneLayer.setRoute(route);
    // tint the header sigil red on the Genocide beat.
    $("header-sigil").className = "soul-sigil" + (route === "Genocide" ? " determined" : "");
    // Route atmosphere: the whole console takes on a faint aura the colour of the
    // path (warm for Pacifist, cool for Neutral, blood-red for Genocide). Genocide
    // also destabilises the dialogue (route-genocide) + a one-shot flash on entry.
    setBodyRoute(route);
    if (route === "Genocide" && state.lastRoute !== "Genocide") flashGenocide();
    state.lastRoute = route;
    // the flavour cards follow the world (Underground lore vs Dark World lore)
    renderQuote(); renderLore();
    // if "let them reach out" is on, resume the proactive timer now a save is live
    startReachTimer(false);
    // New Game+: does anything here know you from another save you've shown?
    loadRecognition();
  }
  function row(k, v) { return '<div class="k">' + k + "</div><div>" + v + "</div>"; }

  // set the single active route-* class on <body> (drives the aura + genocide feel)
  function setBodyRoute(route) {
    var b = document.body, r = (route || "undetermined").toLowerCase();
    ["pacifist", "neutral", "genocide", "undetermined"].forEach(function (x) {
      b.classList.toggle("route-" + x, x === r);
    });
  }
  // one-shot blood-red flash on entering Genocide (CSS gates it under motion prefs)
  function flashGenocide() {
    var el = $("screen-flash"); if (!el) return;
    el.classList.remove("fire");
    void el.offsetWidth;            // force reflow so the animation restarts
    el.classList.add("fire");
  }

  // New Game+ / cross-save recognition: a quiet beat when this save has siblings.
  // Honours the Options "Save/reset talk" dial — off means stay in the fiction.
  function loadRecognition() {
    var box = $("recognition-box");
    if (!box) return;
    if (!state.projectId) { box.classList.add("hidden"); return; }
    var metaOff = (((state.settings || {}).options || {}).meta === "off");
    if (metaOff) { box.classList.add("hidden"); return; }
    api("/api/projects/" + state.projectId + "/recognition").then(function (res) {
      if (!res || !res.present) { box.classList.add("hidden"); return; }
      var n = res.count || 0;
      // The Other's Echo: a darker prior run behind this gentler face — dread, not nostalgia.
      if (res.echo_present && res.darkest) {
        var d = res.darkest;
        var dl = (d.route || "a darker run") +
          (typeof d.love === "number" ? " · LOVE " + d.love : "") +
          (typeof d.total_kills === "number" ? " · " + d.total_kills + " kills" : "");
        box.className = "recognition echo";  // uneasy styling
        box.innerHTML =
          '<span class="rec-mark">🩸</span> <strong>It remembers what you did on another save.</strong> ' +
          '<span class="muted">' + dl + "</span> — on a different file, the same hand. " +
          "<em>The clean face doesn't fool Flowey, or Sans.</em>";
        box.classList.remove("hidden");
        return;
      }
      // Across Two Worlds: the player has shown a save from the OTHER game
      if (res.two_worlds_present && res.other_world) {
        var ow = res.other_world;
        var owWorld = (res.current_game === "deltarune") ? "the Underground" : "the Dark World";
        var owLine = (ow.name || "a nameless run") + (ow.route ? " · " + ow.route : "") +
          (typeof ow.love === "number" ? " · LOVE " + ow.love : "");
        box.className = "recognition two-worlds";
        box.innerHTML =
          '<span class="rec-mark">🜁</span> <strong>A face from another world.</strong> ' +
          "You've also walked <em>" + owWorld + "</em> — " +
          '<span class="muted">' + owLine + "</span>. " +
          "<em>Ask Toriel, or Sans. Something in them stirs.</em>";
        box.classList.remove("hidden");
        return;
      }
      var faces = (res.priors || []).slice(0, 3).map(function (p) {
        var nm = p.name || "a nameless run";
        return nm + (p.route ? (" · " + p.route) : "");
      }).join("  ·  ");
      box.className = "recognition";  // reset to the warm beat
      box.innerHTML =
        '<span class="rec-mark">🌼</span> <strong>You\'ve been here before.</strong> ' +
        n + " other save" + (n === 1 ? "" : "s") + " shown — " +
        '<span class="muted">' + faces + "</span>. " +
        "<em>Flowey never forgets a run. Ask him.</em>";
      box.classList.remove("hidden");
    }).catch(function () { box.classList.add("hidden"); });
  }

  // ── save shelf (switch between read saves) ───────────────────────────────
  // A compact "read on <date>" label for a save card (empty if unknown).
  function fmtSaveDate(iso) {
    if (!iso) return "";
    try {
      var d = new Date(iso);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch (e) { return ""; }
  }

  // ── "START HERE" onboarding pointer: until a first save exists, glow the
  // read-a-save entry point and float a bouncing tag beside it ──────────────
  function updateStartHere(hasSaves) {
    var tag = document.getElementById("start-here-tag");
    var rail = $("add-save-btn");
    var tab = document.querySelector('[data-nav="save"]');
    if (hasSaves) {
      if (tag) tag.remove();
      if (rail) rail.classList.remove("start-glow");
      if (tab) tab.classList.remove("start-glow");
      return;
    }
    if (rail) rail.classList.add("start-glow");
    if (tab) tab.classList.add("start-glow");
    if (!tag) {
      tag = document.createElement("button");
      tag.id = "start-here-tag"; tag.type = "button";
      tag.setAttribute("aria-label", "Start here: read your save file");
      document.body.appendChild(tag);
      tag.onclick = function () {
        var mobile = window.matchMedia("(max-width: 860px)").matches;
        var t = mobile ? document.querySelector('[data-nav="save"]') : $("add-save-btn");
        if (t) t.click();
      };
    }
    positionStartHere();
  }
  function positionStartHere() {
    var tag = document.getElementById("start-here-tag"); if (!tag) return;
    var mobile = window.matchMedia("(max-width: 860px)").matches;
    if (mobile) {
      var tab = document.querySelector('[data-nav="save"]'); if (!tab) return;
      var r = tab.getBoundingClientRect();
      tag.className = "start-here-tag point-down";
      tag.innerHTML = "★ START HERE <span class='sh-arrow'>⬇</span>";
      tag.style.left = Math.min(r.left + r.width / 2, window.innerWidth - 78) + "px";
      tag.style.top = (r.top - 44) + "px";
    } else {
      var rail = $("add-save-btn"); if (!rail) return;
      var r2 = rail.getBoundingClientRect();
      tag.className = "start-here-tag point-left";
      tag.innerHTML = "<span class='sh-arrow'>⬅</span> START HERE · read your save";
      tag.style.left = (r2.right + 12) + "px";
      tag.style.top = (r2.top + r2.height / 2) + "px";
    }
  }
  window.addEventListener("resize", positionStartHere);
  document.addEventListener("click", function (e) {
    var cta = e.target.closest && e.target.closest("[data-go-saves]");
    if (cta) navTo("saves");
  });

  function loadShelf() {
    api("/api/projects").then(function (res) {
      var el = $("shelf"); el.innerHTML = "";
      (res.projects || []).forEach(function (p) {
        var route = p.route || "undetermined";
        var card = document.createElement("div");
        card.className = "save-card" + (p.project_id === state.projectId ? " selected" : "");
        card.dataset.pid = p.project_id;
        var gen = route === "Genocide";
        var lv = (p.love === null || p.love === undefined) ? "—" : p.love;
        var when = fmtSaveDate(p.created_at);
        var dr = p.game === "deltarune";   // a Dark World save on the same shelf
        card.innerHTML =
          '<span class="save-sigil soul-sigil' + (gen ? " determined" : "") + (dr ? " dark-world" : "") + '" aria-hidden="true"></span>' +
          '<span class="save-body">' +
            '<span class="save-head">' +
              '<span class="save-name">' + escHtml(p.name || ("Save #" + p.project_id)) + "</span>" +
              (dr ? '<span class="route-badge dark-world">DR·CH' + (p.chapter || "?") + "</span>"
                  : '<span class="route-badge ' + route.toLowerCase() + '">' + route + "</span>") +
            "</span>" +
            '<span class="save-meta">' + (dr ? "Dark World" : "LV " + lv) + (when ? " · " + when : "") + "</span>" +
          "</span>";
        card.onclick = function () { loadProject(p.project_id); };
        el.appendChild(card);
      });
      if (!res.projects || !res.projects.length) {
        el.innerHTML = '<p class="muted" style="font-size:.78rem;">No saves yet.</p>';
      }
      updateStartHere(!!(res.projects && res.projects.length));
      // "Across Your Saves" only means something once there's more than one save.
      state.multiSave = (res.projects || []).length >= 2;   // gates "Across Your Saves"
      var navC = $("nav-constellation");
      if (navC) navC.classList.toggle("hidden", !state.multiSave);
    });
  }

  // The Constellation of You — the whole shape across every save shown.
  function showConstellation() {
    api("/api/constellation").then(function (res) {
      var el = $("constellation-content");
      if (!res || !res.present) {
        el.innerHTML = '<p class="muted">Only one save shown so far — read another to see the shape of you.</p>';
      } else {
        var a = res.aggregate || {};
        var routes = a.routes || {};
        var chips = Object.keys(routes).map(function (r) {
          return '<span class="route-badge ' + r.toLowerCase() + '" style="font-size:0.74rem;">' +
            r + " ×" + routes[r] + "</span>";
        }).join(" ");
        var rangeLine = "";
        if (a.kindest && a.darkest && a.kindest.route !== a.darkest.route) {
          rangeLine = '<div class="con-range"><span class="muted">moral range:</span> ' +
            (a.kindest.route || "—") + "  →  " + (a.darkest.route || "—") + "</div>";
        }
        var divLine = res.divergence
          ? '<div class="con-divergence">“' + res.divergence + '”</div>' : "";
        el.innerHTML =
          '<div class="con-count">' + res.count + " saves shown</div>" +
          '<div class="con-routes">' + chips + "</div>" +
          rangeLine +
          '<div class="con-verdict' + (a.full_spectrum ? " spectrum" : "") + '">' +
          '<span class="con-mark">🌌</span> ' + (res.verdict || "") + "</div>" +
          divLine;
      }
      populateDivergence();
      showView("constellation");
    });
  }
  // ── the star map: every save a star; the thread of you connects them ───────
  var _conStars = [], _conRAF = null;
  var ROUTE_STAR = {
    Pacifist: { color: "232,162,76", band: 0.24 },
    Neutral: { color: "110,140,178", band: 0.50 },
    Genocide: { color: "209,47,62", band: 0.76 },
    undetermined: { color: "168,155,130", band: 0.50 },
    darkworld: { color: "180,139,242", band: 0.38 },
  };
  function conJitter(seed) {   // deterministic organic offset per save
    var x = Math.sin(seed * 127.1) * 43758.5453;
    return (x - Math.floor(x)) - 0.5;
  }
  function buildConstellationMap(projects) {
    var cv = $("con-map"); if (!cv) return;
    var wrap = cv.parentNode, dpr = window.devicePixelRatio || 1;
    var W = wrap.clientWidth || 700, H = 240;
    cv.width = W * dpr; cv.height = H * dpr;
    cv.style.width = W + "px"; cv.style.height = H + "px";
    var list = (projects || []).slice().sort(function (a, b) { return a.project_id - b.project_id; });
    _conStars = list.map(function (p, i) {
      var kind = p.game === "deltarune" ? "darkworld" : (p.route || "undetermined");
      var spec = ROUTE_STAR[kind] || ROUTE_STAR.undetermined;
      var pad = 34;
      var x = list.length === 1 ? W / 2 : pad + (W - pad * 2) * (i / (list.length - 1));
      var y = H * spec.band + conJitter(p.project_id) * H * 0.22;
      y = Math.max(22, Math.min(H - 22, y));
      var r = 3 + Math.min(8, ((p.love || 1) - 1) * 0.42);
      if (p.game === "deltarune") r = 4.2;
      return { x: x, y: y, r: r, color: spec.color, p: p, tw: (p.project_id % 7) / 7 };
    });
    if (_conRAF) cancelAnimationFrame(_conRAF);
    var motion = !(state.settings && state.settings.hud && state.settings.hud.motion === false) &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    (function draw(ts) {
      if (!document.querySelector("#view-constellation.active")) { _conRAF = null; return; }
      var g = cv.getContext("2d");
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.clearRect(0, 0, W, H);
      // the thread of you: chronological line, faint
      g.beginPath();
      _conStars.forEach(function (s, i) { i ? g.lineTo(s.x, s.y) : g.moveTo(s.x, s.y); });
      g.strokeStyle = "rgba(184,147,63,.22)"; g.lineWidth = 1; g.stroke();
      _conStars.forEach(function (s) {
        var a = motion ? 0.72 + 0.28 * Math.sin((ts || 0) / 900 + s.tw * 6.28) : 0.85;
        var grad = g.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 3.2);
        grad.addColorStop(0, "rgba(" + s.color + "," + a + ")");
        grad.addColorStop(0.45, "rgba(" + s.color + "," + (a * 0.32) + ")");
        grad.addColorStop(1, "rgba(" + s.color + ",0)");
        g.fillStyle = grad;
        g.beginPath(); g.arc(s.x, s.y, s.r * 3.2, 0, 6.283); g.fill();
        g.fillStyle = "rgba(255,255,255," + (0.55 + a * 0.35) + ")";
        g.beginPath(); g.arc(s.x, s.y, Math.max(1.4, s.r * 0.42), 0, 6.283); g.fill();
      });
      if (motion) _conRAF = requestAnimationFrame(draw); else _conRAF = null;
    })(0);
    // hover + click
    function starAt(ev) {
      var r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top, hit = null;
      _conStars.forEach(function (s) {
        var d = Math.hypot(s.x - mx, s.y - my);
        if (d < Math.max(10, s.r * 2.4) && (!hit || d < hit.d)) hit = { s: s, d: d };
      });
      return hit && hit.s;
    }
    cv.onmousemove = function (ev) {
      var s = starAt(ev), tip = $("con-tip");
      cv.style.cursor = s ? "pointer" : "default";
      if (!s) { tip.classList.add("hidden"); return; }
      var p = s.p;
      tip.textContent = (p.name || "Save #" + p.project_id) + " · " +
        (p.game === "deltarune" ? "Dark World" : (p.route || "?")) +
        (p.love != null ? " · LV " + p.love : "");
      tip.style.left = (s.x + 12) + "px"; tip.style.top = (s.y - 10) + "px";
      tip.classList.remove("hidden");
    };
    cv.onmouseleave = function () { $("con-tip").classList.add("hidden"); };
    cv.onclick = function (ev) { var s = starAt(ev); if (s) loadProject(s.p.project_id); };
  }

  var _conResizeT = null;
  window.addEventListener("resize", function () {
    if (!document.querySelector("#view-constellation.active")) return;
    clearTimeout(_conResizeT);
    _conResizeT = setTimeout(function () {
      api("/api/projects").then(function (res) { buildConstellationMap(res.projects || []); }).catch(function () {});
    }, 250);
  });

  function populateDivergence() {
    var chSel = $("div-char");
    if (chSel && chSel.options.length === 0) {
      (state.characters || []).forEach(function (c) {
        var o = document.createElement("option"); o.value = c.name; o.textContent = c.name; chSel.appendChild(o);
      });
    }
    api("/api/projects").then(function (res) {
      var projs = res.projects || [];
      buildConstellationMap(projs);   // the star map shares this fetch
      [$("div-a"), $("div-b")].forEach(function (sel, idx) {
        if (!sel) return;
        var keep = sel.value;
        sel.innerHTML = "";
        projs.forEach(function (p) {
          var o = document.createElement("option"); o.value = p.project_id;
          o.textContent = (p.name || ("Save #" + p.project_id)) + " · " +
            (p.game === "deltarune" ? "Dark World" : (p.route || "?"));
          sel.appendChild(o);
        });
        if (keep) sel.value = keep;
        else if (projs.length > 1) sel.selectedIndex = idx === 1 ? 1 : 0;   // default to two different saves
      });
    });
  }
  function askDivergence() {
    var a = $("div-a").value, b = $("div-b").value, ch = $("div-char").value;
    if (!a || !b || !ch) return;
    var btn = $("div-ask"), t = btn.textContent; btn.disabled = true; btn.textContent = "…";
    $("div-output").textContent = ch + " considers the fork…";
    api("/api/divergence", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_a: +a, project_b: +b, character: ch }),
    }).then(function (res) {
      var out = $("div-output");
      out.innerHTML = '<div class="div-head">' + avatarMarkup(res.author, "bubble-avatar") +
        '<span class="div-author">' + escHtml(res.author) + "</span>" +
        '<span class="div-fork muted">' + escHtml((res.a.route || "?") + " ↔ " + (res.b.route || "?")) + "</span></div>" +
        '<div class="div-text"></div>';
      out.querySelector(".div-text").textContent = res.text;
    }).catch(function (e) { $("div-output").textContent = "Couldn't reach the fork: " + e.message; })
      .then(function () { btn.disabled = false; btn.textContent = t; });
  }

  function loadProject(id) {
    api("/api/projects/" + id + "/save-truth").then(function (res) {
      state.projectId = id;
      state.history = {};
      state.character = null;
      $("refresh-btn").classList.remove("hidden");
      renderTruth(res.save_truth, null, "");
      loadRoster();
      loadShelf();           // refresh the shelf's selected highlight
      renderTranscript();    // chat shows the "pick someone" placeholder
      showView("chat");
    });
  }

  // ── roster ────────────────────────────────────────────────────────────────
  // stance → CSS class for the affinity chip colour
  var STANCE_CLASS = { warm: "ok", wary: "free", grieving: "warn", hostile: "warn", unreadable: "free" };

  // ── portraits (bring-your-own; click a card's photo to change it) ─────────
  var portraitBust = 0;   // bumped on change so the browser re-fetches the image
  function charByName(name) {
    var l = (state.characters || []).concat(state.drCharacters || []);
    for (var i = 0; i < l.length; i++) if (l[i].name === name) return l[i];
    return null;
  }
  function _bust(u) {
    if (!u) return "";
    return portraitBust ? (u + (u.indexOf("?") < 0 ? "?" : "&") + "v=" + portraitBust) : u;
  }
  function portraitUrl(name) { var c = charByName(name); return _bust(c && c.avatar_url); }
  function emblemRaster(name) { var c = charByName(name); return _bust(c && c.emblem_url); }
  function emblemSvg(name) { return (window.UV_EMBLEMS && window.UV_EMBLEMS[name]) || ""; }
  function slug(name) { return (name || "").toLowerCase().replace(/[^a-z0-9]+/g, "-"); }

  // The avatar shown for a character, in priority order:
  //   user-supplied photo  >  designed raster emblem  >  inline SVG emblem  >  blank crest.
  function avatarMarkup(name, baseCls, id) {
    var idAttr = id ? ' id="' + id + '"' : "";
    var p = portraitUrl(name);
    if (p) return '<img' + idAttr + ' class="' + baseCls + '" src="' + p + '" alt="' + name + '" />';
    var e = emblemRaster(name);
    if (e) return '<img' + idAttr + ' class="' + baseCls + ' emblem-img" src="' + e + '" alt="' + name + '" />';
    var svg = emblemSvg(name);
    if (svg) return '<div' + idAttr + ' class="' + baseCls + ' emblem">' + svg + "</div>";
    return '<div' + idAttr + ' class="' + baseCls + ' empty"></div>';
  }
  function hasAnyImage(name) { var c = charByName(name); return !!(c && (c.avatar_url || c.emblem_url)); }

  // ── Undertale-feel: a short text "blip" per character as dialogue types ────
  // Each character has its own synthesized voice (see voices.js). This wrapper
  // just honours the Options "Text blip" toggle; the synthesis lives in VoiceLayer.
  function blip(name) {
    if (!(state.settings && state.settings.hud && state.settings.hud.blip)) return;
    if (window.VoiceLayer) window.VoiceLayer.blip(name);
  }
  function blipEvery(name) {
    return (window.VoiceLayer && window.VoiceLayer.blipEvery(name)) || 2;
  }
  function portraitTag(name) { return avatarMarkup(name, "relic-portrait"); }

  function loadRoster() {
    // the roster follows the active save's world: Deltarune saves seat the Ch1 cast
    var game = (state.truth && state.truth.game) === "deltarune" ? "deltarune" : "";
    api("/api/characters" + (game ? "?game=" + game : "")).then(function (res) {
      state.characters = res.characters;
      renderRoster();
      loadAffinities();   // decorate cards with how each regards you (no-op without a save)
      if (!state.character) renderTranscript();   // fill the welcome's cast row once loaded
    });
  }

  // Render roster + speaker strip from cached state.characters (no refetch), so a
  // portrait change repaints instantly.
  function renderRoster() {
    var el = $("roster"); if (el) el.innerHTML = "";
    var strip = $("speaker-strip"); if (strip) strip.innerHTML = "";
    (state.characters || []).forEach(function (c) {
      // left-rail roster card — the portrait opens a photo-options menu (⋯)
      var card = document.createElement("div");
      card.className = "char-card";
      card.dataset.name = c.name;
      card.classList.toggle("selected", c.name === state.character);
      card.innerHTML =
        '<div class="portrait-wrap" title="Photo options">' + portraitTag(c.name) +
          '<span class="pbadge" aria-hidden="true">⋯</span></div>' +
        '<div class="name">' + c.name + "</div>" +
        '<div class="affinity" data-for="' + c.name + '"></div>';
      card.onclick = function () { selectCharacter(c); };
      var wrap = card.querySelector(".portrait-wrap");
      wrap.onclick = function (e) { e.stopPropagation(); openPortraitMenu(c.name, wrap); };
      if (el) el.appendChild(card);
      // mobile speaker strip face (display only)
      if (strip) {
        var face = document.createElement("div");
        face.className = "face"; face.dataset.name = c.name;
        face.classList.toggle("selected", c.name === state.character);
        face.innerHTML = portraitTag(c.name) + "<div>" + c.name + "</div>";
        face.onclick = function () { selectCharacter(c); };
        strip.appendChild(face);
      }
    });
  }

  // ── change / clear a character's portrait (your own image; downscaled) ────
  function downscaleToPng(file, max, cb) {
    var img = new Image();
    img.onload = function () {
      var s = Math.min(1, max / Math.max(img.width, img.height));
      var w = Math.max(1, Math.round(img.width * s)), h = Math.max(1, Math.round(img.height * s));
      var cv = document.createElement("canvas"); cv.width = w; cv.height = h;
      cv.getContext("2d").drawImage(img, 0, 0, w, h);
      cv.toBlob(function (blob) { cb(blob); }, "image/png");
      URL.revokeObjectURL(img.src);
    };
    img.onerror = function () { alert("That file isn't a readable image."); };
    img.src = URL.createObjectURL(file);
  }
  function applyPortrait(name, avatarUrl) {
    var c = charByName(name); if (c) c.avatar_url = avatarUrl;
    portraitBust = (portraitBust || 0) + 1;
    renderRoster(); renderAffinities();
    if (state.character) renderTranscript();
  }
  function changePortrait(name) {
    var inp = document.createElement("input");
    inp.type = "file"; inp.accept = "image/*";
    inp.onchange = function () {
      var f = inp.files && inp.files[0]; if (!f) return;
      downscaleToPng(f, 192, function (blob) {
        var fd = new FormData(); fd.append("image", blob, name.toLowerCase() + ".png");
        api("/api/characters/" + name.toLowerCase() + "/portrait", { method: "POST", body: fd })
          .then(function (res) { applyPortrait(name, res.avatar_url); })
          .catch(function (e) { alert("Couldn't set image: " + e.message); });
      });
    };
    inp.click();
  }
  function resetPortrait(name) {
    api("/api/characters/" + name.toLowerCase() + "/portrait", { method: "DELETE" })
      .then(function (res) { applyPortrait(name, res.avatar_url); })
      .catch(function () {});
  }

  // a small options menu on the portrait: View larger · Change · Remove
  function closePortraitMenu() {
    var m = $("portrait-menu"); if (m) m.parentNode.removeChild(m);
    document.removeEventListener("click", closePortraitMenu, true);
  }
  function openPortraitMenu(name, anchor) {
    closePortraitMenu();
    var c = charByName(name);
    var hasPhoto = !!(c && c.avatar_url);   // a user-supplied photo (removable)
    var anyImg = hasAnyImage(name);          // photo or designed emblem (viewable)
    var m = document.createElement("div"); m.id = "portrait-menu"; m.className = "portrait-menu";
    var items = [];
    if (anyImg) items.push(["🔍 View larger", function () { openLightbox(name); }]);
    items.push(["🔊 Hear voice", function () { if (window.VoiceLayer) window.VoiceLayer.preview(name); }]);
    items.push([hasPhoto ? "✎ Change image" : "✎ Add image", function () { changePortrait(name); }]);
    if (hasPhoto) items.push(["✕ Remove image", function () { resetPortrait(name); }]);
    items.forEach(function (it) {
      var b = document.createElement("button"); b.className = "pm-item"; b.textContent = it[0];
      b.onclick = function (e) { e.stopPropagation(); closePortraitMenu(); it[1](); };
      m.appendChild(b);
    });
    document.body.appendChild(m);
    var r = anchor.getBoundingClientRect();
    m.style.left = Math.max(6, Math.min(r.left, window.innerWidth - m.offsetWidth - 6)) + "px";
    m.style.top = Math.min(r.bottom + 4, window.innerHeight - m.offsetHeight - 6) + "px";
    setTimeout(function () { document.addEventListener("click", closePortraitMenu, true); }, 0);
  }
  function openLightbox(name) {
    var u = portraitUrl(name) || emblemRaster(name); if (!u) return;
    var ov = document.createElement("div"); ov.className = "lightbox";
    var img = document.createElement("img"); img.src = u; img.alt = name;
    var cap = document.createElement("div"); cap.className = "lb-name"; cap.textContent = name;
    ov.appendChild(img); ov.appendChild(cap);
    ov.onclick = function () { ov.parentNode.removeChild(ov); };
    document.body.appendChild(ov);
  }

  // How the Underground regards you — a stance chip per roster card (SACRED-derived).
  function loadAffinities() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/affinities").then(function (res) {
      state.affinities = res.affinities || {};
      renderAffinities();
    }).catch(function () {});
  }
  function renderAffinities() {
    var aff = state.affinities || {};
    Array.prototype.forEach.call(document.querySelectorAll("#roster .affinity"), function (slot) {
      var a = aff[slot.dataset.for];
      if (!a) { slot.innerHTML = ""; return; }
      slot.innerHTML = '<span class="chip ' + (STANCE_CLASS[a.stance] || "free") +
        '" title="' + a.basis + '">' + a.stance + "</span>";
    });
    renderHeroTitle();   // the chat banner's stance chip, once affinities are in
  }

  // a brief, tappable nudge (reuses the reach-toast surface)
  function miniToast(msg) {
    var t = $("reach-toast"); if (!t) return;
    t.innerHTML = ""; t.textContent = msg;
    t.classList.remove("hidden");
    t.onclick = function () { t.classList.add("hidden"); };
    clearTimeout(t._timer); t._timer = setTimeout(function () { t.classList.add("hidden"); }, 3800);
  }

  // ── Easter eggs ────────────────────────────────────────────────────────────
  // "You are filled with DETERMINATION." — a gold flash + a rain of ember-gems.
  function determinationBurst(msg) {
    miniToast(msg || "* You are filled with DETERMINATION.");
    if (window.VoiceLayer) window.VoiceLayer.ui();
    var flash = document.createElement("div"); flash.className = "dt-flash";
    document.body.appendChild(flash);
    setTimeout(function () { if (flash.parentNode) flash.parentNode.removeChild(flash); }, 950);
    for (var i = 0; i < 26; i++) {
      var s = document.createElement("span"); s.className = "dt-gem soul-sigil";
      s.style.left = Math.floor(Math.random() * 100) + "vw";
      s.style.animationDelay = (Math.random() * 0.5).toFixed(2) + "s";
      s.style.animationDuration = (1.4 + Math.random() * 1.6).toFixed(2) + "s";
      document.body.appendChild(s);
      (function (el) { setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 3400); })(s);
    }
  }
  // ── word Easter eggs: say the magic word in chat and something happens ──────
  function rainItems(chars, count) {
    for (var i = 0; i < (count || 22); i++) {
      var s = document.createElement("span"); s.className = "fall-item";
      s.textContent = chars[i % chars.length];
      s.style.left = Math.floor(Math.random() * 100) + "vw";
      s.style.fontSize = (16 + Math.floor(Math.random() * 16)) + "px";
      s.style.animationDelay = (Math.random() * 0.6).toFixed(2) + "s";
      s.style.animationDuration = (1.6 + Math.random() * 1.6).toFixed(2) + "s";
      document.body.appendChild(s);
      (function (el) { setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 3800); })(s);
    }
  }
  function colorFlash(color) {
    var f = document.createElement("div"); f.className = "dt-flash"; f.style.background = color;
    document.body.appendChild(f);
    setTimeout(function () { if (f.parentNode) f.parentNode.removeChild(f); }, 950);
  }
  function discoFlash() { ["#ff3bd0", "#3bd0ff", "#ffd23b"].forEach(function (c, i) { setTimeout(function () { colorFlash(c); }, i * 170); }); }

  var WORD_EGGS = [
    { re: /spaghetti/i, run: function () { rainItems(["🍝", "🍝", "🍝", "🍅"]); miniToast("* NYEH HEH HEH! HAVE SOME SPAGHETTI!"); } },
    { re: /\bnyeh+\b/i, run: function () { miniToast("* NYEH HEH HEH HEH!"); } },
    { re: /\bhowdy\b/i, run: function () { rainItems(["🌼", "🌼", "🔸", "⚪"]); miniToast("* Howdy! I'm FLOWEY. FLOWEY the FLOWER!"); } },
    { re: /butterscotch/i, run: function () { rainItems(["🥧", "🧈", "🍮"]); miniToast("* (a slice of butterscotch-cinnamon pie appears.)"); } },
    { re: /(oh,?\s?yes)|\bmettaton\b|gorgeous|fabulous/i, run: function () { discoFlash(); rainItems(["✨", "💎", "⭐", "💖"]); miniToast("* OHHH YES! Simply GORGEOUS, darling!"); } },
    { re: /megalovania|bad time/i, run: function () { colorFlash("#3aa0ff"); if (window.VoiceLayer) window.VoiceLayer.blip("Sans"); miniToast("* huh. you're gonna have a bad time."); } },
    { re: /\bundyne\b|suplex/i, run: function () { colorFlash("#2ec9a0"); miniToast("* NGAHHH!! FUHUHUHU!"); } },
    { re: /annoying dog|\bdoggo\b/i, run: function () { rainItems(["🐶", "🦴"]); miniToast("* (a small white dog trots across the screen, and steals something.)"); } },
    { re: /determination/i, run: function () { determinationBurst(); } },
    // ── Dark World eggs ─────────────────────────────────────────────────────
    { re: /\bchaos\b/i, run: function () { discoFlash(); rainItems(["♠", "♦", "♣", "♥"]); miniToast("* CHAOS, CHAOS! UEE HEE HEE!"); } },
    { re: /ho ho ho/i, run: function () { rainItems(["♠", "🚲"]); miniToast("* HO HO HO! I, LANCER, APPROVE THIS MESSAGE!"); } },
    { re: /\bworm(s|eth)?\b/i, run: function () { miniToast("* ROUXLS KAARD APPROACHETH. HANDETH OVER THY WORMS."); } },
    { re: /\bprophecy\b/i, run: function () { colorFlash("#b48bf2"); miniToast("* (a legend whispers itself, older than the dark.)"); } },
    { re: /^egg$/i, run: function () { miniToast("* (you got the egg.)"); } },
  ];
  var _eggCooling = false;
  function runWordEgg(msg) {
    if (_eggCooling) return;
    var m = (msg || "").trim(), egg = null;
    var gen = (((state.truth || {}).route || {}).route === "Genocide");
    if (/^[.…]{2,}$/.test(m)) egg = function () { colorFlash("#3aa0ff"); miniToast("* ...(sans says nothing. but he's watching.)"); };
    else if (/\bchara\b/i.test(m)) egg = gen ? openHiddenRoom : function () { miniToast("* a name you shouldn't know."); };
    else { for (var i = 0; i < WORD_EGGS.length; i++) { if (WORD_EGGS[i].re.test(m)) { egg = WORD_EGGS[i].run; break; } } }
    if (!egg) return;
    _eggCooling = true; setTimeout(function () { _eggCooling = false; }, 3500);
    egg();
  }

  // A hidden room — only reachable on a Genocide save (say "chara"). It knows you.
  function openHiddenRoom() {
    if ($("hidden-room")) return;
    var ov = document.createElement("div"); ov.id = "hidden-room"; ov.className = "hidden-room";
    ov.innerHTML = '<div class="hr-box"><span class="soul-sigil determined hr-sigil" aria-hidden="true"></span>' +
      '<div class="hr-lines" id="hr-lines"></div><div class="hr-close">(click anywhere to leave)</div></div>';
    document.body.appendChild(ov);
    ov.onclick = function () { if (ov.parentNode) ov.parentNode.removeChild(ov); };
    var lines = ["...", "so you found me.", "the one who remembers this place.", "we are the same, you and i.", "...", "shall we go further?"];
    var el = $("hr-lines"), i = 0;
    (function next() {
      if (i >= lines.length || !$("hidden-room")) return;
      var p = document.createElement("div"); p.className = "hr-line"; p.textContent = "* " + lines[i++];
      el.appendChild(p);
      setTimeout(next, 1150);
    })();
  }

  // Rapid-tap a character's portrait in the chat banner and they react.
  var EMOTES = {
    "Sans": "* heh. what?",
    "Papyrus": "* NYEH?! YOU REQUIRE THE GREAT PAPYRUS?",
    "Flowey": "* Hee hee hee. Poking me?",
    "Toriel": "* Oh! Hello, my child.",
    "Undyne": "* HEY! Quit poking me, punk!",
    "Alphys": "* A-ah! W-what is it?!",
    "Asgore": "* Howdy. Did you need something?",
    "Mettaton": "* Ooh, a fan! Mind the finish, darling.",
    "Napstablook": "* oh... did you need me... sorry...",
    "Susie": "* WHAT. ...what?", "Ralsei": "* Oh! Um, hello!",
    "Lancer": "* HO HO HO! You rang?", "Noelle": "* O-oh! Hi! Sorry! Hi.",
    "King": "* You DARE prod at the King?", "Rouxls Kaard": "* UNHANDETH ME, WORM.",
    "Jevil": "* UEE HEE HEE! POKES, POKES!", "Seam": "* Krrr... easy on the stitching, traveller.",
  };
  function selectCharacter(c) {
    // no save yet? let them HEAR the voice and nudge them to read a save to talk.
    if (!state.projectId) {
      if (window.VoiceLayer) window.VoiceLayer.preview(c.name);
      miniToast("Read a save to talk to " + c.name + " — tap “＋ Read a save”.");
      return;
    }
    state.character = c.name;
    if (window.VoiceLayer && state.settings && state.settings.hud && state.settings.hud.blip) {
      window.VoiceLayer.ui();   // soft menu-confirm on selecting a speaker
    }
    if (!state.history[c.name]) state.history[c.name] = [];
    $$("#roster .char-card, #speaker-strip .face").forEach(function (el) {
      el.classList.toggle("selected", el.dataset.name === c.name);
    });
    // character presence banner: portrait + name + epithet + how they regard you
    $("chat-hero").classList.remove("hidden");
    $("chat-name").textContent = c.name;
    renderHeroTitle();
    var p = $("chat-portrait");
    if (p) p.outerHTML = avatarMarkup(c.name, "relic-portrait", "chat-portrait");
    // their own theme while you talk to them (falls back to the route bed if absent)
    if (window.MusicLayer && $("music-toggle").checked) window.MusicLayer.setCharacter(slug(c.name));
    showView("chat");
    renderTranscript();   // show what we have immediately (placeholder or local history)
    // Load the persisted transcript so the conversation survives a reload. Only
    // adopt it if nothing was typed locally in the meantime (a fast
    // send-after-select must not be clobbered), and only render if this is still
    // the selected character.
    api("/api/projects/" + state.projectId + "/conversations/" + c.name.toLowerCase())
      .then(function (res) {
        if ((state.history[c.name] || []).length === 0) {
          state.history[c.name] = (res.messages || []).map(function (m) {
            return { role: m.role, content: m.content };
          });
        }
        if (state.character === c.name) renderTranscript();
      })
      .catch(function () { if (state.character === c.name) renderTranscript(); });
  }

  // ── chat ──────────────────────────────────────────────────────────────────
  function avatarFor(name) { return portraitUrl(name); }

  // a transient "they're typing" bubble; any renderTranscript() clears it
  function showTyping() {
    var t = $("transcript"); if (!t || !state.character) return;
    var msg = document.createElement("div"); msg.className = "msg them typing-row";
    var holder = document.createElement("div"); holder.innerHTML = avatarMarkup(state.character, "bubble-avatar");
    if (holder.firstChild) msg.appendChild(holder.firstChild);
    var b = document.createElement("div"); b.className = "bubble them speaker-" + slug(state.character);
    b.innerHTML = '<div class="who">' + state.character +
      '</div><span class="typing-dots"><i></i><i></i><i></i></span>';
    msg.appendChild(b);
    t.appendChild(msg);
    scrollChatToBottom(true);
  }

  function renderTranscript() {
    var t = $("transcript"); t.innerHTML = "";
    // once a speaker is chosen, mobile chat goes immersive (chrome slides away)
    document.body.classList.toggle("chatting", !!state.character);
    if (!state.character) { var hero = $("chat-hero"); if (hero) hero.classList.add("hidden"); }
    if (!state.character) {
      var cast = state.characters || [];
      var castHtml = cast.map(function (c) {
        return '<button class="ce-face" type="button" data-name="' + escHtml(c.name) + '" title="' +
          (state.projectId ? "Talk to " : "Hear ") + escHtml(c.name) + '">' +
          avatarMarkup(c.name, "ce-face-img") + "<span>" + escHtml(c.name) + "</span></button>";
      }).join("");
      t.innerHTML = '<div class="chat-empty">' +
        '<span class="soul-sigil chat-empty-sigil" aria-hidden="true"></span>' +
        '<p class="chat-empty-prompt">' +
        (state.projectId ? "Pick someone to talk to." : "Show Ember your save file and the cast will talk about YOUR run — or tap a face to hear their voice.") +
        "</p>" +
        (state.projectId ? "" :
          '<button class="btn read-save-cta" data-go-saves>📂 Read a save — start here</button>' +
          '<p class="chat-empty-need muted">You\'ll need <code>file0</code> from your game folder ' +
          '(and <code>undertale.ini</code> if you can) — the reader has a step-by-step guide.</p>') +
        (cast.length ? '<div class="chat-empty-cast">' + castHtml + "</div>" : "") +
        '<p class="chat-empty-quote">“' + quoteOfDay() + '”</p>' +
        '<div class="chat-empty-go">' +
          '<button class="go-card" data-go="soundtest"><b>🎵</b><span class="go-title">Sound Test</span><span class="go-sub">play the whole soundtrack — or jam the cast together</span></button>' +
          '<button class="go-card" data-go="guided"><b>🧭</b><span class="go-title">Guided Mode</span><span class="go-sub">play beside them — every save becomes a beat</span></button>' +
          '<button class="go-card" data-go="reports"><b>📋</b><span class="go-title">Report Cards</span><span class="go-sub">how did you really do? they\'ll tell you</span></button>' +
        "</div></div>";
      $$(".go-card").forEach(function (btn) {
        btn.onclick = function () { navTo(btn.dataset.go); };
      });
      if (document.body.classList.contains("edition-lite")) renderLiteCards();
      $$(".ce-face").forEach(function (btn) {
        btn.onclick = function () {
          var c = charByName(btn.dataset.name);
          if (state.projectId && c) selectCharacter(c);
          else if (window.VoiceLayer) window.VoiceLayer.preview(btn.dataset.name);
        };
      });
      return;
    }
    (state.history[state.character] || []).forEach(function (m) {
      var them = m.role !== "user";
      var msg = document.createElement("div");
      msg.className = "msg " + (them ? "them" : "you");

      // the speaker's portrait sits beside their reply (photo > emblem > crest)
      if (them) {
        var holder = document.createElement("div");
        holder.innerHTML = avatarMarkup(state.character, "bubble-avatar");
        msg.appendChild(holder.firstChild);
      }

      var b = document.createElement("div");
      b.className = "bubble " + (them ? "them" : "you") +
        (them ? " speaker-" + slug(state.character) : "");
      var who = document.createElement("div");
      who.className = "who"; who.textContent = them ? state.character : "you";
      var span = document.createElement("span");
      span.textContent = m.content;
      b.appendChild(who); b.appendChild(span);
      msg.appendChild(b);
      t.appendChild(msg);
    });
    // a fresh conversation? offer a few grounded starters so the input's never blank
    if ((state.history[state.character] || []).length === 0) {
      var box = document.createElement("div"); box.className = "starters";
      var lbl = document.createElement("div"); lbl.className = "starters-lbl";
      lbl.textContent = "Ask " + state.character + "…"; box.appendChild(lbl);
      starterPrompts(state.character).forEach(function (q) {
        var c = document.createElement("button"); c.className = "starter-chip"; c.type = "button";
        c.textContent = q;
        c.onclick = function () { $("chat-input").value = q; sendMessage(); };
        box.appendChild(c);
      });
      t.appendChild(box);
    }
    scrollChatToBottom(true);   // land on the latest line when (re)rendering
  }

  // Save-aware conversation starters — generic openers plus a couple keyed to the
  // real route / LOVE and the speaker, so the grounding shows from the first tap.
  function starterPrompts(name) {
    var t = state.truth || {};
    var route = ((t.route) || {}).route;
    var love = ((t.play_state) || {}).love;
    if (t.game === "deltarune") {
      var drS = ["How do you feel about my run?", "What do you make of the Dark World?"];
      var drFlavor = {
        Susie: "was i tough enough?", Ralsei: "did i follow the prophecy?",
        Lancer: "am i a good bad guy?", Noelle: "do you remember me from class?",
        King: "why do you hate the lightners?", "Rouxls Kaard": "how were thy puzzles?",
        Jevil: "what game are we playing?", Seam: "what's coming, seam?",
        Toriel: "how was school today?", Sans: "have we met before?",
        Asgore: "how's the flower shop?", Alphys: "what anime should i watch?",
      };
      if (drFlavor[name]) drS.push(drFlavor[name]);
      drS.push("Do you remember what I did?");
      return drS.slice(0, 4);
    }
    var s = ["How do you feel about my run?"];
    if (route && route !== "undetermined") s.push("What does my " + route + " path say about me?");
    if (love !== null && love !== undefined) s.push("What do you make of my LOVE?");
    s.push("Do you remember what I did?");
    var flavor = {
      Sans: "you've been watching, haven't you?",
      Flowey: "are you enjoying this?",
      Toriel: "would you have guided me differently?",
      Papyrus: "did i do a cool job?",
      Undyne: "was i strong enough?",
      Alphys: "were you keeping notes on me?",
      Asgore: "do you forgive me?",
      Mettaton: "was my run good television?",
      Napstablook: "was any of it… okay?",
    };
    if (flavor[name]) s.push(flavor[name]);
    return s.slice(0, 4);
  }

  // Keep the newest dialogue in view. Pins whichever element actually scrolls
  // (the transcript on desktop, the stage on mobile). `force` always jumps to the
  // bottom (on send / render); otherwise it only follows if already near the end,
  // so scrolling up to read history isn't yanked away mid-reply.
  function scrollChatToBottom(force) {
    [$("transcript"), $("stage")].forEach(function (el) {
      if (!el) return;
      if (force || (el.scrollHeight - el.scrollTop - el.clientHeight) < 120) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }

  // append the blinking ▼ "continue" arrow to a finished line of dialogue
  function dialogueDone(span, name) {
    var bubble = span.parentNode; if (!bubble) return;
    bubble.classList.remove("ink-reveal");
    if (!bubble.classList.contains("them")) return;
    var prov = bubble.querySelector(".grounding");
    var arrow = document.createElement("span"); arrow.className = "dialogue-arrow"; arrow.textContent = "▼";
    bubble.insertBefore(arrow, prov || null);
    scrollChatToBottom();   // settle on the finished line
  }
  // ── Undertale-feel: *asterisk-marked* words shake for emphasis ────────────
  // Parse a line into clean text (markers stripped) + the char ranges to shake.
  // The markers never render; the shake activates when the line finishes typing.
  function parseEmphasis(text) {
    var spans = [], clean = "", last = 0, re = /\*([^*\n]+)\*/g, m;
    while ((m = re.exec(text))) {
      clean += text.slice(last, m.index);
      var s = clean.length;
      clean += m[1];
      spans.push({ s: s, e: clean.length });
      last = re.lastIndex;
    }
    clean += text.slice(last);
    return { text: clean, spans: spans };
  }
  function escHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  // Swap a finished line's plain text for shake-wrapped HTML (motion permitting).
  function applyShake(el, text, spans) {
    var motion = !(state.settings && state.settings.hud && state.settings.hud.motion === false);
    if (!spans.length || !motion) { el.textContent = text; return; }
    var html = "", cur = 0;
    spans.forEach(function (r) {
      html += escHtml(text.slice(cur, r.s));
      html += '<span class="shake">' + escHtml(text.slice(r.s, r.e)) + "</span>";
      cur = r.e;
    });
    html += escHtml(text.slice(cur));
    el.innerHTML = html;
  }

  function typewriter(span, text, name) {
    var parsed = parseEmphasis(text);
    text = parsed.text;
    var ms = (state.settings && state.settings.hud.typewriterMs);
    if (ms == null) ms = 18;
    if (!ms) { applyShake(span, text, parsed.spans); dialogueDone(span, name); return; }   // instant
    span.textContent = ""; span.parentNode.classList.add("ink-reveal");
    var i = 0, every = blipEvery(name);   // cadence is per-character (voices.js)
    var timer = setInterval(function () {
      // stop the moment this line leaves the DOM (you switched characters / re-rendered)
      // — no more typing, and crucially no more blips in the old character's voice
      if (!span.isConnected) { clearInterval(timer); return; }
      span.textContent = text.slice(0, ++i);
      if (i % every === 0 && /\S/.test(text.charAt(i - 1))) blip(name);   // a blip every few glyphs
      scrollChatToBottom();   // follow the reply as it types (unless you've scrolled up)
      if (i >= text.length) { clearInterval(timer); applyShake(span, text, parsed.spans); dialogueDone(span, name); }
    }, ms);
  }

  function sendMessage() {
    var input = $("chat-input"); var msg = input.value.trim();
    if (!msg || !state.projectId || !state.character) return;
    runWordEgg(msg);   // secret words → sparks of chaos (message still sends)
    var who = state.character;   // capture: the reply belongs to THIS character
    var hist = state.history[who];
    hist.push({ role: "user", content: msg });
    renderTranscript(); input.value = "";
    showTyping();   // a "…" while we wait on the reply (removed by the next render)
    var body = { character: who, message: msg, history: hist.slice(0, -1),
                 options: (state.settings || {}).options };
    api("/api/projects/" + state.projectId + "/chat", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(function (res) {
      hist.push({ role: "assistant", content: res.response });   // always saved to their history
      if (state.character !== who) return;   // switched away → it's stored, don't type it into the new chat
      renderTranscript();
      var row = $("transcript").lastChild;                 // the .msg row
      var bubble = row.querySelector(".bubble") || row;     // provenance rides the bubble
      renderProvenance(bubble, res);   // the wall, made visible (before the arrow)
      scrollChatToBottom(true);        // pin to the reply before it starts typing
      typewriter(bubble.querySelector("span"), res.response, who);
    }).catch(function (e) {
      hist.push({ role: "assistant", content: "(error: " + e.message + ")" });
      if (state.character === who) renderTranscript();
    });
  }

  // ── provenance overlay (sacred vs free, + the hallucination guard) ───────
  function chip(cls, text) {
    var s = document.createElement("span");
    s.className = "chip " + cls; s.textContent = text; return s;
  }
  function renderProvenance(bubble, res) {
    var p = res.provenance; if (!p) return;
    var box = document.createElement("div");
    box.className = "provenance hidden";   // detail is tucked away; a toggle reveals it
    var s = p.sacred, f = p.free;
    box.appendChild(Object.assign(document.createElement("span"),
      { className: "label", textContent: "SACRED" }));
    if (s.route) box.appendChild(chip("sacred", "route: " + s.route));
    if (s.love !== null && s.love !== undefined) box.appendChild(chip("sacred", "LOVE: " + s.love));
    if (s.kills !== null && s.kills !== undefined) box.appendChild(chip("sacred", "kills: " + s.kills));
    if (res.path_turn) {
      box.appendChild(chip("sacred", "↳ path turned: " + res.path_turn.from + " → " + res.path_turn.to));
    }
    var disp = s.dispositions || {};
    Object.keys(disp).forEach(function (who) {
      box.appendChild(chip("sacred", who + ": " + disp[who]));
    });
    if (s.area) box.appendChild(chip("sacred", "area: " + s.area));
    if (s.playtime) box.appendChild(chip("sacred", "time: " + s.playtime));
    if (s.fun_event) box.appendChild(chip("warn", "⌖ anomaly: " + s.fun_event));
    box.appendChild(Object.assign(document.createElement("span"),
      { className: "label", textContent: "FREE" }));
    if (f.voice) box.appendChild(chip("free", "voice: " + f.voice));
    (f.lore || []).slice(0, 3).forEach(function (t) { box.appendChild(chip("free", "lore: " + t)); });
    if (f.memory_used) box.appendChild(chip("free", "memory"));
    if (f.remembrance_used) box.appendChild(chip("free", "remembers"));
    // Model-less replies own it: the Spark engine spoke (by choice or as the
    // graceful degrade) — still grounded, just scripted.
    if (res.grounding && res.grounding.source === "deterministic_fallback") {
      var sparkMode = state.power && state.power.source === "none";
      box.appendChild(chip("free", sparkMode ? "🕯 spark voice" : "🕯 spark voice (model unreachable)"));
    }
    // The guard verdict becomes the toggle's label — the at-a-glance signal — and
    // the full sacred/free breakdown stays folded behind it so it never crowds the
    // reply. Tap to expand. (Respects the HUD "Provenance chips" setting via .grounding.)
    var clean = !(res.guard && res.guard.clean === false);
    var wrap = document.createElement("div"); wrap.className = "grounding";
    var toggle = document.createElement("button"); toggle.type = "button";
    toggle.className = "prov-toggle" + (clean ? "" : " warn");
    toggle.innerHTML = (clean ? "✓ grounded" : "⚠ check (" + res.guard.issues.length + ")") +
      ' <span class="prov-caret">ⓘ</span>';
    toggle.setAttribute("aria-expanded", "false");
    toggle.onclick = function () {
      var open = !box.classList.toggle("hidden");
      toggle.classList.toggle("open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    };
    wrap.appendChild(toggle); wrap.appendChild(box);
    bubble.appendChild(wrap);
  }



  // ── ♿ Vision & Reading: settings live on <html> classes + localStorage ────
  function a11yLoad() {
    try { return JSON.parse(localStorage.getItem("uv_a11y") || "[]"); } catch (e) { return []; }
  }
  function a11ySave(list) { try { localStorage.setItem("uv_a11y", JSON.stringify(list)); } catch (e) {} }
  function openVisionModal() {
    var on = a11yLoad();
    $$("#vision-modal [data-a11y]").forEach(function (c) { c.checked = on.indexOf(c.dataset.a11y) !== -1; });
    $("vision-modal").classList.remove("hidden");
    trapFocus($("vision-modal"));
  }
  function closeVisionModal() { $("vision-modal").classList.add("hidden"); releaseFocus($("vision-modal")); }
  function a11yToggle(key, onNow) {
    var list = a11yLoad().filter(function (k) { return k !== key; });
    if (onNow) list.push(key);
    a11ySave(list);
    document.documentElement.classList.toggle("a11y-" + key, onNow);
  }

  // ── the Prompt Workshop: live-true prompt content + click-to-copy ──────────
  var _workshopLoaded = false;
  function showWorkshop() {
    showView("workshop");
    if (_workshopLoaded) return;
    api("/api/workshop").then(function (w) {
      _workshopLoaded = true;
      var an = $("ws-anatomy"); an.innerHTML = "";
      (w.anatomy || []).forEach(function (a) {
        var row = document.createElement("div"); row.className = "ws-row";
        row.innerHTML = '<span class="ws-bucket ' + a.bucket.toLowerCase() + '">' + a.bucket + "</span>" +
          "<div><strong>" + a.n + " · " + a.label + "</strong><div class='muted'>" + a.what + "</div></div>";
        an.appendChild(row);
      });
      $("ws-example-note").textContent = w.example_note || "";
      $("ws-example").textContent = w.example_prompt || "";
      var box = $("ws-instructions"); box.innerHTML = "";
      (w.instructions || []).forEach(function (i) {
        var c = document.createElement("div"); c.className = "ws-card";
        c.innerHTML = "<div class='ws-card-head'>" + i.icon + " <strong>" + i.feature + "</strong>" +
          " <span class='muted'>· " + i.source + "</span></div>";
        var pre = document.createElement("pre"); pre.className = "ws-prompt";
        pre.textContent = i.text; c.appendChild(pre);
        box.appendChild(c);
      });
    }).catch(function () { $("ws-example").textContent = "(couldn't reach /api/workshop)"; });
  }
  // any prompt block: tap to copy (a tiny flash confirms)
  document.addEventListener("click", function (e) {
    var pre = e.target.closest && e.target.closest(".ws-prompt");
    if (!pre || !navigator.clipboard) return;
    navigator.clipboard.writeText(pre.textContent).then(function () {
      pre.classList.add("copied");
      setTimeout(function () { pre.classList.remove("copied"); }, 700);
      miniToast("prompt copied");
    }).catch(function () {});
  });


  // ── judgment ──────────────────────────────────────────────────────────────
  function showJudgment() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/judgment").then(function (res) {
      var j = res.judgment;
      $("verdict-line").textContent = '"' + j.verdict.line + '"  — ' + j.verdict.label;
      var f = j.facts;
      function fmt(v) { return (v === null || v === undefined || v === "") ? "—" : v; }
      $("judgment-facts").innerHTML =
        row("Route", fmt(f.route) + " (" + fmt(f.route_confidence) + ")") +
        row("LOVE", fmt(f.love)) + row("Kills", fmt(f.total_kills)) + row("Name", fmt(f.name));
      var gaps = $("judgment-gaps"); gaps.innerHTML = "";
      (j.honest_gaps || []).forEach(function (g) {
        var li = document.createElement("li"); li.textContent = g; gaps.appendChild(li);
      });
      $("spoken-box").classList.add("hidden");
      showView("judgment");
    });
  }

  function speakJudgment() {
    if (!state.projectId) return;
    var who = state.character || "sans";
    api("/api/projects/" + state.projectId + "/judgment/speak", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ character: who.toLowerCase() }),
    }).then(function (res) {
      var box = $("spoken-box");
      box.innerHTML = '<div class="who">' + res.character + "</div>";
      var span = document.createElement("span"); box.appendChild(span);
      box.classList.remove("hidden");
      typewriter(span, res.spoken, res.character);
    });
  }

  // ── wiring ────────────────────────────────────────────────────────────────
  // ── The Chronicle (in-app viewer + markdown export) ────────────────────────
  var chronicleMd = "";   // last-fetched markdown, for download

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  // tiny markdown → HTML, just enough for the Chronicle's shape (#, ##, **, -, ---, *)
  function mdToHtml(md) {
    var out = [], inList = false;
    md.split("\n").forEach(function (raw) {
      var line = esc(raw);
      line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
                 .replace(/(^|[^*])\*(?!\*)([^*]+?)\*/g, "$1<em>$2</em>");
      if (/^- /.test(raw)) {
        if (!inList) { out.push("<ul>"); inList = true; }
        out.push("<li>" + line.slice(2) + "</li>"); return;
      }
      if (inList) { out.push("</ul>"); inList = false; }
      if (/^# /.test(raw)) out.push("<h2>" + line.slice(2) + "</h2>");
      else if (/^## /.test(raw)) out.push("<h3>" + line.slice(3) + "</h3>");
      else if (/^---\s*$/.test(raw)) out.push("<hr/>");
      else if (raw.trim() === "") out.push("");
      else out.push("<p>" + line + "</p>");
    });
    if (inList) out.push("</ul>");
    return out.join("\n");
  }

  function showChronicle() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/chronicle").then(function (res) {
      chronicleMd = res.markdown;
      $("chronicle-content").innerHTML = mdToHtml(res.markdown);
      showView("chronicle");
    }).catch(function (e) { $("upload-status").textContent = "Chronicle error: " + e.message; });
  }

  function downloadChronicle() {
    if (!chronicleMd) return;
    var blob = new Blob([chronicleMd], { type: "text/markdown" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    var slug = ($("chronicle-content").querySelector("h2") || {}).textContent || "chronicle";
    a.href = url; a.download = slug.replace(/[^a-z0-9]+/gi, "_").toLowerCase() + ".md";
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  function downloadText(text, filename) {
    var blob = new Blob([text], { type: "text/markdown" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  function openCharacter(name) {
    var c = (state.characters || []).filter(function (x) { return x.name === name; })[0];
    if (c) selectCharacter(c); else showView("chat");
  }

  // ── The Keepsake Journal ───────────────────────────────────────────────────
  function showJournal() {
    if (!state.projectId) return;
    var sel = $("journal-author");
    if (sel.options.length === 0) {
      (state.characters || []).forEach(function (c) {
        var o = document.createElement("option"); o.value = c.name; o.textContent = c.name; sel.appendChild(o);
      });
    }
    loadJournal();
    showView("journal");
  }
  function loadJournal() {
    api("/api/projects/" + state.projectId + "/journal").then(function (res) {
      state.journalMd = res.markdown;
      var box = $("journal-entries"); box.innerHTML = "";
      if (!res.entries.length) {
        box.innerHTML = '<p class="muted">No one has written here yet — ask someone to leave you a page.</p>';
        return;
      }
      res.entries.forEach(function (e) {
        var d = document.createElement("div"); d.className = "entry";
        d.innerHTML = '<div class="entry-head">' + e.author +
          (e.route_context ? ' <span class="muted">· ' + e.route_context + "</span>" : "") +
          '</div><div class="entry-text"></div>';
        d.querySelector(".entry-text").textContent = e.text;
        box.appendChild(d);
      });
    });
  }
  function inscribeJournal() {
    if (!state.projectId) return;
    var btn = $("journal-inscribe-btn"); btn.disabled = true; btn.textContent = "writing…";
    api("/api/projects/" + state.projectId + "/journal/inscribe", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ character: $("journal-author").value }),
    }).then(loadJournal).catch(function () {}).then(function () {
      btn.disabled = false; btn.textContent = "Ask them to write";
    });
  }

  // ── Report Cards — a persistent history: request, filter, archive, delete ──
  function showReports() {
    if (!state.projectId) return;
    populateReportSelects();
    refreshEmailStatus();
    loadReports();
    showView("reports");
  }
  function populateReportSelects() {
    var sel = $("report-author"), filt = $("report-filter");
    if (sel && sel.options.length === 0) {
      (state.characters || []).forEach(function (c) {
        var o = document.createElement("option"); o.value = c.name; o.textContent = c.name; sel.appendChild(o);
      });
    }
    if (filt && filt.options.length <= 1) {   // keep the leading "All characters"
      (state.characters || []).forEach(function (c) {
        var o = document.createElement("option"); o.value = c.name; o.textContent = c.name; filt.appendChild(o);
      });
    }
  }
  function reportQuery() {
    var status = $("report-archived-toggle").checked ? "archived" : "active";
    var character = $("report-filter").value || "";
    return "?status=" + status + (character ? "&character=" + encodeURIComponent(character) : "");
  }
  function loadReports() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/reports" + reportQuery()).then(function (res) {
      state.reportsShown = res.reports || [];
      renderReportList(res.reports || [], res.counts || {});
    }).catch(function () {});
  }
  function renderReportList(list, counts) {
    var box = $("reports-list"); box.innerHTML = "";
    var archived = $("report-archived-toggle").checked;
    $("report-count").textContent =
      (counts.active || 0) + " active" + (counts.archived ? " · " + counts.archived + " archived" : "");
    $("report-download-btn").disabled = !list.length;
    var dig = $("report-digest-btn");   // the list changed → allow a fresh digest
    if (dig) { dig.dataset.sent = ""; dig.textContent = "✉ Email digest"; }
    if (!list.length) {
      box.innerHTML = '<p class="muted">' +
        (archived ? "No archived reports." : "No reports yet — ask someone to file one on your run.") + "</p>";
      updateEmailButtons();
      return;
    }
    list.forEach(function (rep) { box.appendChild(reportCard(rep)); });
    updateEmailButtons();
  }
  function reportCard(rep) {
    var card = document.createElement("div");
    card.className = "report-card" + (rep.status === "archived" ? " archived" : "");
    var head = document.createElement("div"); head.className = "report-head";
    head.innerHTML = avatarMarkup(rep.author, "bubble-avatar") +
      '<span class="report-author">' + escHtml(rep.author) + "</span>" +
      (rep.route_context ? '<span class="report-route muted">· ' + escHtml(rep.route_context) + "</span>" : "") +
      (rep.verdict ? '<span class="report-verdict">' + escHtml(rep.verdict) + "</span>" : "");
    var body = document.createElement("div"); body.className = "report-body";
    body.textContent = rep.body || rep.text || "";
    var actions = document.createElement("div"); actions.className = "report-actions";
    actions.appendChild(mkReportBtn("＋ Journal", "btn tiny", function (b) { addReportToJournal(rep, b); }));
    actions.appendChild(mkReportBtn("✉ Email me", "btn tiny report-email-btn", function (b) { emailReport(rep, b); }));
    if (rep.status === "archived") {
      actions.appendChild(mkReportBtn("↩ Restore", "btn tiny", function () { setReportStatus(rep.id, "active"); }));
    } else {
      actions.appendChild(mkReportBtn("🗄 Archive", "btn tiny", function () { setReportStatus(rep.id, "archived"); }));
    }
    actions.appendChild(mkReportBtn("🗑 Delete", "btn tiny danger", function () { deleteReport(rep.id); }));
    card.appendChild(head); card.appendChild(body); card.appendChild(actions);
    return card;
  }
  function mkReportBtn(label, cls, onclick) {
    var b = document.createElement("button"); b.className = cls; b.textContent = label;
    b.onclick = function () { onclick(b); }; return b;
  }
  function reportBusy(busy, label) {
    ["report-request-btn", "report-full-btn"].forEach(function (id) { $(id).disabled = busy; });
    if (label !== undefined) $("report-hint").textContent = label;
  }
  function requestReport() {
    if (!state.projectId) return;
    var who = $("report-author").value; if (!who) return;
    reportBusy(true, who + " is writing your report…");
    if ($("report-archived-toggle").checked) $("report-archived-toggle").checked = false;  // reveal the new one
    api("/api/projects/" + state.projectId + "/report", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ character: who }),
    }).then(function () { $("report-hint").textContent = ""; loadReports(); })
      .catch(function (e) { $("report-hint").textContent = "Couldn't get a report: " + e.message; })
      .then(function () { reportBusy(false); });
  }
  function fullReport() {
    if (!state.projectId) return;
    var names = (state.characters || []).map(function (c) { return c.name; });
    if (!names.length) return;
    if ($("report-archived-toggle").checked) $("report-archived-toggle").checked = false;
    reportBusy(true);
    var i = 0;
    (function next() {
      if (i >= names.length) { reportBusy(false, ""); loadReports(); return; }
      var who = names[i++];
      $("report-hint").textContent = "Collecting reports… (" + i + "/" + names.length + ") — " + who;
      api("/api/projects/" + state.projectId + "/report", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ character: who }),
      }).catch(function () {}).then(next);
    })();
  }
  function setReportStatus(id, status) {
    api("/api/projects/" + state.projectId + "/reports/" + id, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: status }),
    }).then(loadReports).catch(function () {});
  }
  function deleteReport(id) {
    if (!confirm("Delete this report permanently?")) return;
    api("/api/projects/" + state.projectId + "/reports/" + id, { method: "DELETE" })
      .then(loadReports).catch(function () {});
  }
  function refreshEmailStatus() {
    api("/api/email/status").then(function (s) { state.emailStatus = s; updateEmailButtons(); }).catch(function () {});
  }
  function updateEmailButtons() {
    var on = !!(state.emailStatus && state.emailStatus.configured);
    var hint = (state.emailStatus && state.emailStatus.recipient_hint) || "";
    $$(".report-email-btn").forEach(function (b) {
      if (b.dataset.sent === "1") return;   // don't re-enable an already-sent button
      b.disabled = !on;
      b.title = on ? ("Email this report to you" + (hint ? " (" + hint + ")" : ""))
                   : "Email isn't set up — configure AgentMail (AGENTMAIL_API_KEY) to enable";
    });
    var dig = $("report-digest-btn");
    if (dig && dig.dataset.sent !== "1") {
      dig.disabled = !on || !(state.reportsShown && state.reportsShown.length);
      dig.title = on ? ("Email all your active reports as one digest" + (hint ? " (" + hint + ")" : ""))
                     : "Email isn't set up — configure AgentMail to enable";
    }
  }
  function emailDigest() {
    var btn = $("report-digest-btn"); if (!btn) return;
    btn.disabled = true; var t = btn.textContent; btn.textContent = "sending…";
    api("/api/projects/" + state.projectId + "/report/digest/email", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
    }).then(function (res) {
      if (res.email && res.email.sent) { btn.textContent = "✓ Digest sent"; btn.dataset.sent = "1"; }
      else { btn.textContent = t; btn.disabled = false; alert("Digest not sent: " + ((res.email && res.email.reason) || "unknown")); }
    }).catch(function (e) { btn.textContent = t; btn.disabled = false; alert("Digest failed: " + e.message); });
  }
  function addReportToJournal(rep, btn) {
    btn.disabled = true; var t = btn.textContent; btn.textContent = "saving…";
    api("/api/projects/" + state.projectId + "/journal/add", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author: rep.author, text: rep.text }),
    }).then(function () { btn.textContent = "✓ In journal"; })
      .catch(function () { btn.disabled = false; btn.textContent = t; });
  }
  function emailReport(rep, btn) {
    btn.disabled = true; btn.textContent = "sending…";
    api("/api/projects/" + state.projectId + "/report/email", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ character: rep.author, text: rep.text, verdict: rep.verdict }),
    }).then(function (res) {
      if (res.email && res.email.sent) { btn.textContent = "✓ Emailed"; btn.dataset.sent = "1"; }
      else { btn.disabled = false; btn.textContent = "✉ Email me"; alert("Email not sent: " + ((res.email && res.email.reason) || "unknown")); }
    }).catch(function (e) { btn.disabled = false; btn.textContent = "✉ Email me"; alert("Email failed: " + e.message); });
  }
  function downloadReports() {
    var list = state.reportsShown || [];
    if (!list.length) return;
    var md = "# Report Cards\n\n*The Underground's after-action reports on your run.*\n\n";
    list.forEach(function (r) {
      md += "## " + r.author + (r.verdict ? " — *" + r.verdict + "*" : "") + "\n\n" + (r.text || "") + "\n\n";
    });
    downloadText(md, "report_cards.md");
  }

  // ── Guided Mode: watch the save folder; every save becomes a beat ──────────
  var guidedES = null;
  var AREA_CHARS = { "the Ruins": "Toriel", "Snowdin": "Sans", "Waterfall": "Undyne",
                     "Hotland": "Alphys", "the Core": "Mettaton", "New Home": "Asgore" };
  function guidedParty() {
    try { return JSON.parse(localStorage.getItem("uv_guided_party") || "[]"); } catch (e) { return []; }
  }
  function setGuidedParty(list) {
    try { localStorage.setItem("uv_guided_party", JSON.stringify(list.slice(0, 4))); } catch (e) {}
    renderGuidedParty();
  }
  function renderGuidedParty() {
    var box = $("guided-party"); if (!box) return;
    var pinned = guidedParty();
    box.innerHTML = "";
    (state.characters || []).forEach(function (c) {
      var chip = document.createElement("button"); chip.type = "button";
      chip.className = "g-chip" + (pinned.indexOf(c.name) >= 0 ? " on" : "");
      chip.innerHTML = avatarMarkup(c.name, "g-chip-img") + "<span>" + escHtml(c.name) + "</span>";
      chip.onclick = function () {
        var p = guidedParty(), i = p.indexOf(c.name);
        if (i >= 0) p.splice(i, 1); else p.push(c.name);
        setGuidedParty(p);
      };
      box.appendChild(chip);
    });
  }
  function showGuided() {
    renderGuidedParty();
    guidedConnect();
    api("/api/guided/status").then(function (st) { guidedSyncStatus(st); }).catch(function () {});
    // re-register a remembered folder (server watch list is in-memory)
    var saved = localStorage.getItem("uv_guided_dir");
    if (saved && !$("guided-path").value) $("guided-path").value = saved;
    showView("guided");
  }
  function guidedSyncStatus(st) {
    var watching = (st.watching || []).length > 0;
    $("guided-watch-btn").classList.toggle("hidden", watching);
    $("guided-stop-btn").classList.toggle("hidden", !watching);
    $("guided-status").textContent = watching
      ? "Watching " + st.watching.join("  ·  ") + " — play and save; the party is listening."
      : "Not watching anything yet. Point Ember at the folder your game saves into, then just play — save in-game and the party reacts here.";
  }
  function guidedWatch() {
    var p = $("guided-path").value.trim(); if (!p) return;
    api("/api/guided/watch", { method: "POST", headers: { "Content-Type": "application/json" },
                               body: JSON.stringify({ path: p }) })
      .then(function (res) {
        try { localStorage.setItem("uv_guided_dir", p); } catch (e) {}
        guidedSyncStatus({ watching: res.watching });
        guidedBeatCard({ type: "watching", file: (res.found || []).join(", ") || "no saves yet" });
        (res.adopted || []).forEach(guidedBeatCard);
      })
      .catch(function (e) { $("guided-status").textContent = "Couldn't watch that folder: " + e.message; });
  }
  function guidedStop() {
    var p = localStorage.getItem("uv_guided_dir") || $("guided-path").value.trim();
    api("/api/guided/watch", { method: "DELETE", headers: { "Content-Type": "application/json" },
                               body: JSON.stringify({ path: p }) })
      .then(function (res) { guidedSyncStatus(res); }).catch(function () {});
  }
  function guidedConnect() {
    if (guidedES) return;
    try { guidedES = new EventSource("/api/guided/events"); } catch (e) { return; }
    guidedES.onmessage = function (m) {
      var beat; try { beat = JSON.parse(m.data); } catch (e) { return; }
      guidedBeatCard(beat);
      if (beat.type === "save" || beat.type === "adopted") {
        // follow the run: adopt the project as the active save
        if (beat.project_id && state.projectId !== beat.project_id) loadShelf();
        if (beat.project_id) {
          api("/api/projects/" + beat.project_id + "/save-truth").then(function (res) {
            state.projectId = beat.project_id;
            renderTruth(res.save_truth, beat.visit || null, "");
          }).catch(function () {});
        }
        if (beat.type === "save") guidedReactions(beat);
        guidedSuggest(beat);
      }
    };
  }
  function guidedBeatCard(beat) {
    var feed = $("guided-feed"); if (!feed) return;
    var ph = feed.querySelector("p.muted"); if (ph) ph.remove();
    var card = document.createElement("div"); card.className = "g-beat g-" + (beat.type || "note");
    var head = { adopted: "◆ picked up the save", save: "✦ SAVE", watching: "👁 watching" }[beat.type] || "·";
    var meta = [beat.name, beat.game === "deltarune" ? "Dark World" : beat.route, beat.area]
      .filter(Boolean).join(" · ");
    var lines = (beat.changes || []).map(function (c) { return "<li>" + escHtml(c) + "</li>"; }).join("");
    card.innerHTML = '<div class="g-beat-head"><b>' + head + "</b> <span class='muted'>" +
      escHtml(meta || beat.file || "") + "</span></div>" + (lines ? "<ul>" + lines + "</ul>" : "");
    feed.prepend(card);
  }
  function guidedReactions(beat) {
    // the pinned party speaks to WHAT CHANGED (the beat's sacred delta lines);
    // a QUIET save (no measured change) gets a single murmur from the lead, not
    // the whole party piling on
    var quiet = !(beat.changes && beat.changes.length);
    var party = guidedParty().slice(0, quiet ? 1 : 3);
    party.forEach(function (who, i) {
      setTimeout(function () {
        api("/api/projects/" + beat.project_id + "/guided-react", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ character: who, changes: beat.changes || [] }),
        }).then(function (res) {
          var feed = $("guided-feed");
          var card = document.createElement("div"); card.className = "g-beat g-voice";
          card.innerHTML = '<div class="g-beat-head">' + avatarMarkup(res.character, "g-chip-img") +
            "<b>" + escHtml(res.character) + "</b></div><div class='g-line'></div>";
          card.querySelector(".g-line").textContent = res.message;
          feed.prepend(card);
          if (window.VoiceLayer && state.settings && state.settings.hud && state.settings.hud.blip) {
            window.VoiceLayer.blip(res.character);
          }
        }).catch(function () {});
      }, i * 2500);
    });
  }
  function guidedSuggest(beat) {
    var box = $("guided-suggest"); if (!box) return;
    var who = beat.area && AREA_CHARS[beat.area];
    if (!who || guidedParty().indexOf(who) >= 0 || beat.game === "deltarune") {
      box.classList.add("hidden"); return;
    }
    box.innerHTML = "🌟 <em>" + escHtml(who) + "</em> knows " + escHtml(beat.area) +
      " — <button class='btn tiny' id='g-add-suggest'>add to party</button>";
    box.classList.remove("hidden");
    $("g-add-suggest").onclick = function () {
      var p = guidedParty(); p.push(who); setGuidedParty(p); box.classList.add("hidden");
    };
  }

  // 📖 Tonight's story: a character narrates the session's arc (sacred beats)
  function guidedStory() {
    if (!state.projectId) { guidedBeatCard({ type: "note", file: "no run adopted yet — watch a folder and save in-game." }); return; }
    var who = guidedSpeaker(), btn = $("g-story");
    btn.disabled = true; var t = btn.textContent; btn.textContent = "📖 writing…";
    api("/api/projects/" + state.projectId + "/session-story", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ character: who }),
    }).then(function (res) {
      var feed = $("guided-feed");
      var card = document.createElement("div"); card.className = "g-beat g-voice g-story";
      card.innerHTML = '<div class="g-beat-head">' + avatarMarkup(res.character, "g-chip-img") +
        "<b>" + escHtml(res.character) + "</b> <span class='muted'>· the story of this session · " +
        res.visits + " saves</span></div><div class='g-line'></div><div class='report-actions'></div>";
      card.querySelector(".g-line").textContent = res.text;
      var acts = card.querySelector(".report-actions");
      var jb = document.createElement("button"); jb.className = "btn tiny"; jb.textContent = "＋ Journal";
      jb.onclick = function () {
        jb.disabled = true; jb.textContent = "saving…";
        api("/api/projects/" + state.projectId + "/journal/add", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ author: res.character, text: res.text }),
        }).then(function () { jb.textContent = "✓ In journal"; })
          .catch(function () { jb.disabled = false; jb.textContent = "＋ Journal"; });
      };
      var db_ = document.createElement("button"); db_.className = "btn tiny"; db_.textContent = "⤓ .md";
      db_.onclick = function () {
        downloadText("# The story of this session — told by " + res.character + "\n\n" + res.text + "\n", "session_story.md");
      };
      acts.appendChild(jb); acts.appendChild(db_);
      feed.prepend(card);
    }).catch(function () {}).then(function () { btn.disabled = false; btn.textContent = t; });
  }

  // ── the Companion Pop-out: a slim window that floats beside the game ────────
  // Chrome's Document Picture-in-Picture gives a true always-on-top mini window;
  // anywhere it's unavailable (non-secure origin, other browsers) we fall back to
  // a small popup. Either way the live feed + ask bar move INTO it and come home
  // when it closes.
  var popoutWin = null;
  function guidedPopout() {
    if (popoutWin && !popoutWin.closed) { try { popoutWin.focus(); } catch (e) {} return; }
    var pip = window.documentPictureInPicture;
    if (pip && pip.requestWindow) {
      pip.requestWindow({ width: 420, height: 720 }).then(function (w) {
        popoutWin = w; guidedFillPopout(w, true);
      }).catch(function () { guidedPopupFallback(); });
    } else {
      guidedPopupFallback();
    }
  }
  function guidedPopupFallback() {
    var w = window.open("", "ember-companion", "width=420,height=720,resizable=yes");
    if (!w) { miniToast("Pop-out blocked — allow pop-ups for Ember, or keep this tab beside the game."); return; }
    popoutWin = w; guidedFillPopout(w, false);
  }
  function guidedFillPopout(w, isPip) {
    var doc = w.document;
    doc.title = "Ember · Companion";
    // carry the look: clone every stylesheet link + inline styles
    doc.head.innerHTML = "";
    $$("link[rel=stylesheet]").forEach(function (l) {
      var n = doc.createElement("link"); n.rel = "stylesheet";
      n.href = new URL(l.getAttribute("href"), location.href).href;
      doc.head.appendChild(n);
    });
    var meta = doc.createElement("meta"); meta.name = "viewport"; meta.content = "width=device-width, initial-scale=1";
    doc.head.appendChild(meta);
    doc.body.className = document.body.className + " companion";
    doc.body.innerHTML = '<div class="companion-shell">' +
      '<div class="companion-head"><span class="soul-sigil" style="width:16px;height:16px;"></span> ' +
      '<b>Ember rides along</b><span class="muted" id="c-status"></span></div>' +
      '<div id="companion-slot"></div></div>';
    // MOVE the live pieces in (the SSE feed keeps flowing into the same nodes).
    // Keep refs — once moved they live in the pop-out's document, so bringing
    // them home must reinsert these exact nodes, not re-query the main page.
    var slot = doc.getElementById("companion-slot");
    var partyBlock = document.querySelector(".guided-party");
    var askBlock = document.querySelector(".guided-ask");
    var feedEl = $("guided-feed");
    slot.appendChild(partyBlock);
    slot.appendChild(askBlock);
    slot.appendChild(feedEl);
    var back = function () {
      // bring everything home when the companion closes
      var view = $("view-guided");
      var anchor = view.querySelector(".g-feed-lbl");
      view.insertBefore(partyBlock, anchor);
      view.insertBefore(askBlock, anchor);
      view.appendChild(feedEl);
      popoutWin = null;
    };
    w.addEventListener("pagehide", back);
    w.addEventListener("unload", back);
  }

  // guided quick-asks: Where am I? (local truth summary) · What now? (the guide)
  function guidedSpeaker() {
    var p = guidedParty();
    if (p.length) return p[0];
    return ((state.truth || {}).game === "deltarune") ? "Ralsei" : "Sans";
  }
  function guidedWhereAmI() {
    var t = state.truth || {};
    if (!state.projectId) { guidedBeatCard({ type: "note", file: "no run adopted yet — watch a folder and save in-game." }); return; }
    var p = t.play_state || {};
    var bits = [p.name, t.game === "deltarune" ? "the Dark World" : ((t.route || {}).route || "undetermined")];
    if (t.game === "deltarune") {
      var dr = t.deltarune || {};
      if (dr.party) bits.push("party: " + dr.party.join(" · "));
      if (p.gold != null) bits.push(p.gold + " dark $");
      if (dr.jevil_defeated) bits.push("the jester: bested");
    } else {
      if (p.love != null) bits.push("LOVE " + p.love);
      if (p.room_name) bits.push(p.room_name);
    }
    guidedBeatCard({ type: "note", file: bits.filter(Boolean).join("  ·  ") });
  }
  function guidedWhatNow() {
    if (!state.projectId) { guidedBeatCard({ type: "note", file: "no run adopted yet — watch a folder and save in-game." }); return; }
    var level = $("g-spoiler").value || "nudge";
    try { localStorage.setItem("uv_guided_spoiler", level); } catch (e) {}
    var btn = $("g-whatnow"); btn.disabled = true;
    api("/api/projects/" + state.projectId + "/guided-hint", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: level, character: guidedSpeaker() }),
    }).then(function (res) {
      var feed = $("guided-feed");
      var card = document.createElement("div"); card.className = "g-beat g-voice";
      card.innerHTML = '<div class="g-beat-head">' + avatarMarkup(res.speaker || "?", "g-chip-img") +
        "<b>" + escHtml(res.speaker || "the guide") + "</b> <span class='muted'>· " +
        escHtml(res.where || "") + " · " + escHtml(res.level) + "</span></div><div class='g-line'></div>";
      card.querySelector(".g-line").textContent = res.text;
      feed.prepend(card);
    }).catch(function () {}).then(function () { btn.disabled = false; });
  }

  // ── The Commons: the give-back page (music downloads render live) ──────────
  function showCommons() {
    api("/api/community/music").then(function (res) {
      var box = $("cm-music"); box.innerHTML = "";
      if (!res.files || !res.files.length) {
        box.innerHTML = '<p class="muted">No music on this install yet — the tracks live outside the repo and appear here when present.</p>';
        return;
      }
      res.files.forEach(function (f) {
        var row = document.createElement("div"); row.className = "cm-track";
        var mb = (f.bytes / 1048576).toFixed(1);
        row.innerHTML = '<span class="cm-title">' + escHtml(f.title) + "</span>" +
          '<span class="muted cm-size">' + mb + " MB</span>" +
          '<a class="btn tiny" href="/audio/' + encodeURIComponent(f.file) + '" download>⤓ ' + escHtml(f.file) + "</a>";
        box.appendChild(row);
      });
    }).catch(function () {});
    showView("commons");
  }

  // ── Sound Test (interactive soundtrack: jukebox · jam · visualizer) ────────
  var _stMusicWasPlaying = false, _stRAF = null;
  function showSoundTest() {
    if (!window.SoundTest) return;
    buildSoundTest();
    if (window.MusicLayer && MusicLayer.audio) {   // hush the ambient bed while here
      _stMusicWasPlaying = !MusicLayer.audio.paused;
      if (_stMusicWasPlaying) MusicLayer.audio.pause();
    }
    showView("soundtest");
    startVisualizer();
  }
  function leaveSoundTest() {
    stopVisualizer();
    if (window.SoundTest) SoundTest.stopAll();
    syncSoundTestUI();
    if (_stMusicWasPlaying && window.MusicLayer && MusicLayer._resume) MusicLayer._resume();
    _stMusicWasPlaying = false;
  }
  function buildSoundTest() {
    var g = $("st-groups"); if (!g) return;
    g.innerHTML = "";
    var cat = SoundTest.catalog();
    g.appendChild(stGroup("Main", cat.main, "main"));
    g.appendChild(stGroup("Routes", cat.routes, "routes"));
    g.appendChild(stGroup("The Cast", cat.cast, "cast"));
    g.appendChild(stGroup("The Dark World", cat.darkbed.concat(cat.darkcast), "darkcast"));
    // the Darkners' emblems come from the Deltarune roster; cache it once for the art
    if (!state.drCharacters) {
      api("/api/characters?game=deltarune").then(function (res) {
        state.drCharacters = res.characters || [];
        var grp = document.querySelector(".st-group-darkcast .st-grid");
        if (grp) {
          grp.innerHTML = "";
          cat.darkbed.concat(cat.darkcast).forEach(function (t) { grp.appendChild(stCard(t, "darkcast")); });
          syncSoundTestUI();
        }
      }).catch(function () {});
    }
    var all = $("st-all"), none = $("st-none");
    if (all) all.onclick = function () {
      setSoundTestMode("jam");
      SoundTest.catalog().cast.forEach(function (t) { if (!SoundTest.isActive(t.id)) SoundTest.toggle(t.id); });
      syncSoundTestUI();
      miniToast("* the whole Underground plays as one.");   // secret 3
    };
    if (none) none.onclick = function () { SoundTest.stopAll(); syncSoundTestUI(); };
    var dwAll = $("st-dw-all"), dwNone = $("st-dw-none");
    if (dwAll) dwAll.onclick = function () {
      setSoundTestMode("jam");
      SoundTest.catalog().darkcast.forEach(function (t) { if (!SoundTest.isActive(t.id)) SoundTest.toggle(t.id); });
      syncSoundTestUI();
      miniToast("* the whole Dark World plays as one.");
    };
    if (dwNone) dwNone.onclick = function () {
      SoundTest.catalog().darkbed.concat(SoundTest.catalog().darkcast).forEach(function (t) {
        if (SoundTest.isActive(t.id)) SoundTest.toggle(t.id);
      });
      syncSoundTestUI();
    };
    syncSoundTestUI();
  }
  function stGroup(title, tracks, kind) {
    var sec = document.createElement("div"); sec.className = "st-group st-group-" + kind;
    var head = document.createElement("div"); head.className = "rail-lbl st-group-head"; head.textContent = title;
    if (kind === "cast") {
      var an = document.createElement("span"); an.className = "st-allnone";
      an.innerHTML = '<button class="btn tiny" id="st-all">All</button><button class="btn tiny" id="st-none">None</button>';
      head.appendChild(an);
    }
    if (kind === "darkcast") {
      var an2 = document.createElement("span"); an2.className = "st-allnone";
      an2.innerHTML = '<button class="btn tiny" id="st-dw-all">All</button><button class="btn tiny" id="st-dw-none">None</button>';
      head.appendChild(an2);
    }
    sec.appendChild(head);
    var grid = document.createElement("div"); grid.className = "st-grid";
    tracks.forEach(function (t) { grid.appendChild(stCard(t, kind)); });
    sec.appendChild(grid);
    return sec;
  }
  function stCard(t, kind) {
    var card = document.createElement("button"); card.type = "button";
    card.className = "st-card st-" + kind + (t.route ? " tln-" + t.route : "") + (t.dark ? " dw" : "");
    card.dataset.id = t.id;
    var art = (t.name)
      ? avatarMarkup(t.name, "st-card-art")
      : '<span class="soul-sigil st-card-sigil' + (t.route === "genocide" ? " determined" : "") + (t.dark ? " dark-world" : "") + '"></span>';
    card.innerHTML = art + '<span class="st-card-label">' + escHtml(t.label) + "</span>" +
      '<span class="st-card-state">▶</span>';
    card.onclick = function () { soundtestClick(t.id); };
    return card;
  }
  function soundtestClick(id) {
    if (SoundTest.mode === "jukebox") {
      if (SoundTest.isActive(id)) SoundTest.stopAll(); else SoundTest.playSolo(id);
    } else { SoundTest.toggle(id); }
    syncSoundTestUI();
  }
  function setSoundTestMode(mode) {
    if (window.SoundTest) SoundTest.mode = mode;
    $$(".st-mode").forEach(function (b) { b.classList.toggle("sel", b.dataset.mode === mode); });
  }
  function syncSoundTestUI() {
    var labels = [];
    $$(".st-card").forEach(function (c) {
      var on = window.SoundTest && SoundTest.isActive(c.dataset.id);
      c.classList.toggle("playing", !!on);
      var st = c.querySelector(".st-card-state"); if (st) st.textContent = on ? "⏸" : "▶";
      if (on) { var l = c.querySelector(".st-card-label"); if (l) labels.push(l.textContent); }
    });
    var np = $("st-np-label");
    if (np) np.textContent = labels.length
      ? labels.join("  ·  ") + (labels.length > 1 ? "   — " + labels.length + " jamming" : "")
      : "— nothing playing —";
  }
  function startVisualizer() { stopVisualizer(); drawViz(); }
  function stopVisualizer() { if (_stRAF) cancelAnimationFrame(_stRAF); _stRAF = null; }
  function drawViz() {
    _stRAF = requestAnimationFrame(drawViz);
    var canvas = $("st-canvas"); if (!canvas || !window.SoundTest) return;
    var g = canvas.getContext("2d"), W = canvas.width, H = canvas.height;
    g.clearRect(0, 0, W, H);
    var data = SoundTest.bars();
    if (data) {
      var n = data.length, bw = W / n;
      for (var i = 0; i < n; i++) {
        var v = data[i] / 255, h = v * H;
        g.fillStyle = "rgba(232,162,76," + (0.3 + 0.7 * v) + ")";
        g.fillRect(i * bw + 1, H - h, bw - 2, h);
      }
    }
    var sigil = $("st-sigil");
    if (sigil) {
      var lvl = SoundTest.level();
      sigil.style.transform = "scale(" + (1 + lvl * 0.7) + ")";
      sigil.style.filter = "brightness(" + (1 + lvl * 0.9) + ")";
    }
  }

  // ── The Timeline (the save's history, with resets marked) ──────────────────
  function showTimeline() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/save-memory").then(function (res) {
      var snaps = res.snapshots || [], track = $("timeline-track"); track.innerHTML = "";
      var peakLove = null, peakKills = null;
      snaps.forEach(function (s, i) {
        var reset = false;
        if (typeof s.love === "number") {
          if (peakLove !== null && s.love < peakLove) reset = true;
          peakLove = peakLove === null ? s.love : Math.max(peakLove, s.love);
        }
        if (typeof s.total_kills === "number") {
          if (peakKills !== null && s.total_kills < peakKills) reset = true;
          peakKills = peakKills === null ? s.total_kills : Math.max(peakKills, s.total_kills);
        }
        if (i > 0) {
          var conn = document.createElement("div");
          conn.className = "tl-conn" + (reset ? " reset" : "");
          conn.textContent = reset ? "↩" : "→"; track.appendChild(conn);
        }
        var route = (s.route || "undetermined").toLowerCase();
        var node = document.createElement("div");
        node.className = "tl-node tln-" + route + (i === snaps.length - 1 ? " current" : "");
        node.innerHTML = '<div class="tl-visit">reading #' + s.counter + "</div>" +
          '<span class="route-badge ' + route + '">' + (s.route || "undetermined") + "</span>" +
          '<div class="muted tl-meta">LV ' + (s.love == null ? "—" : s.love) +
          " · " + (s.total_kills == null ? "—" : s.total_kills) + " kills</div>";
        track.appendChild(node);
      });
      if (!snaps.length) track.innerHTML = '<p class="muted">No readings yet.</p>';
      showView("timeline");
    });
  }

  // ── The Council (the whole Underground reacts at once) ─────────────────────
  function showCouncil() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/council").then(function (res) {
      var box = $("council-list"); box.innerHTML = "";
      var route = ((state.truth || {}).route || {}).route;
      var intro = document.createElement("p"); intro.className = "council-intro muted";
      intro.textContent = (route && route !== "undetermined")
        ? "The whole Underground reacts to your " + route + " run — grief and anger speak loudest."
        : "The whole Underground reacts to your run.";
      box.appendChild(intro);
      (res.council || []).forEach(function (e, i) {
        var sc = STANCE_CLASS[e.stance] || "free";
        var row = document.createElement("div");
        row.className = "council-voice cv-" + sc;
        row.style.animationDelay = (i * 55) + "ms";
        row.innerHTML =
          '<button class="cv-face" type="button" title="Hear ' + escHtml(e.character) + '">' +
            avatarMarkup(e.character, "bubble-avatar") + "</button>" +
          '<div class="cv-body"><div class="cv-head">' + escHtml(e.character) +
          ' <span class="chip ' + sc + '">' + e.stance + "</span>" +
          '<button class="cv-talk" type="button">💬 talk</button></div>' +
          '<div class="cv-line"></div></div>';
        row.querySelector(".cv-line").textContent = e.line;
        row.querySelector(".cv-face").onclick = function () {
          if (window.VoiceLayer) window.VoiceLayer.preview(e.character);
        };
        row.querySelector(".cv-talk").onclick = function () {
          var c = charByName(e.character); if (c) selectCharacter(c);
        };
        box.appendChild(row);
      });
      showView("council");
    });
  }

  // ── Proactive contact (they reach out to you) ──────────────────────────────
  // Opt-in and persisted as a cadence: Muted / Rarely / Sometimes / Often. Once
  // you've turned it on at least once, a quick cadence control appears in the rail
  // so you can dial it down or mute entirely without reopening the explainer.
  var reachTimer = null;
  var REACH_MS = { rare: 300000, normal: 180000, often: 90000 };   // base gap per cadence
  var REACH_LABEL = { off: "Off", rare: "Rarely", normal: "Sometimes", often: "Often" };
  function reachFreq() {
    try {
      var f = localStorage.getItem("uv_reach_freq");
      if (f) return f;
      if (localStorage.getItem("uv_reachout") === "1") return "normal";  // migrate old on/off pref
    } catch (e) {}
    return "off";
  }
  function reachOn() { return reachFreq() !== "off"; }
  function reachSeen() {
    try { return localStorage.getItem("uv_reach_seen") === "1" || localStorage.getItem("uv_reachout") === "1"; }
    catch (e) { return false; }
  }
  function writeReachFreq(freq) {
    try {
      localStorage.setItem("uv_reach_freq", freq);
      if (freq !== "off") localStorage.setItem("uv_reach_seen", "1");
    } catch (e) {}
  }
  function stopReachTimer() { if (reachTimer) { clearTimeout(reachTimer); reachTimer = null; } }
  function reachInterval() {
    var base = REACH_MS[reachFreq()] || REACH_MS.normal;
    return Math.round(base * (0.7 + Math.random() * 0.6));   // ±30% jitter so it never feels clockwork
  }
  function scheduleReach() {
    reachTimer = setTimeout(function () { reachOutNow(); scheduleReach(); }, reachInterval());
  }
  function startReachTimer(immediate) {
    if (reachTimer || !reachOn() || !state.projectId) return;
    if (immediate) reachOutNow();
    scheduleReach();
  }
  // modal yes/no — a fresh yes breaks the silence right away
  function setReachOut(on) {
    writeReachFreq(on ? "normal" : "off");
    syncReachCta(); stopReachTimer();
    if (on) startReachTimer(true);
  }
  // quick cadence control (incl. Muted) — re-cadence only, no immediate hello
  function setReachFreq(freq) {
    writeReachFreq(freq);
    syncReachCta(); stopReachTimer();
    if (reachOn()) startReachTimer(false);
  }
  function syncReachCta() {
    var freq = reachFreq();
    var cta = $("reach-cta"); if (cta) cta.classList.toggle("on", freq !== "off");
    var st = $("reach-cta-state"); if (st) st.textContent = REACH_LABEL[freq] || "Off";
    var row = $("reach-freq-row"); if (row) row.classList.toggle("hidden", !reachSeen());
    var sel = $("reach-freq"); if (sel) sel.value = freq;
  }
  function openReachModal() { $("reach-modal").classList.remove("hidden"); trapFocus($("reach-modal")); }
  function closeReachModal() { $("reach-modal").classList.add("hidden"); releaseFocus($("reach-modal")); }
  function reachOutNow() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/reach-out", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
    }).then(function (res) { showReachToast(res.character, res.message); }).catch(function () {});
  }
  function showReachToast(character, message) {
    var t = $("reach-toast");
    t.innerHTML = "<strong>" + character + "</strong> reached out — <em>tap to answer</em><br/><span></span>";
    var parsed = parseEmphasis(message);   // strip *markers*, shake the emphatic word
    applyShake(t.querySelector("span"), parsed.text, parsed.spans);
    t.classList.remove("hidden");
    t.onclick = function () { t.classList.add("hidden"); openCharacter(character); };
    clearTimeout(t._timer);
    t._timer = setTimeout(function () { t.classList.add("hidden"); }, 14000);
  }

  // ── Options menu (response dials + HUD density; persisted) ─────────────────
  var SETTINGS_DEFAULT = {
    options: { verbosity: "normal", intensity: "normal", lore: "normal", meta: "subtle" },
    hud: { provenance: true, affinity: true, remembrance: true, motion: true, typewriterMs: 18, blip: true },
  };
  function loadSettings() {
    try {
      var saved = JSON.parse(localStorage.getItem("uv_settings") || "{}");
      return {
        options: Object.assign({}, SETTINGS_DEFAULT.options, saved.options || {}),
        hud: Object.assign({}, SETTINGS_DEFAULT.hud, saved.hud || {}),
      };
    } catch (e) { return JSON.parse(JSON.stringify(SETTINGS_DEFAULT)); }
  }
  function applyHud() {
    var h = state.settings.hud, b = document.body;
    b.classList.toggle("hud-no-provenance", !h.provenance);
    b.classList.toggle("hud-no-affinity", !h.affinity);
    b.classList.toggle("hud-no-remembrance", !h.remembrance);
    b.classList.toggle("hud-no-motion", !h.motion);
  }
  function syncSettingsControls() {
    var o = state.settings.options, h = state.settings.hud;
    $("opt-verbosity").value = o.verbosity; $("opt-intensity").value = o.intensity;
    $("opt-lore").value = o.lore; $("opt-meta").value = o.meta;
    $("hud-provenance").checked = h.provenance; $("hud-affinity").checked = h.affinity;
    $("hud-remembrance").checked = h.remembrance; $("hud-motion").checked = h.motion;
    $("hud-typewriter").value = String(h.typewriterMs);
    $("hud-blip").checked = h.blip;
  }
  function readSettingsControls() {
    state.settings.options = {
      verbosity: $("opt-verbosity").value, intensity: $("opt-intensity").value,
      lore: $("opt-lore").value, meta: $("opt-meta").value,
    };
    state.settings.hud = {
      provenance: $("hud-provenance").checked, affinity: $("hud-affinity").checked,
      remembrance: $("hud-remembrance").checked, motion: $("hud-motion").checked,
      typewriterMs: parseInt($("hud-typewriter").value, 10) || 0,
      blip: $("hud-blip").checked,
    };
    try { localStorage.setItem("uv_settings", JSON.stringify(state.settings)); } catch (e) {}
    applyHud();
    loadRecognition();  // the "Save/reset talk" dial gates the recognition beat
  }

  // mobile bottom nav: Chat (stage) · Cast (left drawer) · Save (right drawer)
  function bottomNav(which) {
    $$("#bottom-nav .bn").forEach(function (b) {
      b.classList.toggle("sel", b.getAttribute("data-nav") === which);
    });
    if (which === "cast") { openDrawer("left"); }
    else if (which === "save") { openDrawer("right"); }
    else { showView("chat"); }
  }

  window.addEventListener("DOMContentLoaded", function () {
    state.settings = loadSettings();
    AudioBus.load();   // load the master volume/mute before any audio inits
    syncSettingsControls();
    applyHud();
    if (window.MusicLayer) {
      window.MusicLayer.init();
      var mtog = $("music-toggle");
      if (mtog) {
        mtog.checked = window.MusicLayer.isEnabled();
        // If music is on (default), auto-play the theme now (autoplay-block → resumes on first tap).
        if (mtog.checked) window.MusicLayer.startMenu();
      }
    }

    // options drawer
    $("settings-btn").onclick = function () { $("settings-panel").classList.toggle("hidden"); };
    $("settings-close").onclick = function () { $("settings-panel").classList.add("hidden"); };
    $("settings-panel").addEventListener("change", readSettingsControls);

    // view router: left-rail nav + any [data-view] control
    $$("[data-view]").forEach(function (b) {
      b.onclick = function () { navTo(b.getAttribute("data-view")); };
    });
    // mobile bottom nav + drawer scrim + save pill
    $$("#bottom-nav .bn").forEach(function (b) {
      b.onclick = function () { bottomNav(b.getAttribute("data-nav")); };
    });
    $("scrim").onclick = closeDrawers;
    $("chat-hero-menu").onclick = function () { openDrawer("left"); };   // escape chat → features
    // secret 1 — tap the soul: escalating whispers, then a DETERMINATION burst
    var emberTaps = 0, emberTimer = null, sig = $("header-sigil");
    if (sig) {
      sig.style.cursor = "pointer";
      sig.onclick = function () {
        clearTimeout(emberTimer); emberTimer = setTimeout(function () { emberTaps = 0; }, 1600);
        var gen = (((state.truth || {}).route || {}).route === "Genocide");
        switch (++emberTaps) {
          case 5: miniToast(gen ? "* file0 — it remembers what you did." : "* file0 — the save still remembers you."); break;
          case 10: miniToast("* ...you're still tapping."); break;
          case 15: miniToast(gen ? "* stop." : "* okay, you're clearly determined."); break;
          case 20: emberTaps = 0; determinationBurst(); break;
        }
      };
    }
    // secret 2 — the Konami code on a keyboard (PC), anywhere → a DETERMINATION burst
    var KONAMI = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"], kpos = 0;
    document.addEventListener("keydown", function (e) {
      var k = (e.key || "").length === 1 ? e.key.toLowerCase() : e.key;
      if (k === KONAMI[kpos]) {
        kpos++;
        // once you're clearly entering the code, stop the arrows scrolling/moving focus
        if (kpos >= 2 && k.indexOf("Arrow") === 0) e.preventDefault();
        if (kpos === KONAMI.length) { kpos = 0; determinationBurst("* The Underground bends to your DETERMINATION."); }
      } else {
        kpos = (k === KONAMI[0]) ? 1 : 0;
      }
    });
    // secret — the corner code (works on touch): tap the four corners clockwise
    var corners = [], cornerT = null, SEQ = "TL,TR,BR,BL";
    document.addEventListener("pointerdown", function (e) {
      var x = e.clientX, y = e.clientY, W = innerWidth, H = innerHeight, m = 72;
      var c = (x < m && y < m) ? "TL" : (x > W - m && y < m) ? "TR" :
              (x > W - m && y > H - m) ? "BR" : (x < m && y > H - m) ? "BL" : null;
      if (!c) return;
      clearTimeout(cornerT); cornerT = setTimeout(function () { corners = []; }, 3000);
      corners.push(c); if (corners.length > 4) corners.shift();
      if (corners.join() === SEQ) { corners = []; determinationBurst("* the corners of the world fold inward."); }
    });
    // secret — rapid-tap a character's portrait in the chat banner → they react
    var emoteTaps = 0, emoteT = null;
    $("chat-hero").addEventListener("click", function (e) {
      var port = e.target.closest && e.target.closest(".relic-portrait");
      if (!port || !state.character) return;
      clearTimeout(emoteT); emoteT = setTimeout(function () { emoteTaps = 0; }, 1200);
      if (++emoteTaps >= 5) {
        emoteTaps = 0;
        miniToast(EMOTES[state.character] || "* ...?");
        if (window.VoiceLayer) window.VoiceLayer.preview(state.character);
        port.classList.remove("emote-bounce"); void port.offsetWidth; port.classList.add("emote-bounce");
      }
    });
    $("save-pill").onclick = function () { openDrawer("left"); };
    $("modes-btn").onclick = function (e) {
      e.stopPropagation();
      if ($("modes-menu")) closeModesMenu(); else openModesMenu(this);
    };
    // global audio master (volume + mute) — every layer reads AudioBus.gain()
    AudioBus.onChange(function () {
      if (window.MusicLayer && MusicLayer.applyMaster) MusicLayer.applyMaster();
      if (window.SoundTest && SoundTest.applyMaster) SoundTest.applyMaster();
    });
    updateAudioBtn();
    $("audio-btn").onclick = function (e) {
      e.stopPropagation();
      if ($("audio-menu")) closeAudioMenu(); else openAudioMenu(this);
    };
    $("add-save-btn").onclick = function () { showView("saves"); };

    // save read / refresh
    $("upload-btn").onclick = uploadSave;
    $("refresh-btn").onclick = refreshSave;

    // chat
    $("send-btn").onclick = sendMessage;
    $("chat-input").addEventListener("keydown", function (e) { if (e.key === "Enter") sendMessage(); });

    // per-view actions
    $("speak-btn").onclick = speakJudgment;
    $("chronicle-download-btn").onclick = downloadChronicle;
    $("journal-inscribe-btn").onclick = inscribeJournal;
    $("journal-download-btn").onclick = function () { if (state.journalMd) downloadText(state.journalMd, "keepsake_journal.md"); };
    $("report-request-btn").onclick = requestReport;
    $("report-full-btn").onclick = fullReport;
    $("report-download-btn").onclick = downloadReports;
    $("report-digest-btn").onclick = emailDigest;
    $("report-filter").onchange = loadReports;
    $("report-archived-toggle").onchange = loadReports;
    $("div-ask").onclick = askDivergence;
    $("guided-watch-btn").onclick = guidedWatch;
    $("guided-stop-btn").onclick = guidedStop;
    $("g-whereami").onclick = guidedWhereAmI;
    $("guided-popout-btn").onclick = guidedPopout;
    $("g-story").onclick = guidedStory;
    $("cm-zip").onclick = function () { location.href = "/api/community/music.zip"; };
    // the power source (ladder) controls
    $("vision-btn").onclick = function () { $("settings-panel").classList.add("hidden"); openVisionModal(); };
    $("vision-close").onclick = closeVisionModal;
    $("vision-modal").addEventListener("click", function (e) { if (e.target === $("vision-modal")) closeVisionModal(); });
    $$("#vision-modal [data-a11y]").forEach(function (c) {
      c.addEventListener("change", function () { a11yToggle(c.dataset.a11y, c.checked); });
    });
    $("power-btn").onclick = function () { $("settings-panel").classList.add("hidden"); openPowerModal(); };
    $("power-cancel").onclick = closePowerModal;
    $("power-save").onclick = savePower;
    $$(".power-card").forEach(function (c) {
      c.onclick = function () {
        _powerSel = c.dataset.source;
        $$(".power-card").forEach(function (x) { x.classList.toggle("sel", x === c); });
        $("power-or").classList.toggle("hidden", _powerSel !== "openrouter");
      };
    });
    $("power-model").onchange = function () {
      $("power-model-custom").classList.toggle("hidden", this.value !== "__custom__");
    };
    $("power-modal").addEventListener("click", function (e) { if (e.target === this) closePowerModal(); });
    refreshPowerChip();
    $("g-whatnow").onclick = guidedWhatNow;
    try { var sp = localStorage.getItem("uv_guided_spoiler"); if (sp) $("g-spoiler").value = sp; } catch (e) {}
    // Sound Test controls
    $$(".st-mode").forEach(function (b) { b.onclick = function () { setSoundTestMode(b.dataset.mode); }; });
    $("st-stop").onclick = function () { if (window.SoundTest) SoundTest.stopAll(); syncSoundTestUI(); };
    $("st-vol").oninput = function () { if (window.SoundTest) SoundTest.setMasterVolume(this.value / 100); };
    $("st-loop").onchange = function () { if (window.SoundTest) SoundTest.setLoop(this.checked); };

    // "let them reach out" — CTA opens an explainer modal with the yes/no choice
    syncReachCta();
    $("reach-cta").onclick = openReachModal;
    $("reach-yes").onclick = function () { setReachOut(true); closeReachModal(); };
    $("reach-no").onclick = function () { setReachOut(false); closeReachModal(); };
    $("reach-freq").onchange = function () { setReachFreq(this.value); };
    $("reach-modal").addEventListener("click", function (e) { if (e.target === this) closeReachModal(); });
    $("feature-modal-ok").onclick = closeFeatureModal;
    $("feature-modal").addEventListener("click", function (e) { if (e.target === this) closeFeatureModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape") return;
      if ($("modes-menu")) closeModesMenu();
      if ($("audio-menu")) closeAudioMenu();
      if (!$("reach-modal").classList.contains("hidden")) closeReachModal();
      if (!$("feature-modal").classList.contains("hidden")) closeFeatureModal();
      if (!$("power-modal").classList.contains("hidden")) closePowerModal();
      if (!$("vision-modal").classList.contains("hidden")) closeVisionModal();
    });

    // ambient music toggle
    $("music-toggle").onchange = function () {
      if (!window.MusicLayer) return;
      window.MusicLayer.setEnabled(this.checked);
    };

    renderQuote();
    $("quote-refresh").onclick = nextQuote;
    renderLore();
    // secret 4 — spam the lore ↻ and a hidden page turns
    var loreSpam = 0, loreSpamT = null;
    $("lore-refresh").onclick = function () {
      nextLore();
      clearTimeout(loreSpamT); loreSpamT = setTimeout(function () { loreSpam = 0; }, 2200);
      if (++loreSpam >= 7) {
        loreSpam = 0;
        var el = $("lore-text"); if (el) el.textContent = "It was never just a save file. It was reading you back.";
        miniToast("* a hidden page turns.");
      }
    };

    document.body.classList.add("on-chat");
    loadShelf();
    loadRoster();          // meet the cast right away (voices previewable before a save)
    renderTranscript();   // chat starts with the welcome (cast row fills once loaded)
  });
})();
