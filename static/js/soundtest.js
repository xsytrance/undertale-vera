/* ════════════════════════════════════════════════════════════════════════
   SOUND TEST — undertale-vera's interactive soundtrack room
   ------------------------------------------------------------------------
   Play the whole soundtrack (main theme, the three route beds, and the nine
   character themes), two ways:
     • Jukebox — one track at a time, on loop.
     • Jam     — layer any characters together (all, some, or none) and let
                 their themes collide. Gloriously chaotic on purpose.

   A WebAudio graph mixes it: each track's <audio> → per-track gain → a master
   gain → an analyser (for the visualizer) → the speakers. Files are the same
   gitignored /audio/*.mp3 the rest of the app uses. The UI lives in app.js;
   this module is just the engine + the catalog.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var CATALOG = {
    main: [
      { id: "a-new-save-file", label: "A New Save File" },
      { id: "main-theme", label: "Alternate Theme" },
    ],
    routes: [
      { id: "route-pacifist", label: "Pacifist", route: "pacifist" },
      { id: "route-neutral", label: "Neutral", route: "neutral" },
      { id: "route-genocide", label: "Genocide", route: "genocide" },
    ],
    cast: [
      ["Sans", "sans"], ["Papyrus", "papyrus"], ["Flowey", "flowey"],
      ["Toriel", "toriel"], ["Undyne", "undyne"], ["Alphys", "alphys"],
      ["Asgore", "asgore"], ["Mettaton", "mettaton"], ["Napstablook", "napstablook"],
    ].map(function (c) { return { id: "char-" + c[1], label: c[0], name: c[0], slug: c[1] }; }),
    darkbed: [
      { id: "dark-world", label: "The Dark World", dark: true },
    ],
    darkcast: [
      ["Susie", "susie"], ["Ralsei", "ralsei"], ["Lancer", "lancer"], ["Noelle", "noelle"],
      ["King", "king"], ["Rouxls Kaard", "rouxls-kaard"], ["Jevil", "jevil"], ["Seam", "seam"],
    ].map(function (c) { return { id: "char-" + c[1], label: c[0], name: c[0], slug: c[1], dark: true }; }),
  };

  var ST = {
    ctx: null, master: null, analyser: null, freq: null,
    nodes: {},      // id → { audio, src, gain }
    active: {},     // id → true (currently playing)
    mode: "jukebox",
    loop: true,
    masterVol: 0.6,

    ensure: function () {
      if (this.ctx) { if (this.ctx.state === "suspended") this.ctx.resume(); return this.ctx; }
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      this.ctx = new AC();
      this.master = this.ctx.createGain(); this.master.gain.value = this.masterVol * this._bus();
      this.analyser = this.ctx.createAnalyser(); this.analyser.fftSize = 128;
      this.freq = new Uint8Array(this.analyser.frequencyBinCount);
      this.master.connect(this.analyser); this.analyser.connect(this.ctx.destination);
      return this.ctx;
    },

    _node: function (id) {
      if (this.nodes[id]) return this.nodes[id];
      if (!this.ensure()) return null;
      try {
        var a = new Audio("/audio/" + id + ".mp3"); a.loop = this.loop; a.preload = "auto";
        var src = this.ctx.createMediaElementSource(a);
        var g = this.ctx.createGain(); g.gain.value = 1;
        src.connect(g); g.connect(this.master);
        return (this.nodes[id] = { audio: a, src: src, gain: g });
      } catch (e) { return null; }
    },

    playSolo: function (id) {          // jukebox: exactly one at a time
      this.ensure(); this.stopAll();
      var n = this._node(id); if (!n) return;
      this.active[id] = true; n.audio.currentTime = 0;
      var p = n.audio.play(); if (p && p.catch) p.catch(function () {});
    },
    toggle: function (id) {            // jam: add / remove a layer
      this.ensure();
      var n = this._node(id); if (!n) return false;
      if (this.active[id]) { n.audio.pause(); delete this.active[id]; return false; }
      this.active[id] = true;
      var p = n.audio.play(); if (p && p.catch) p.catch(function () {});
      return true;
    },
    stopAll: function () { for (var id in this.active) { if (this.nodes[id]) this.nodes[id].audio.pause(); } this.active = {}; },

    isActive: function (id) { return !!this.active[id]; },
    activeIds: function () { var out = []; for (var id in this.active) out.push(id); return out; },
    setLoop: function (on) { this.loop = !!on; for (var id in this.nodes) this.nodes[id].audio.loop = this.loop; },
    _bus: function () { return window.AudioBus ? window.AudioBus.gain() : 1; },   // global master
    applyMaster: function () { if (this.master) this.master.gain.value = this.masterVol * this._bus(); },
    setMasterVolume: function (v) { this.masterVol = Math.max(0, Math.min(1, v)); this.applyMaster(); },

    // visualizer feeds
    bars: function () { if (!this.analyser) return null; this.analyser.getByteFrequencyData(this.freq); return this.freq; },
    level: function () {
      if (!this.freq) return 0;
      var s = 0; for (var i = 0; i < this.freq.length; i++) s += this.freq[i];
      return (s / this.freq.length) / 255;
    },

    catalog: function () { return CATALOG; },
  };

  window.SoundTest = ST;
})();
