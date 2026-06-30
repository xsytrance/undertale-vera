/* ════════════════════════════════════════════════════════════════════════
   undertale-vera frontend — vanilla JS, no build step.
   Drives the Spine-0 backend: upload -> SaveTruth -> roster -> grounded chat ->
   the remembrance ledger -> the Judgment beat. Reuses the Determination
   Chronicle CSS. Route-aware music binds to the live SaveTruth route.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var state = { projectId: null, character: null, characters: [], history: {} };

  function $(id) { return document.getElementById(id); }

  function api(path, opts) {
    return fetch(path, opts).then(function (r) {
      return r.json().then(function (body) {
        if (!r.ok) throw new Error(body.detail || ("HTTP " + r.status));
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
        $("refresh-btn").classList.remove("hidden");
        $("upload-status").textContent = "Save read. Project #" + res.project_id + ".";
        renderTruth(res.save_truth, null, "");
        loadRoster();
        loadShelf();
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
      })
      .catch(function (e) { $("upload-status").textContent = "Error: " + e.message; });
  }

  // ── SaveTruth summary + route-aware music ────────────────────────────────
  function renderTruth(truth, visit, remembrance) {
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

    $("truth-panel").classList.remove("hidden");

    // route-aware music: drive the bed from the live route (if enabled).
    if (window.MusicLayer && $("music-toggle").checked) window.MusicLayer.setRoute(route);
    // route-reactive backdrop: tint (always) + generated scene art (when present).
    if (window.SceneLayer) window.SceneLayer.setRoute(route);
    // tint the header sigil red on the Genocide beat.
    $("header-sigil").className = "soul-sigil" + (route === "Genocide" ? " determined" : "");
  }
  function row(k, v) { return '<div class="k">' + k + "</div><div>" + v + "</div>"; }

  // ── save shelf (switch between read saves) ───────────────────────────────
  function loadShelf() {
    api("/api/projects").then(function (res) {
      var el = $("shelf"); el.innerHTML = "";
      if (!res.projects.length) { $("shelf-panel").classList.add("hidden"); return; }
      res.projects.forEach(function (p) {
        var route = p.route || "undetermined";
        var card = document.createElement("div");
        card.className = "char-card";
        card.style.width = "150px";
        card.innerHTML =
          '<div class="name">' + (p.name || "Save #" + p.project_id) + "</div>" +
          '<span class="route-badge ' + route.toLowerCase() + '" style="font-size:0.72rem;">' +
          route + "</span>";
        card.onclick = function () { loadProject(p.project_id); };
        el.appendChild(card);
      });
      $("shelf-panel").classList.remove("hidden");
    });
  }

  function loadProject(id) {
    api("/api/projects/" + id + "/save-truth").then(function (res) {
      state.projectId = id;
      state.history = {};
      state.character = null;
      $("refresh-btn").classList.remove("hidden");
      $("chat-panel").classList.add("hidden");
      $("judgment-panel").classList.add("hidden");
      renderTruth(res.save_truth, null, "");
      loadRoster();
    });
  }

  // ── roster ────────────────────────────────────────────────────────────────
  // stance → CSS class for the affinity chip colour
  var STANCE_CLASS = { warm: "ok", wary: "free", grieving: "warn", hostile: "warn", unreadable: "free" };

  function loadRoster() {
    api("/api/characters").then(function (res) {
      state.characters = res.characters;
      var el = $("roster"); el.innerHTML = "";
      res.characters.forEach(function (c) {
        var card = document.createElement("div");
        card.className = "char-card";
        card.dataset.name = c.name;
        var portrait = c.avatar_url
          ? '<img class="relic-portrait" src="' + c.avatar_url + '" alt="' + c.name + '" />'
          : '<div class="relic-portrait empty"></div>';
        card.innerHTML = portrait + '<div class="name">' + c.name + "</div>" +
          '<div class="affinity" data-for="' + c.name + '"></div>';
        card.onclick = function () { selectCharacter(c); };
        el.appendChild(card);
      });
      $("roster-panel").classList.remove("hidden");
      loadAffinities();   // decorate cards with how each regards you
    });
  }

  // How the Underground regards you — a stance chip per roster card (SACRED-derived).
  function loadAffinities() {
    if (!state.projectId) return;
    api("/api/projects/" + state.projectId + "/affinities").then(function (res) {
      var aff = res.affinities || {};
      Array.prototype.forEach.call(document.querySelectorAll("#roster .affinity"), function (slot) {
        var a = aff[slot.dataset.for];
        if (!a) { slot.innerHTML = ""; return; }
        slot.innerHTML = '<span class="chip ' + (STANCE_CLASS[a.stance] || "free") +
          '" title="' + a.basis + '">' + a.stance + "</span>";
      });
    }).catch(function () {});
  }

  function selectCharacter(c) {
    state.character = c.name;
    if (!state.history[c.name]) state.history[c.name] = [];
    Array.prototype.forEach.call(document.querySelectorAll("#roster .char-card"), function (el) {
      el.classList.toggle("selected", el.dataset.name === c.name);
    });
    $("chat-name").textContent = c.name;
    var p = $("chat-portrait");
    if (c.avatar_url) { p.outerHTML = '<img class="relic-portrait" id="chat-portrait" src="' + c.avatar_url + '" />'; }
    $("chat-panel").classList.remove("hidden");
    $("judgment-panel").classList.add("hidden");
    // Load the persisted transcript so the conversation survives a reload.
    api("/api/projects/" + state.projectId + "/conversations/" + c.name.toLowerCase())
      .then(function (res) {
        state.history[c.name] = (res.messages || []).map(function (m) {
          return { role: m.role, content: m.content };
        });
        renderTranscript();
      })
      .catch(function () { renderTranscript(); });
  }

  // ── chat ──────────────────────────────────────────────────────────────────
  function avatarFor(name) {
    var list = state.characters || [];
    for (var i = 0; i < list.length; i++) {
      if (list[i].name === name) return list[i].avatar_url || "";
    }
    return "";
  }

  function renderTranscript() {
    var t = $("transcript"); t.innerHTML = "";
    (state.history[state.character] || []).forEach(function (m) {
      var them = m.role !== "user";
      var msg = document.createElement("div");
      msg.className = "msg " + (them ? "them" : "you");

      // the speaker's portrait sits beside their reply (crest until art lands)
      if (them) {
        var av = avatarFor(state.character);
        var avEl = document.createElement(av ? "img" : "div");
        avEl.className = "bubble-avatar" + (av ? "" : " empty");
        if (av) { avEl.src = av; avEl.alt = state.character; }
        msg.appendChild(avEl);
      }

      var b = document.createElement("div");
      b.className = "bubble " + (them ? "them" : "you");
      var who = document.createElement("div");
      who.className = "who"; who.textContent = them ? state.character : "you";
      var span = document.createElement("span");
      span.textContent = m.content;
      b.appendChild(who); b.appendChild(span);
      msg.appendChild(b);
      t.appendChild(msg);
    });
  }

  function typewriter(span, text) {
    span.textContent = ""; span.parentNode.classList.add("ink-reveal");
    var i = 0;
    var timer = setInterval(function () {
      span.textContent = text.slice(0, ++i);
      if (i >= text.length) { clearInterval(timer); span.parentNode.classList.remove("ink-reveal"); }
    }, 18);
  }

  function sendMessage() {
    var input = $("chat-input"); var msg = input.value.trim();
    if (!msg || !state.projectId || !state.character) return;
    var hist = state.history[state.character];
    hist.push({ role: "user", content: msg });
    renderTranscript(); input.value = "";
    var body = { character: state.character, message: msg, history: hist.slice(0, -1) };
    api("/api/projects/" + state.projectId + "/chat", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }).then(function (res) {
      hist.push({ role: "assistant", content: res.response });
      renderTranscript();
      var row = $("transcript").lastChild;                 // the .msg row
      var bubble = row.querySelector(".bubble") || row;     // provenance rides the bubble
      typewriter(bubble.querySelector("span"), res.response);
      renderProvenance(bubble, res);   // the wall, made visible
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
    box.className = "provenance";
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
    // the guard verdict
    if (res.guard && res.guard.clean === false) {
      box.appendChild(chip("warn", "⚠ contradicts save (" + res.guard.issues.length + ")"));
    } else {
      box.appendChild(chip("ok", "✓ grounded"));
    }
    bubble.appendChild(box);
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
      $("judgment-panel").classList.remove("hidden");
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
      typewriter(span, res.spoken);
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
      $("chronicle-panel").classList.remove("hidden");
      $("chronicle-panel").scrollIntoView({ behavior: "smooth", block: "start" });
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

  window.addEventListener("DOMContentLoaded", function () {
    if (window.MusicLayer) window.MusicLayer.init();
    loadShelf();
    $("upload-btn").onclick = uploadSave;
    $("refresh-btn").onclick = refreshSave;
    $("send-btn").onclick = sendMessage;
    $("chat-input").addEventListener("keydown", function (e) { if (e.key === "Enter") sendMessage(); });
    $("judge-btn").onclick = showJudgment;
    $("speak-btn").onclick = speakJudgment;
    $("chronicle-btn").onclick = showChronicle;
    $("chronicle-download-btn").onclick = downloadChronicle;
    $("chronicle-close-btn").onclick = function () { $("chronicle-panel").classList.add("hidden"); };
    $("music-toggle").onchange = function () {
      if (!window.MusicLayer) return;
      window.MusicLayer.setEnabled(this.checked);
    };
  });
})();
