/* ════════════════════════════════════════════════════════════════════════
   GLOBAL MUSIC LAYER — undertale-vera
   ------------------------------------------------------------------------
   Ported PATTERN from fft-psx-vera's MusicProvider (frontend/src/lib/music.tsx):
   a single shared <audio> element, a static track/screen catalog, localStorage
   preferences, autoplay-block handling, and per-screen track selection. Ported
   from React context to dependency-free vanilla JS so the Spine-0 static shell
   carries it with no build step.

   Audio files themselves are gitignored (see .gitignore) — this is the layer,
   not the soundtrack. Tracks point at /audio/<id>.mp3 and degrade silently when
   a file is absent (autoplay/404 handled).

   NEXT BEAT (see ROADMAP): route-aware music — swap the ambient bed by the
   SaveTruth route. The hook (MusicLayer.setRoute) is stubbed here.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var PREF_KEY = "undertale-vera:music:v1";

  // Static catalog (flavour only; structure is portable).
  var TRACKS = {
    "ember-field":   { title: "Ember Field",   url: "/audio/ember-field.mp3",   ambient: true },
    "obsidian-calm": { title: "Obsidian Calm",  url: "/audio/obsidian-calm.mp3", ambient: true },
    "determination": { title: "Determination",  url: "/audio/determination.mp3", ambient: false }
  };

  // Per-route default bed (the route-aware-music seed for the next beat).
  var ROUTE_TRACK = {
    Pacifist: "ember-field",
    Neutral: "obsidian-calm",
    Genocide: "determination",
    undetermined: "obsidian-calm"
  };

  function loadPrefs() {
    try { return JSON.parse(localStorage.getItem(PREF_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function savePrefs(p) {
    try { localStorage.setItem(PREF_KEY, JSON.stringify(p)); } catch (e) {}
  }

  var MusicLayer = {
    audio: null,
    prefs: loadPrefs(),
    current: null,
    blocked: false,

    init: function () {
      if (this.audio) return this;
      this.audio = new Audio();
      this.audio.loop = true;
      this.audio.volume = (this.prefs.volume != null) ? this.prefs.volume : 0.5;
      if (this.prefs.enabled === undefined) this.prefs.enabled = true;
      return this;
    },

    play: function (trackId) {
      this.init();
      var track = TRACKS[trackId];
      if (!track || !this.prefs.enabled) return;
      this.current = trackId;
      this.audio.src = track.url;
      var self = this;
      var p = this.audio.play();
      if (p && p.catch) {
        p.catch(function () { self.blocked = true; });  // autoplay blocked → hint, no error
      }
    },

    setEnabled: function (on) {
      this.init();
      this.prefs.enabled = !!on;
      savePrefs(this.prefs);
      if (!on) { this.audio.pause(); }
      else if (this.current) { this.play(this.current); }
    },

    setVolume: function (v) {
      this.init();
      this.prefs.volume = Math.max(0, Math.min(1, v));
      this.audio.volume = this.prefs.volume;
      savePrefs(this.prefs);
    },

    // route-aware-music seed for the NEXT beat.
    setRoute: function (route) {
      var trackId = ROUTE_TRACK[route] || ROUTE_TRACK.undetermined;
      this.play(trackId);
    }
  };

  window.MusicLayer = MusicLayer;
})();
