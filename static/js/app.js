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
    // tint the header sigil red on the Genocide beat.
    $("header-sigil").className = "soul-sigil" + (route === "Genocide" ? " determined" : "");
  }
  function row(k, v) { return '<div class="k">' + k + "</div><div>" + v + "</div>"; }

  // ── roster ────────────────────────────────────────────────────────────────
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
        card.innerHTML = portrait + '<div class="name">' + c.name + "</div>";
        card.onclick = function () { selectCharacter(c); };
        el.appendChild(card);
      });
      $("roster-panel").classList.remove("hidden");
    });
  }

  function selectCharacter(c) {
    state.character = c.name;
    if (!state.history[c.name]) state.history[c.name] = [];
    Array.prototype.forEach.call(document.querySelectorAll(".char-card"), function (el) {
      el.classList.toggle("selected", el.dataset.name === c.name);
    });
    $("chat-name").textContent = c.name;
    var p = $("chat-portrait");
    if (c.avatar_url) { p.outerHTML = '<img class="relic-portrait" id="chat-portrait" src="' + c.avatar_url + '" />'; }
    renderTranscript();
    $("chat-panel").classList.remove("hidden");
    $("judgment-panel").classList.add("hidden");
  }

  // ── chat ──────────────────────────────────────────────────────────────────
  function renderTranscript() {
    var t = $("transcript"); t.innerHTML = "";
    (state.history[state.character] || []).forEach(function (m) {
      var b = document.createElement("div");
      b.className = "bubble " + (m.role === "user" ? "you" : "them");
      b.innerHTML = '<div class="who">' + (m.role === "user" ? "you" : state.character) + "</div>";
      var span = document.createElement("span");
      span.textContent = m.content;
      b.appendChild(span);
      t.appendChild(b);
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
      var last = $("transcript").lastChild.querySelector("span");
      typewriter(last, res.response);
    }).catch(function (e) {
      hist.push({ role: "assistant", content: "(error: " + e.message + ")" });
      renderTranscript();
    });
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
  window.addEventListener("DOMContentLoaded", function () {
    if (window.MusicLayer) window.MusicLayer.init();
    $("upload-btn").onclick = uploadSave;
    $("refresh-btn").onclick = refreshSave;
    $("send-btn").onclick = sendMessage;
    $("chat-input").addEventListener("keydown", function (e) { if (e.key === "Enter") sendMessage(); });
    $("judge-btn").onclick = showJudgment;
    $("speak-btn").onclick = speakJudgment;
    $("music-toggle").onchange = function () {
      if (!window.MusicLayer) return;
      window.MusicLayer.setEnabled(this.checked);
    };
  });
})();
