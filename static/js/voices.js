/* ════════════════════════════════════════════════════════════════════════
   CHARACTER VOICES — undertale-vera
   ------------------------------------------------------------------------
   The Underground has no spoken voices — characters "speak" in little beeps as
   their text types out. This layer gives each character an ORIGINAL synthesized
   voice (no ripped samples), rendered live in WebAudio from a small per-character
   profile. It replaces the old single-square-wave blip.

   A profile drives one blip:
     wave     — timbre: sine (soft) / triangle (round) / square (chippy) / sawtooth (harsh)
     freq     — base pitch (Hz)
     jitter   — per-glyph random detune (fraction of freq) so it isn't monotone
     dur      — length (s)
     gain     — loudness (0..1, kept low)
     attack   — envelope rise (s); the rest of dur is the decay
     glide    — pitch bends to freq*glide over dur (the "boop"); omit for steady
     vibrato  — {rate, depth} frequency wobble (theatrical / unstable voices)
     lowpass  — cutoff (Hz) for muffled / distant voices
     every    — fire a blip every N typed glyphs (cadence)
     stutter  — 0..1 chance of a quick second blip (nervous voices)

   Exposes window.VoiceLayer: blip(name), blipEvery(name), preview(name).
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  // Per-character voices — tuned by feeling, not by the game's actual sounds.
  // Phone speakers roll off bass and can't reproduce pure sines, so every voice
  // keeps its fundamental above ~330 Hz and uses a harmonic-rich wave (square /
  // sawtooth); the "soft" characters get their warmth from a lowpass filter that
  // rounds the harmonics off rather than from a quiet sine that vanishes on a phone.
  var VOICES = {
    // low, lazy, unbothered — a rounded low tone that sags downward
    "Sans":        { wave: "square",   freq: 340, jitter: 0.04, dur: 0.085, gain: 0.062, attack: 0.006, glide: 0.80, lowpass: 1500, every: 2 },
    // loud, bombastic, HEROIC — a punchy chip that leaps upward
    "Papyrus":     { wave: "square",   freq: 500, jitter: 0.03, dur: 0.070, gain: 0.075, attack: 0.002, glide: 1.42, every: 2 },
    // saccharine and wrong — bright, harsh, unstable wobble
    "Flowey":      { wave: "sawtooth", freq: 636, jitter: 0.13, dur: 0.060, gain: 0.052, attack: 0.002, vibrato: { rate: 34, depth: 26 }, every: 2 },
    // warm, gentle, motherly — a rounded swell that lingers (lowpass = warmth)
    "Toriel":      { wave: "square",   freq: 466, jitter: 0.03, dur: 0.095, gain: 0.072, attack: 0.012, lowpass: 1900, every: 2 },
    // fierce, aggressive — harsh and fast, snapping upward
    "Undyne":      { wave: "sawtooth", freq: 452, jitter: 0.05, dur: 0.055, gain: 0.075, attack: 0.001, glide: 1.12, every: 2 },
    // nervous, anxious — short and high, prone to stammering doubles
    "Alphys":      { wave: "square",   freq: 610, jitter: 0.10, dur: 0.045, gain: 0.056, attack: 0.002, stutter: 0.35, every: 2 },
    // deep, sorrowful, regal — the lowest voice, muffled, sinking slowly
    "Asgore":      { wave: "square",   freq: 330, jitter: 0.03, dur: 0.110, gain: 0.074, attack: 0.010, lowpass: 1300, glide: 0.90, every: 2 },
    // glam, theatrical, electric — bright with a showy shimmer
    "Mettaton":    { wave: "square",   freq: 574, jitter: 0.04, dur: 0.080, gain: 0.066, attack: 0.003, vibrato: { rate: 18, depth: 16 }, glide: 1.08, every: 2 },
    // quiet, melancholic, ethereal — soft and muffled, but still there; sparse
    "Napstablook": { wave: "square",   freq: 430, jitter: 0.05, dur: 0.110, gain: 0.058, attack: 0.018, lowpass: 1500, every: 3 },
    // anyone else
    "_default":    { wave: "square",   freq: 480, jitter: 0.05, dur: 0.050, gain: 0.060, attack: 0.003, every: 2 }
  };

  var _ac = null, _master = null;
  function ctx() {
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      if (!_ac) { _ac = new AC(); _master = _ac.createGain(); _master.gain.value = 1; _master.connect(_ac.destination); }
      if (_ac.state === "suspended") _ac.resume();
      return _ac;
    } catch (e) { return null; }
  }

  function profile(name) { return VOICES[name] || VOICES._default; }

  // Render one blip from a profile, starting at time `when`.
  function tone(ac, spec, when) {
    var mg = window.AudioBus ? window.AudioBus.gain() : 1;   // global master volume/mute
    if (mg <= 0) return;                                     // muted → no blip
    var f0 = spec.freq * (1 + (Math.random() * 2 - 1) * (spec.jitter || 0));
    var dur = spec.dur || 0.05;
    var osc = ac.createOscillator();
    osc.type = spec.wave || "square";
    osc.frequency.setValueAtTime(f0, when);
    if (spec.glide) osc.frequency.exponentialRampToValueAtTime(Math.max(20, f0 * spec.glide), when + dur);

    var g = ac.createGain();
    var peak = (spec.gain != null ? spec.gain : 0.05) * mg;
    var atk = Math.min(spec.attack != null ? spec.attack : 0.004, dur * 0.5);
    g.gain.setValueAtTime(0.0001, when);
    g.gain.exponentialRampToValueAtTime(peak, when + atk);
    g.gain.exponentialRampToValueAtTime(0.0001, when + dur);

    if (spec.vibrato) {
      var lfo = ac.createOscillator(), lg = ac.createGain();
      lfo.type = "sine"; lfo.frequency.setValueAtTime(spec.vibrato.rate, when);
      lg.gain.setValueAtTime(spec.vibrato.depth, when);
      lfo.connect(lg); lg.connect(osc.frequency);
      lfo.start(when); lfo.stop(when + dur + 0.02);
    }

    osc.connect(g);
    if (spec.lowpass) {
      var lp = ac.createBiquadFilter();
      lp.type = "lowpass"; lp.frequency.setValueAtTime(spec.lowpass, when);
      g.connect(lp); lp.connect(_master);
    } else {
      g.connect(_master);
    }
    osc.start(when); osc.stop(when + dur + 0.02);
  }

  var VoiceLayer = {
    blipEvery: function (name) { return profile(name).every || 2; },

    // one typing blip, right now
    blip: function (name) {
      var ac = ctx(); if (!ac) return;
      var v = profile(name), t = ac.currentTime;
      tone(ac, v, t);
      if (v.stutter && Math.random() < v.stutter) {
        tone(ac, { wave: v.wave, freq: v.freq, jitter: v.jitter, dur: v.dur * 0.6, gain: (v.gain || 0.05) * 0.7, attack: v.attack, lowpass: v.lowpass }, t + v.dur * 0.7);
      }
    },

    // a soft menu "confirm" — two quick rising notes (the classic pick-a-thing feel)
    ui: function () {
      var ac = ctx(); if (!ac) return;
      var t = ac.currentTime;
      tone(ac, { wave: "square", freq: 520, dur: 0.05, gain: 0.045, attack: 0.002 }, t);
      tone(ac, { wave: "square", freq: 720, dur: 0.06, gain: 0.045, attack: 0.002 }, t + 0.055);
    },

    // play a short sample of the voice, as if the character were typing a line
    preview: function (name) {
      var ac = ctx(); if (!ac) return;
      var v = profile(name), every = v.every || 2;
      var steps = 16, step = 0.055, t = ac.currentTime + 0.02;
      for (var i = 0; i < steps; i++) {
        if (i % every === 0) {
          tone(ac, v, t);
          if (v.stutter && (i * 7) % 5 === 0) {
            tone(ac, { wave: v.wave, freq: v.freq, jitter: v.jitter, dur: v.dur * 0.6, gain: (v.gain || 0.05) * 0.7, attack: v.attack, lowpass: v.lowpass }, t + v.dur * 0.7);
          }
        }
        t += step;
      }
    }
  };

  window.VoiceLayer = VoiceLayer;
})();
