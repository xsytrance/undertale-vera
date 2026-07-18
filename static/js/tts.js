/* Guided-Mode read-aloud (TTS).  window.TTS
 *
 * Presentation layer ONLY: it speaks text that is already grounded — the party's
 * reactions, the guide's hints, the session story — and never invents or alters a
 * word.  Same two-bucket wall as everywhere else: TTS colours HOW a line sounds,
 * never WHAT it says.  Scoped to Guided Mode by the app; OFF by default, so the rest
 * of Ember keeps Undertale's no-voices silence.
 *
 * Two engines, auto-selected:
 *   • server  — Ember's local Kokoro neural TTS (/api/tts). Best quality; works in
 *               ANY browser/OS (Linux has no built-in voices). Preferred when present.
 *   • browser — the Web Speech API (speechSynthesis). The fallback — e.g. Windows
 *               SAPI voices when the server engine isn't installed.
 *
 * Controls note: a browser only receives key/gamepad input while ITS window is
 * focused.  Auto-speak needs no input (new beats speak themselves), so it works while
 * you play.  Repeat/Stop/Toggle fire when the companion window is focused — or map a
 * pad button to a key at the OS level (joy2key / AntiMicro).
 */
(function () {
  "use strict";

  var synth = window.speechSynthesis || null;
  var LS = { on: "uv_tts_on", rate: "uv_tts_rate", pitch: "uv_tts_pitch",
             vol: "uv_tts_vol", voice: "uv_tts_voice", keys: "uv_tts_keys", pad: "uv_tts_pad" };

  // Per-character colour for the BROWSER engine (rate/pitch nudges). The server
  // engine picks a distinct Kokoro voice per character instead (see tts_service.py).
  var PROFILES = {
    Sans: { rate: -0.15, pitch: -0.55 }, Papyrus: { rate: 0.18, pitch: 0.55 },
    Toriel: { rate: -0.05, pitch: 0.05 }, Undyne: { rate: 0.18, pitch: -0.25 },
    Alphys: { rate: 0.22, pitch: 0.35 }, Flowey: { rate: 0.05, pitch: 0.30 },
    Asgore: { rate: -0.20, pitch: -0.60 }, Mettaton: { rate: 0.10, pitch: 0.20 },
    Napstablook: { rate: -0.22, pitch: -0.10 },
    Susie: { rate: 0.10, pitch: -0.40 }, Ralsei: { rate: -0.05, pitch: 0.35 },
    Kris: { rate: -0.05, pitch: -0.15 }, Noelle: { rate: 0.00, pitch: 0.30 },
    Lancer: { rate: 0.20, pitch: 0.45 }
  };
  var DEFAULT_KEYS = { repeat: "r", stop: "x", toggle: "t" };

  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function jGet(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function clamp(n, lo, hi) { n = parseFloat(n); if (isNaN(n)) n = lo; return Math.max(lo, Math.min(hi, n)); }
  function assign(t) { for (var i = 1; i < arguments.length; i++) { var s = arguments[i]; if (s) for (var k in s) if (Object.prototype.hasOwnProperty.call(s, k)) t[k] = s[k]; } return t; }

  var state = {
    enabled: lsGet(LS.on, "0") === "1",
    rate: clamp(lsGet(LS.rate, "1"), 0.5, 2),
    pitch: clamp(lsGet(LS.pitch, "1"), 0, 2),
    vol: clamp(lsGet(LS.vol, "1"), 0, 1),
    voice: lsGet(LS.voice, ""),           // override voice id (browser voiceURI OR kokoro id); "" = auto
    keys: assign({}, DEFAULT_KEYS, jGet(LS.keys, {})),
    pad: jGet(LS.pad, {}),                 // command -> gamepad button index
    active: false,                         // true only while the Guided view is showing
    last: null,                            // { text, character } — for Repeat
    engine: synth ? "browser" : "none",    // upgraded to "server" once /api/tts is confirmed
    serverVoices: [],                      // kokoro voice ids
    browserVoices: []
  };

  var listeners = [];
  function onChange(cb) { if (typeof cb === "function") listeners.push(cb); }
  function emit() { var c = config(); listeners.forEach(function (f) { try { f(c); } catch (e) {} }); }

  // ── browser voices ──────────────────────────────────────────────────────────
  function loadVoices() { if (synth) { state.browserVoices = synth.getVoices() || []; emit(); } }
  if (synth) { loadVoices(); try { synth.addEventListener("voiceschanged", loadVoices); } catch (e) {} }
  function pickBrowserVoice() {
    var vs = state.browserVoices, i;
    if (state.voice) for (i = 0; i < vs.length; i++) if (vs[i].voiceURI === state.voice) return vs[i];
    for (i = 0; i < vs.length; i++) if (/^en(-|_|$)/i.test(vs[i].lang || "")) return vs[i];
    return vs[0] || null;
  }

  // ── server engine probe (/api/tts) ─────────────────────────────────────────
  var probed = false;
  function probe() {
    if (probed) return; probed = true;
    try {
      fetch("/api/tts/health").then(function (r) { return r.ok ? r.json() : null; }).then(function (h) {
        if (h && h.available) { state.engine = "server"; state.serverVoices = h.voices || []; }
        emit();
      }).catch(function () { emit(); });
    } catch (e) { emit(); }
  }

  // ── speaking ────────────────────────────────────────────────────────────────
  var curAudio = null, lastUrl = null;
  function stopAudio() { if (curAudio) { try { curAudio.pause(); } catch (e) {} curAudio = null; } }
  function playUrl(url) { stopAudio(); try { var a = new Audio(url); a.volume = state.vol; curAudio = a; a.play().catch(function () {}); } catch (e) {} }

  function browserUtter(text, character) {
    if (!synth || !text) return;
    var u = new SpeechSynthesisUtterance(text);
    var prof = (character && PROFILES[character]) || { rate: 0, pitch: 0 };
    u.rate = clamp(state.rate + prof.rate, 0.5, 2);
    u.pitch = clamp(state.pitch + prof.pitch, 0, 2);
    u.volume = state.vol;
    var v = pickBrowserVoice(); if (v) u.voice = v;
    try { synth.speak(u); } catch (e) {}
  }
  function serverSpeak(text, character) {
    stopAudio();
    var body = { text: text, character: character || null, voice: state.voice || null, speed: state.rate };
    fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) throw new Error("tts " + r.status); return r.blob(); })
      .then(function (blob) {
        if (lastUrl) { try { URL.revokeObjectURL(lastUrl); } catch (e) {} }
        lastUrl = URL.createObjectURL(blob); playUrl(lastUrl);
      })
      .catch(function () { if (synth) browserUtter(text, character); });   // degrade to the browser voice
  }

  function speak(text, character) {
    if (!state.enabled || !text) return;
    var t = String(text).trim(); if (!t) return;
    state.last = { text: t, character: character || null };
    if (state.engine === "server") serverSpeak(t, character);
    else browserUtter(t, character);
  }
  function repeat() {
    if (state.engine === "server") { if (lastUrl) playUrl(lastUrl); else if (state.last) serverSpeak(state.last.text, state.last.character); return; }
    if (state.last) { cancel(); browserUtter(state.last.text, state.last.character); }
  }
  function preview(text, character) {
    var t = text || "Ember will read the party's replies aloud, in each character's voice.";
    cancel();
    if (state.engine === "server") serverSpeak(t, character); else browserUtter(t, character);
  }
  function cancel() { stopAudio(); if (synth) { try { synth.cancel(); } catch (e) {} } }

  function setEnabled(on) { state.enabled = !!on; lsSet(LS.on, on ? "1" : "0"); if (!on) cancel(); emit(); }
  function toggle() { setEnabled(!state.enabled); }

  function command(name) {
    if (name === "repeat") repeat();
    else if (name === "stop") cancel();
    else if (name === "toggle") toggle();
  }
  function keyCommand(key) {
    var k = (key || "").toLowerCase();
    for (var cmd in state.keys) if (Object.prototype.hasOwnProperty.call(state.keys, cmd) && (state.keys[cmd] || "").toLowerCase() === k && k) return cmd;
    return null;
  }

  // ── config setters ────────────────────────────────────────────────────────
  function setRate(r) { state.rate = clamp(r, 0.5, 2); lsSet(LS.rate, state.rate); }
  function setPitch(p) { state.pitch = clamp(p, 0, 2); lsSet(LS.pitch, state.pitch); }
  function setVol(v) { state.vol = clamp(v, 0, 1); lsSet(LS.vol, state.vol); if (curAudio) curAudio.volume = state.vol; }
  function setVoice(id) { state.voice = id || ""; lsSet(LS.voice, state.voice); }
  function setKey(cmd, key) { state.keys[cmd] = (key || "").toLowerCase(); lsSet(LS.keys, JSON.stringify(state.keys)); emit(); }
  function setPad(cmd, idx) { if (idx == null) delete state.pad[cmd]; else state.pad[cmd] = idx; lsSet(LS.pad, JSON.stringify(state.pad)); emit(); }

  // ── gamepad: a rAF edge-detector while Guided is active ─────────────────────
  var padRAF = null, padPrev = {};
  function pads() { try { return (navigator.getGamepads && navigator.getGamepads()) || []; } catch (e) { return []; } }
  function padLoop() {
    padRAF = null;
    if (!state.active) return;
    var gps = pads();
    for (var i = 0; i < gps.length; i++) {
      var gp = gps[i]; if (!gp) continue;
      for (var cmd in state.pad) {
        if (!Object.prototype.hasOwnProperty.call(state.pad, cmd)) continue;
        var bi = state.pad[cmd], btn = gp.buttons && gp.buttons[bi];
        var pressed = !!(btn && (btn.pressed || btn.value > 0.5));
        var kkey = i + ":" + bi;
        if (pressed && !padPrev[kkey]) command(cmd);
        padPrev[kkey] = pressed;
      }
    }
    padRAF = requestAnimationFrame(padLoop);
  }
  function startPad() { if (!padRAF && state.active && window.requestAnimationFrame) padRAF = requestAnimationFrame(padLoop); }
  function stopPad() { if (padRAF) { cancelAnimationFrame(padRAF); padRAF = null; } padPrev = {}; }
  function setActive(on) { state.active = !!on; if (on) startPad(); else stopPad(); }

  // Poll for the next pressed button, for press-to-bind. Returns a cancel fn.
  function captureGamepad(onDone) {
    var raf = null, done = false;
    function tick() {
      if (done) return;
      var gps = pads();
      for (var i = 0; i < gps.length; i++) {
        var gp = gps[i]; if (!gp || !gp.buttons) continue;
        for (var b = 0; b < gp.buttons.length; b++) {
          var btn = gp.buttons[b];
          if (btn && (btn.pressed || btn.value > 0.5)) { done = true; onDone(b, gp.id || ""); return; }
        }
      }
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return function () { done = true; if (raf) cancelAnimationFrame(raf); };
  }

  function voiceList() {
    if (state.engine === "server") return state.serverVoices.map(function (id) { return { name: id, voiceURI: id, lang: "" }; });
    return state.browserVoices.map(function (v) { return { name: v.name, lang: v.lang, voiceURI: v.voiceURI }; });
  }
  function config() {
    return {
      supported: state.engine !== "none", engine: state.engine,
      enabled: state.enabled, rate: state.rate, pitch: state.pitch, vol: state.vol,
      voice: state.voice, voices: voiceList(),
      keys: assign({}, state.keys), pad: assign({}, state.pad)
    };
  }

  window.TTS = {
    supported: state.engine !== "none",
    speak: speak, repeat: repeat, preview: preview, stop: cancel, toggle: toggle,
    setEnabled: setEnabled, isEnabled: function () { return state.enabled; },
    command: command, keyCommand: keyCommand, setActive: setActive, probe: probe,
    setRate: setRate, setPitch: setPitch, setVol: setVol, setVoice: setVoice,
    setKey: setKey, setPad: setPad, captureGamepad: captureGamepad,
    config: config, onChange: onChange
  };
})();
