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

  // Static catalog (flavour only; structure is portable). The route beds are
  // optional — drop the files on the server to hear them; until then the layer
  // falls back to the main theme (see the 'error' handler in init), so a missing
  // bed is silent-safe rather than a 404 into no music.
  var TRACKS = {
    "a-new-save-file": { title: "A New Save File", url: "/audio/a-new-save-file.mp3", ambient: true },
    "route-pacifist":  { title: "Mercy",          url: "/audio/route-pacifist.mp3",  ambient: true },
    "route-neutral":   { title: "The In-Between",  url: "/audio/route-neutral.mp3",   ambient: true },
    "route-genocide":  { title: "Dust",            url: "/audio/route-genocide.mp3",  ambient: true },
    "dark-world":      { title: "The Dark World",  url: "/audio/dark-world.mp3",      ambient: true }
  };

  // Per-route bed. Each route prefers its own track; if that file isn't present
  // it falls back to the main theme (and remembers, to avoid restart churn).
  var ROUTE_TRACK = {
    Pacifist: "route-pacifist",
    Neutral: "route-neutral",
    Genocide: "route-genocide",
    undetermined: MENU_TRACK
  };
  var _failed = {};     // track ids whose audio file 404'd this session
  var _fallback = {};   // trackId → the track to play if its file is missing

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
      if (this.prefs.volume == null) this.prefs.volume = 0.22;
      this.audio.volume = this.prefs.volume * (window.AudioBus ? window.AudioBus.gain() : 1);
      if (this.prefs.enabled === undefined) this.prefs.enabled = true;  // on by default, quiet
      var self = this;
      // a missing bed → remember it and fall back (route bed → main theme;
      // character theme → the current route bed → main theme)
      this.audio.addEventListener("error", function () {
        var cur = self.current;
        if (cur && cur !== MENU_TRACK) {
          _failed[cur] = true;
          self.play(_fallback[cur] || MENU_TRACK);
        }
      });
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
      this.applyMaster();
      savePrefs(this.prefs);
    },

    // the global master (top-bar volume/mute) scales the music bed on top of its
    // own gentle level; called on init and whenever the master changes.
    _master: function () { return window.AudioBus ? window.AudioBus.gain() : 1; },
    applyMaster: function () {
      if (this.audio) this.audio.volume = this.prefs.volume * this._master();
    },

    // Drive the bed from the live SaveTruth route (if enabled). A route whose bed
    // is known-missing plays the main theme directly (no 404, no restart churn).
    setRoute: function (route) {
      var id = ROUTE_TRACK[route] || ROUTE_TRACK.undetermined;
      if (_failed[id]) id = MENU_TRACK;
      this._routeBed = id;   // remembered as the fallback for character themes
      this.play(id);
    },

    // The Dark World's own bed (Deltarune saves). Missing file → main theme, and
    // character themes recorded against it fall back through it the same way.
    setWorld: function (world) {
      if (world !== "dark") return;
      var id = _failed["dark-world"] ? MENU_TRACK : "dark-world";
      _fallback["dark-world"] = MENU_TRACK;
      this._routeBed = id;
      this.play(id);
    },

    // Play a character's own theme while you talk to them (optional). The file is
    // /audio/char-<slug>.mp3; if it's absent it falls back to the current route
    // bed (then the main theme), so this is silent-safe until the files exist.
    setCharacter: function (slug) {
      if (!slug) return;
      this.init();
      var id = "char-" + slug, back = this._routeBed || MENU_TRACK;
      if (!TRACKS[id]) TRACKS[id] = { title: slug, url: "/audio/" + id + ".mp3", ambient: true };
      _fallback[id] = back;
      this.play(_failed[id] ? back : id);   // known-missing → route bed directly
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
