/* SceneLayer — the route-reactive backdrop.
 *
 * Two layers, both honest about what's available:
 *   1. A CSS route-tinted gradient (.scene-<route>) — ALWAYS present, so the
 *      backdrop reacts to the route the moment a save is read, before any art.
 *   2. Generated scene art (static/assets/scenes/<route>.png, gitignored) — when
 *      Prime's ComfyUI pipeline has produced it, it fades in OVER the gradient.
 *
 * The art map is fetched once from /api/scenes; missing routes simply keep the
 * gradient. Never an error, never a broken image. */
(function () {
  "use strict";
  var el = null;
  var sceneMap = {};            // {route: url} of generated art that exists on disk
  var ROUTES = ["pacifist", "neutral", "genocide", "undetermined"];

  function backdrop() {
    if (!el) el = document.getElementById("scene-backdrop");
    return el;
  }

  function setRoute(route) {
    var b = backdrop();
    if (!b) return;
    var key = (route || "undetermined").toLowerCase();
    if (ROUTES.indexOf(key) === -1) key = "undetermined";
    // 1. Route-tinted gradient class (guaranteed fallback).
    b.className = "scene-backdrop scene-" + key;
    // 2. Generated art over the gradient, when we have it for this route.
    var url = sceneMap[key];
    if (url) {
      b.style.backgroundImage = "url('" + url + "')";
      b.classList.add("has-art");
    } else {
      b.style.backgroundImage = "";
      b.classList.remove("has-art");
    }
  }

  function init() {
    // Fetch the available-art map once; failure just leaves gradients in place.
    try {
      fetch("/api/scenes").then(function (r) { return r.json(); }).then(function (d) {
        sceneMap = (d && d.scenes) || {};
      }).catch(function () { /* gradients only — fine */ });
    } catch (e) { /* no fetch — gradients only */ }
  }

  window.SceneLayer = { setRoute: setRoute, init: init };
  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
