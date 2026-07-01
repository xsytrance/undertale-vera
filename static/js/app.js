/* ════════════════════════════════════════════════════════════════════════
   undertale-vera frontend — vanilla JS, no build step.
   Drives the Spine-0 backend: upload -> SaveTruth -> roster -> grounded chat ->
   the remembrance ledger -> the Judgment beat. Reuses the Determination
   Chronicle CSS. Route-aware music binds to the live SaveTruth route.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var state = { projectId: null, character: null, characters: [], history: {}, view: "chat" };

  function $(id) { return document.getElementById(id); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  // ── the view router ───────────────────────────────────────────────────────
  // Exactly one stage view is .active at a time. Switching a character or a
  // feature swaps the stage only — the rails never move, nothing scrolls away.
  var VIEWS = ["chat", "council", "timeline", "journal", "constellation", "chronicle", "judgment", "reports", "saves"];

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
  var _quoteIdx = null;
  function quoteOfDay() {
    if (_quoteIdx === null) {
      var d = new Date();
      _quoteIdx = (d.getFullYear() * 372 + d.getMonth() * 31 + d.getDate()) % APHORISMS.length;
    }
    return APHORISMS[_quoteIdx];
  }
  function renderQuote() {
    var el = $("quote-text"); if (el) el.textContent = "“" + quoteOfDay() + "”";
  }
  function nextQuote() {
    _quoteIdx = ((_quoteIdx === null ? 0 : _quoteIdx) + 1) % APHORISMS.length;
    renderQuote();
  }
  function showView(name) {
    state.view = name;
    VIEWS.forEach(function (v) {
      var el = $("view-" + v); if (el) el.classList.toggle("active", v === name);
    });
    $$("[data-view]").forEach(function (b) {
      b.classList.toggle("sel", b.getAttribute("data-view") === name);
    });
    document.body.classList.toggle("on-chat", name === "chat");
    closeDrawers();
    var st = $("stage"); if (st) st.scrollTop = 0;
  }

  // nav button → fetch+render the feature, then reveal its view (or just switch)
  function navTo(name) {
    switch (name) {
      case "council": return showCouncil();
      case "timeline": return showTimeline();
      case "journal": return showJournal();
      case "constellation": return showConstellation();
      case "chronicle": return showChronicle();
      case "judgment": return showJudgment();
      case "reports": return showReports();
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
    if (f0) fd.append("file0", f0, "file0");
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

    function fmt(v) { return (v === null || v === undefined || v === "") ? "—" : v; }
    $("truth-facts").innerHTML =
      row("Name", fmt(play.name)) +
      row("LOVE (LV)", fmt(play.love)) +
      row("Kills", kills === null || kills === undefined ? "—" : kills) +
      row("Room", fmt(play.room_name));

    var badge = $("route-badge");
    badge.className = "route-badge " + route.toLowerCase();
    badge.innerHTML = '<span class="soul-sigil ' + (route === "Genocide" ? "determined" : "") +
      '" style="width:14px;height:14px;"></span> route: ' + route + " (" + conf + ")";

    $("visit-label").textContent = visit ? ("· visit #" + visit) : "";
    var rbox = $("remembrance-box");
    if (remembrance) { rbox.textContent = remembrance; rbox.classList.remove("hidden"); }
    else { rbox.classList.add("hidden"); }

    // reflect the current save in the top-bar pill
    var pill = $("save-pill");
    if (pill) pill.textContent = (fmt(play.name) === "—" ? "Save" : play.name) + " · " + route + " ▾";

    // route-aware music: drive the bed from the live route (if enabled).
    if (window.MusicLayer && $("music-toggle").checked) window.MusicLayer.setRoute(route);
    // route-reactive backdrop: tint (always) + generated scene art (when present).
    if (window.SceneLayer) window.SceneLayer.setRoute(route);
    // tint the header sigil red on the Genocide beat.
    $("header-sigil").className = "soul-sigil" + (route === "Genocide" ? " determined" : "");
    // Genocide feel: destabilise the dialogue (root class) + one blood-red flash
    // fired only when the route first resolves to Genocide, not on every render.
    document.body.classList.toggle("route-genocide", route === "Genocide");
    if (route === "Genocide" && state.lastRoute !== "Genocide") flashGenocide();
    state.lastRoute = route;
    // if "let them reach out" is on, resume the proactive timer now a save is live
    startReachTimer(false);
    // New Game+: does anything here know you from another save you've shown?
    loadRecognition();
  }
  function row(k, v) { return '<div class="k">' + k + "</div><div>" + v + "</div>"; }

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
        card.innerHTML =
          '<span class="save-sigil soul-sigil' + (gen ? " determined" : "") + '" aria-hidden="true"></span>' +
          '<span class="save-body">' +
            '<span class="save-head">' +
              '<span class="save-name">' + escHtml(p.name || ("Save #" + p.project_id)) + "</span>" +
              '<span class="route-badge ' + route.toLowerCase() + '">' + route + "</span>" +
            "</span>" +
            '<span class="save-meta">LV ' + lv + (when ? " · " + when : "") + "</span>" +
          "</span>";
        card.onclick = function () { loadProject(p.project_id); };
        el.appendChild(card);
      });
      if (!res.projects || !res.projects.length) {
        el.innerHTML = '<p class="muted" style="font-size:.78rem;">No saves yet.</p>';
      }
      // "Across Your Saves" only means something once there's more than one save.
      var navC = $("nav-constellation");
      if (navC) navC.classList.toggle("hidden", (res.projects || []).length < 2);
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
      showView("constellation");
    });
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
    var l = state.characters || [];
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
    api("/api/characters").then(function (res) {
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
  }

  // a brief, tappable nudge (reuses the reach-toast surface)
  function miniToast(msg) {
    var t = $("reach-toast"); if (!t) return;
    t.innerHTML = ""; t.textContent = msg;
    t.classList.remove("hidden");
    t.onclick = function () { t.classList.add("hidden"); };
    clearTimeout(t._timer); t._timer = setTimeout(function () { t.classList.add("hidden"); }, 3800);
  }
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
    var a = (state.affinities || {})[c.name];
    $("chat-name").innerHTML = c.name + (a
      ? ' <span class="chip ' + (STANCE_CLASS[a.stance] || "free") + '" title="' + a.basis +
        '" style="font-size:0.64rem; vertical-align:middle;">regards you: ' + a.stance + "</span>"
      : "");
    var p = $("chat-portrait");
    if (p) p.outerHTML = avatarMarkup(c.name, "relic-portrait", "chat-portrait");
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

  function renderTranscript() {
    var t = $("transcript"); t.innerHTML = "";
    // once a speaker is chosen, mobile chat goes immersive (chrome slides away)
    document.body.classList.toggle("chatting", !!state.character);
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
        (state.projectId ? "Pick someone to talk to." : "Read a save to begin — or tap a face to hear their voice.") +
        "</p>" +
        (cast.length ? '<div class="chat-empty-cast">' + castHtml + "</div>" : "") +
        '<p class="chat-empty-quote">“' + quoteOfDay() + '”</p></div>';
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
      span.textContent = text.slice(0, ++i);
      if (i % every === 0 && /\S/.test(text.charAt(i - 1))) blip(name);   // a blip every few glyphs
      scrollChatToBottom();   // follow the reply as it types (unless you've scrolled up)
      if (i >= text.length) { clearInterval(timer); applyShake(span, text, parsed.spans); dialogueDone(span, name); }
    }, ms);
  }

  function sendMessage() {
    var input = $("chat-input"); var msg = input.value.trim();
    if (!msg || !state.projectId || !state.character) return;
    var hist = state.history[state.character];
    hist.push({ role: "user", content: msg });
    renderTranscript(); input.value = "";
    var body = { character: state.character, message: msg, history: hist.slice(0, -1),
                 options: (state.settings || {}).options };
    api("/api/projects/" + state.projectId + "/chat", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(function (res) {
      hist.push({ role: "assistant", content: res.response });
      renderTranscript();
      var row = $("transcript").lastChild;                 // the .msg row
      var bubble = row.querySelector(".bubble") || row;     // provenance rides the bubble
      renderProvenance(bubble, res);   // the wall, made visible (before the arrow)
      scrollChatToBottom(true);        // pin to the reply before it starts typing
      typewriter(bubble.querySelector("span"), res.response, state.character);
    }).catch(function (e) {
      hist.push({ role: "assistant", content: "(error: " + e.message + ")" });
      renderTranscript();
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
    if (!list.length) {
      box.innerHTML = '<p class="muted">' +
        (archived ? "No archived reports." : "No reports yet — ask someone to file one on your run.") + "</p>";
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
        var node = document.createElement("div"); node.className = "tl-node";
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
      (res.council || []).forEach(function (e) {
        var row = document.createElement("div");
        row.className = "council-voice";
        row.innerHTML =
          avatarMarkup(e.character, "bubble-avatar") +
          '<div class="cv-body"><div class="cv-head">' + e.character +
          ' <span class="chip ' + (STANCE_CLASS[e.stance] || "free") + '">' + e.stance + "</span></div>" +
          '<div class="cv-line"></div></div>';
        row.querySelector(".cv-line").textContent = e.line;
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
  function openReachModal() { $("reach-modal").classList.remove("hidden"); }
  function closeReachModal() { $("reach-modal").classList.add("hidden"); }
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
    $("save-pill").onclick = function () { openDrawer("left"); };
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
    $("report-filter").onchange = loadReports;
    $("report-archived-toggle").onchange = loadReports;

    // "let them reach out" — CTA opens an explainer modal with the yes/no choice
    syncReachCta();
    $("reach-cta").onclick = openReachModal;
    $("reach-yes").onclick = function () { setReachOut(true); closeReachModal(); };
    $("reach-no").onclick = function () { setReachOut(false); closeReachModal(); };
    $("reach-freq").onchange = function () { setReachFreq(this.value); };
    $("reach-modal").addEventListener("click", function (e) { if (e.target === this) closeReachModal(); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !$("reach-modal").classList.contains("hidden")) closeReachModal();
    });

    // ambient music toggle
    $("music-toggle").onchange = function () {
      if (!window.MusicLayer) return;
      window.MusicLayer.setEnabled(this.checked);
    };

    renderQuote();
    $("quote-refresh").onclick = nextQuote;

    document.body.classList.add("on-chat");
    loadShelf();
    loadRoster();          // meet the cast right away (voices previewable before a save)
    renderTranscript();   // chat starts with the welcome (cast row fills once loaded)
  });
})();
