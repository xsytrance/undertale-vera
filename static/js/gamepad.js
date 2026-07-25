/* ════════════════════════════════════════════════════════════════════════
   gamepad.js — drive the whole app from a controller.

   Docked to a TV there is NO pointer: no mouse, no touch. The controller is
   the only input, so this is not a convenience layer — without it the app is
   unusable on a television.

   Built and tested against a DualSense over the standard Gamepad mapping,
   which is also what an Xbox pad reports, so the same code drives both. Only
   the on-screen button NAMES differ, and those follow the detected pad.

   Standard mapping (the browser normalises to this):
     buttons[0]  Cross / A        confirm
     buttons[1]  Circle / B       back, close, blur
     buttons[9]  Options / Menu   toggle TV mode
     buttons[12..15]              D-pad up / down / left / right
     axes[0], axes[1]             left stick

   Navigation is SPATIAL, not DOM-order: pressing right goes to whatever is
   physically to the right. DOM order and visual layout diverge constantly
   (rails, grids, absolutely-positioned menus), and tab-order navigation on a
   D-pad feels broken the moment they disagree.

   Degrades to nothing when no gamepad is present. Never interferes with
   typing: while a text field has focus, only Circle (blur) is handled, so the
   on-screen keyboard and the D-pad don't fight over the same presses.
   ════════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  if (!("getGamepads" in navigator)) return;

  var FOCUSABLE = [
    "button:not(:disabled)",
    "a[href]",
    "input:not(:disabled):not([type=hidden])",
    "select:not(:disabled)",
    "textarea:not(:disabled)",
    "[tabindex]:not([tabindex='-1'])",
    ".st-card", ".save-card", ".char-card", ".ce-face", ".g-chip", ".modes-item"
  ].join(",");

  var REPEAT_DELAY = 420;   // hold-to-repeat: first repeat
  var REPEAT_RATE = 110;    // subsequent repeats
  var STICK_DEADZONE = 0.55;

  var state = {
    active: false,
    held: {},         // button index -> next-fire timestamp
    raf: 0,
    lastPad: null
  };

  // ── helpers ──────────────────────────────────────────────────────────────

  function visible(el) {
    if (!el || el.disabled) return false;
    var r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    // must be inside the viewport band we can scroll to
    if (r.bottom < -40 || r.top > window.innerHeight + 40) return false;
    var s = window.getComputedStyle(el);
    return s.visibility !== "hidden" && s.display !== "none" &&
           parseFloat(s.opacity || "1") > 0.05;
  }

  function candidates() {
    var out = [];
    var all = document.querySelectorAll(FOCUSABLE);
    for (var i = 0; i < all.length; i++) {
      if (visible(all[i])) out.push(all[i]);
    }
    return out;
  }

  function centre(el) {
    var r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, r: r };
  }

  function isTextField(el) {
    if (!el) return false;
    var tag = (el.tagName || "").toLowerCase();
    if (tag === "textarea") return true;
    if (tag !== "input") return false;
    var t = (el.getAttribute("type") || "text").toLowerCase();
    return ["text", "search", "email", "url", "password", "number", "tel"]
             .indexOf(t) !== -1;
  }

  /* Pick the best element in a direction.
     Score = distance along the axis + a heavy penalty for drifting off it, so
     a near-perfect neighbour beats something closer but wildly off-axis. */
  function pick(dir) {
    var current = document.activeElement;
    var list = candidates();
    if (!list.length) return null;

    if (!current || current === document.body || list.indexOf(current) === -1) {
      return list[0];
    }

    var from = centre(current);
    var best = null;
    var bestScore = Infinity;

    for (var i = 0; i < list.length; i++) {
      var el = list[i];
      if (el === current) continue;
      var to = centre(el);
      var dx = to.x - from.x;
      var dy = to.y - from.y;

      var along, across;
      if (dir === "left")       { along = -dx; across = Math.abs(dy); }
      else if (dir === "right") { along =  dx; across = Math.abs(dy); }
      else if (dir === "up")    { along = -dy; across = Math.abs(dx); }
      else                      { along =  dy; across = Math.abs(dx); }

      if (along <= 1) continue;                 // not in this direction
      var score = along + across * 2.2;         // off-axis drift hurts
      if (score < bestScore) { bestScore = score; best = el; }
    }
    return best;
  }

  function markFocus(el) {
    var prev = document.querySelectorAll(".gp-focus");
    for (var i = 0; i < prev.length; i++) prev[i].classList.remove("gp-focus");
    if (!el) return;
    el.classList.add("gp-focus");
    try {
      el.focus({ preventScroll: true });
    } catch (e) {
      try { el.focus(); } catch (e2) {}
    }
    if (el.scrollIntoView) {
      el.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }

  function move(dir) {
    var next = pick(dir);
    if (next) markFocus(next);
  }

  function confirm_() {
    var el = document.activeElement;
    if (!el || el === document.body) return;
    if (isTextField(el)) return;              // Cross in a field would submit blind
    el.click();
  }

  function back() {
    var el = document.activeElement;
    if (isTextField(el)) { el.blur(); return; }
    // close whatever is open, in the order a person would expect
    var open = document.querySelector(".modes-menu, .audio-menu, .modal, .overlay");
    if (open) {
      document.dispatchEvent(new KeyboardEvent("keydown", {
        key: "Escape", code: "Escape", keyCode: 27, bubbles: true
      }));
      return;
    }
    if (el && el.blur) el.blur();
  }

  function toggleTvMode() {
    var root = document.documentElement;
    var on = root.classList.toggle("tv-mode");
    try { localStorage.setItem("uv_tv_mode", on ? "1" : "0"); } catch (e) {}
    announce(on ? "TV mode on" : "TV mode off");
  }

  /* A brief on-screen note. Controller users have no tooltips and no status
     bar, so state changes need to say so out loud. */
  function announce(text) {
    var n = document.getElementById("gp-toast");
    if (!n) {
      n = document.createElement("div");
      n.id = "gp-toast";
      n.setAttribute("role", "status");
      n.style.cssText =
        "position:fixed;left:50%;bottom:6vh;transform:translateX(-50%);z-index:400;" +
        "padding:10px 18px;border-radius:8px;font-family:inherit;font-size:1rem;" +
        "background:rgba(12,11,16,.94);color:#e8a24c;border:1px solid #b8933f;" +
        "pointer-events:none;transition:opacity .25s;";
      document.body.appendChild(n);
    }
    n.textContent = text;
    n.style.opacity = "1";
    clearTimeout(n._t);
    n._t = setTimeout(function () { n.style.opacity = "0"; }, 1600);
  }

  // ── the poll loop ────────────────────────────────────────────────────────

  var ACTIONS = {
    12: function () { move("up"); },
    13: function () { move("down"); },
    14: function () { move("left"); },
    15: function () { move("right"); }
  };

  function edge(index, pressed, now, repeats, fn) {
    if (!pressed) { delete state.held[index]; return; }
    var due = state.held[index];
    if (due === undefined) {                 // first press: fire immediately
      state.held[index] = now + REPEAT_DELAY;
      fn();
      return;
    }
    if (repeats && now >= due) {             // held: repeat
      state.held[index] = now + REPEAT_RATE;
      fn();
    }
  }

  function poll() {
    var pads = navigator.getGamepads ? navigator.getGamepads() : [];
    var pad = null;
    for (var i = 0; i < pads.length; i++) {
      if (pads[i] && pads[i].connected) { pad = pads[i]; break; }
    }

    if (pad) {
      var now = performance.now();
      var typing = isTextField(document.activeElement);
      var b = pad.buttons;

      // D-pad + left stick, both repeat while held
      for (var idx in ACTIONS) {
        if (!Object.prototype.hasOwnProperty.call(ACTIONS, idx)) continue;
        var pressed = b[idx] && b[idx].pressed;
        edge(idx, pressed && !typing, now, true, ACTIONS[idx]);
      }

      var ax = pad.axes[0] || 0, ay = pad.axes[1] || 0;
      edge("sx", !typing && Math.abs(ax) > STICK_DEADZONE, now, true, function () {
        move(ax < 0 ? "left" : "right");
      });
      edge("sy", !typing && Math.abs(ay) > STICK_DEADZONE, now, true, function () {
        move(ay < 0 ? "up" : "down");
      });

      // Cross/A confirm — never repeats
      edge(0, b[0] && b[0].pressed && !typing, now, false, confirm_);
      // Circle/B back — works while typing, so you can escape a field
      edge(1, b[1] && b[1].pressed, now, false, back);
      // Options/Menu toggles TV mode
      edge(9, b[9] && b[9].pressed, now, false, toggleTvMode);
    }

    state.raf = requestAnimationFrame(poll);
  }

  // ── lifecycle ────────────────────────────────────────────────────────────

  function start(pad) {
    if (state.active) return;
    state.active = true;
    state.raf = requestAnimationFrame(poll);
    var name = (pad && pad.id) || "controller";
    var isDual = /dualsense|dualshock|playstation|wireless controller/i.test(name);
    announce((isDual ? "DualSense" : "Controller") +
             " connected · Options for TV mode");
    // give focus somewhere sensible so the first D-pad press has an anchor
    if (document.activeElement === document.body) {
      var first = candidates()[0];
      if (first) markFocus(first);
    }
  }

  window.addEventListener("gamepadconnected", function (e) { start(e.gamepad); });
  window.addEventListener("gamepaddisconnected", function () {
    var pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (var i = 0; i < pads.length; i++) if (pads[i] && pads[i].connected) return;
    if (state.raf) cancelAnimationFrame(state.raf);
    state.active = false;
    var prev = document.querySelectorAll(".gp-focus");
    for (var j = 0; j < prev.length; j++) prev[j].classList.remove("gp-focus");
  });

  // A pad already held at load only appears after the first input event.
  window.addEventListener("load", function () {
    var pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (var i = 0; i < pads.length; i++) {
      if (pads[i] && pads[i].connected) { start(pads[i]); return; }
    }
  });

  // restore TV mode: explicit setting, or ?tv=1
  try {
    var q = /[?&]tv=1\b/.test(window.location.search);
    if (q || localStorage.getItem("uv_tv_mode") === "1") {
      document.documentElement.classList.add("tv-mode");
    }
  } catch (e) {}

  /* `move` and `pick` are exposed deliberately: they make the spatial
     navigation testable without a physical controller, and let you drive the
     UI from a console when something is unreachable on a TV. */
  window.UV_GAMEPAD = {
    toggleTvMode: toggleTvMode,
    announce: announce,
    move: move,
    pick: pick,
    candidates: candidates
  };
})();
