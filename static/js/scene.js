/* SceneLayer — the route-reactive backdrop coordinator.
 *
 * Three honest layers, deepest first:
 *   1. ShaderField (WebGL)  — a living ember/haze field graded by route, with a
 *      glitch `pulse()` for the Fun-value anomaly. Active only if WebGL is supported.
 *   2. CSS route tint (.scene-<route>) — the guaranteed fallback. Suppressed by the
 *      `shader-on` body class when the shader is running.
 *   3. Generated scene art (static/assets/scenes/<route>.png, gitignored) — Prime's
 *      painted backdrop, faded in OVER the field when present (/api/scenes).
 *
 * Never an error, never a broken image: missing WebGL → gradient; missing art →
 * shader/gradient. */
(function () {
  "use strict";
  var el = null;
  var sceneMap = {};
  var ROUTES = ["pacifist", "neutral", "genocide", "undetermined"];
  // Fun values that brush a Gaster-tier event (see save_flavor.FUN_EVENTS) — the
  // backdrop tears for a beat when a save sits on one.
  function isAnomalousFun(fun) {
    var f = parseInt(fun, 10);
    if (isNaN(f)) return false;
    return (f >= 61 && f <= 63) || f === 65 || f === 66 || (f >= 90 && f <= 100);
  }

  function backdrop() {
    if (!el) el = document.getElementById("scene-backdrop");
    return el;
  }

  function setRoute(route) {
    var b = backdrop();
    if (!b) return;
    var key = (route || "undetermined").toLowerCase();
    if (ROUTES.indexOf(key) === -1) key = "undetermined";
    b.className = "scene-backdrop scene-" + key;
    // drive the living field
    if (window.ShaderField && window.ShaderField.supported) window.ShaderField.setRoute(key);
    // Prime's painted scene art over the field, when we have it
    var url = sceneMap[key];
    if (url) { b.style.backgroundImage = "url('" + url + "')"; b.classList.add("has-art"); }
    else { b.style.backgroundImage = ""; b.classList.remove("has-art"); }
  }

  // Tear the field for a beat — the Fun-value anomaly made visible. Either pass a
  // raw fun value (gated to Gaster-tier) or call with no args to force a pulse.
  function anomaly(fun) {
    if (!window.ShaderField || !window.ShaderField.supported) return;
    if (arguments.length === 0 || isAnomalousFun(fun)) {
      window.ShaderField.pulse(1.0);
      // a short flurry so it reads as a glitch, not a single frame
      var n = 0, id = setInterval(function () {
        window.ShaderField.pulse(0.8); if (++n > 6) clearInterval(id);
      }, 90);
    }
  }

  function init() {
    // boot the WebGL field; on success suppress the CSS gradient
    var canvas = document.getElementById("scene-shader");
    if (canvas && window.ShaderField && window.ShaderField.init(canvas)) {
      document.body.classList.add("shader-on");
    }
    // fetch Prime's available art map once; failure just leaves the field/gradient
    try {
      fetch("/api/scenes").then(function (r) { return r.json(); }).then(function (d) {
        sceneMap = (d && d.scenes) || {};
      }).catch(function () {});
    } catch (e) {}
  }

  window.SceneLayer = { setRoute: setRoute, anomaly: anomaly, init: init };
  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
