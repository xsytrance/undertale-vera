/* ════════════════════════════════════════════════════════════════════════
   GLOBAL MUSIC LAYER — undertale-vera
   ------------------------------------------------------------------------
   Ported PATTERN from fft-psx-vera's MusicProvider (frontend/src/lib/music.tsx):
   a single shared <audio> element, a static track/screen catalog, localStorage
   preferences, autoplay-block handling, and per-screen track selection. Ported
   from React context to dependency-free vanilla JS so the static shell carries
   it with no build step.

   Audio files themselves are gitignored (see .gitignore) — this is the layer,
   not the soundtrack. Tracks point at /audio/<id>.mp3 and degrade silently when
   a file is absent (autoplay/404 handled).

   Only one bed ships today: the main theme, "A New Save File". ROUTE_TRACK keeps
   the per-route seam so route-specific beds are a one-line change later — every
   route points at the main theme so save-loads never 404.

   Autoplay: browsers block audio.play() until the first user gesture. play()
   arms a one-shot document listener on the block and resumes on the first tap
   or key, so "enable music" reliably starts the theme even mid-page.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var PREF_KEY = "undertale-vera:music:v1";
  var MENU_TRACK = "a-new-save-file";  // the one bed that ships (gitignored on the server)

  // Static catalog (flavour only; structure is portable).
  var TRACKS = {
    "a-new-save-file": { title: "A New Save File", url: "/audio/a-new-save-file.mp3", ambient: true }
  };

  // Per-route bed. Every route points at the main theme today; swap individual
  // entries here (plus a TRACKS entry + the audio file) to add route beds.
  var ROUTE_TRACK = {
    Pacifist: MENU_TRACK,
    Neutral: MENU_TRACK,
    Genocide: MENU_TRACK,
    undetermined: MENU_TRACK
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
    _armed: false,

    init: function () {
      if (this.audio) return this;
      this.audio = new Audio();
      this.audio.loop = true;
      this.audio.volume = (this.prefs.volume != null) ? this.prefs.volume : 0.22;
      if (this.prefs.enabled === undefined) this.prefs.enabled = true;  // on by default, quiet
      return this;
    },

    isEnabled: function () {
      this.init();
      return !!this.prefs.enabled;
    },

    play: function (trackId) {
      this.init();
      var track = TRACKS[trackId];
      if (!track || !this.prefs.enabled) return;
      if (this.current !== trackId) {
        this.current = trackId;
        this.audio.src = track.url;
      }
      this._resume();
    },

    // Start the default bed (used when the user flips music on, even before a
    // save is loaded / a route is known).
    startMenu: function () {
      this.play(MENU_TRACK);
    },

    setEnabled: function (on) {
      this.init();
      this.prefs.enabled = !!on;
      savePrefs(this.prefs);
      if (!on) { this.audio.pause(); return; }
      if (this.current) this._resume();
      else this.startMenu();
    },

    setVolume: function (v) {
      this.init();
      this.prefs.volume = Math.max(0, Math.min(1, v));
      this.audio.volume = this.prefs.volume;
      savePrefs(this.prefs);
    },

    // Drive the bed from the live SaveTruth route (if enabled).
    setRoute: function (route) {
      this.play(ROUTE_TRACK[route] || ROUTE_TRACK.undetermined);
    },

    // Attempt playback; on autoplay block, arm a one-shot gesture retry.
    _resume: function () {
      if (!this.audio || !this.prefs.enabled || !this.current) return;
      var self = this;
      var p = this.audio.play();
      if (p && p.then) {
        p.then(function () { self.blocked = false; })
         .catch(function () { self.blocked = true; self._armGesture(); });
      }
    },

    _armGesture: function () {
      if (this._armed) return;
      this._armed = true;
      var self = this;
      function go() {
        self._armed = false;
        document.removeEventListener("pointerdown", go, true);
        document.removeEventListener("keydown", go, true);
        self._resume();
      }
      document.addEventListener("pointerdown", go, true);
      document.addEventListener("keydown", go, true);
    }
  };

  window.MusicLayer = MusicLayer;
})();
