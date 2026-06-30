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

  // The main theme — a user-supplied track that auto-plays on load. Audio files
  // are gitignored; drop the file at static/audio/a-new-save-file.mp3 on the server.
  var MENU_TRACK = "a-new-save-file";

  // Static catalog (flavour only; structure is portable).
  var TRACKS = {
    "a-new-save-file": { title: "A New Save File", url: "/audio/a-new-save-file.mp3", ambient: true },
    "ember-field":   { title: "Ember Field",   url: "/audio/ember-field.mp3",   ambient: true },
    "obsidian-calm": { title: "Obsidian Calm",  url: "/audio/obsidian-calm.mp3", ambient: true },
    "determination": { title: "Determination",  url: "/audio/determination.mp3", ambient: false }
  };

  // Per-route bed. For now every route keeps the main theme playing — the route
  // track files don't exist yet, and switching to a 404 would cut the music.
  var ROUTE_TRACK = {
    Pacifist: MENU_TRACK, Neutral: MENU_TRACK, Genocide: MENU_TRACK, undetermined: MENU_TRACK
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
      if (this.current !== trackId) { this.current = trackId; this.audio.src = track.url; }
      if (!this.audio.paused) return;   // already playing this track — don't restart
      var self = this;
      var p = this.audio.play();
      if (p && p.catch) {
        p.catch(function () { self.blocked = true; });  // autoplay blocked → start on first gesture
      }
    },

    isEnabled: function () { this.init(); return this.prefs.enabled !== false; },

    // Auto-play the main theme. Browsers block autoplay until a user gesture, so
    // we try immediately AND start on the first interaction (one-shot listeners).
    startMenu: function () {
      this.init();
      if (this.prefs.volume == null) this.setVolume(0.4);   // a reasonable default
      var self = this;
      this.play(MENU_TRACK);
      function kick() {
        ["pointerdown", "keydown", "touchstart"].forEach(function (ev) {
          document.removeEventListener(ev, kick, true);
        });
        self.play(MENU_TRACK);
      }
      ["pointerdown", "keydown", "touchstart"].forEach(function (ev) {
        document.addEventListener(ev, kick, true);
      });
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
