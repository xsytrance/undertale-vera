/* ════════════════════════════════════════════════════════════════════════
   gamepad_nav_test.js — spatial navigation regression for static/js/gamepad.js

   Run:  node tools/gamepad_nav_test.js        (exit 0 = pass)

   Docked to a TV the controller is the ONLY input, so if directional
   navigation picks the wrong element the app is simply unusable — there's no
   mouse to fall back on. The scoring in `pick()` is pure geometry, so it can
   be checked without a browser or a physical pad.

   Runs on a shimmed DOM rather than a real one: the geometry only ever reads
   getBoundingClientRect(), so fake rects exercise the real code path. Pytest
   doesn't cover this (it's browser JS), and the Playwright smoke can't drive a
   gamepad, which is why it lives here as its own check.
   ════════════════════════════════════════════════════════════════════════ */
"use strict";

const path = require("path");

// Node >= 21 defines a read-only `navigator`; plain assignment is silently
// dropped, which makes gamepad.js take its no-support early return.
Object.defineProperty(globalThis, "navigator", {
  value: { getGamepads: () => [] }, writable: true, configurable: true
});

global.performance = { now: () => 0 };
global.localStorage = { getItem: () => null, setItem() {} };
global.requestAnimationFrame = () => 1;
global.cancelAnimationFrame = () => {};
global.KeyboardEvent = class {};

function mk(name, x, y, w, h) {
  w = w || 80; h = h || 40;
  return {
    name, disabled: false, tagName: "BUTTON",
    classList: { add() {}, remove() {} }, style: {},
    focus() {}, blur() {}, click() {}, scrollIntoView() {},
    getAttribute: () => null,
    getBoundingClientRect: () => ({
      left: x, top: y, width: w, height: h, bottom: y + h, right: x + w
    })
  };
}

/*  A(0,0)    B(100,0)    C(200,0)
    D(0,80)   E(100,80)   F(200,80)   */
const els = [
  mk("A", 0, 0), mk("B", 100, 0), mk("C", 200, 0),
  mk("D", 0, 80), mk("E", 100, 80), mk("F", 200, 80)
];

global.document = {
  activeElement: null, body: {},
  documentElement: { classList: { add() {}, toggle: () => true } },
  querySelectorAll: (sel) => (sel === ".gp-focus" ? [] : els),
  querySelector: () => null, getElementById: () => null,
  createElement: () => ({ style: {}, setAttribute() {},
                          classList: { add() {}, remove() {} } }),
  dispatchEvent() {}, addEventListener() {}
};
global.window = {
  addEventListener() {}, location: { search: "" },
  getComputedStyle: () => ({ visibility: "visible", display: "block", opacity: "1" }),
  innerHeight: 800
};

require(path.join(__dirname, "..", "static", "js", "gamepad.js"));
const gp = global.window.UV_GAMEPAD;

if (!gp) {
  console.error("FAIL gamepad.js exported nothing — it returned early");
  process.exit(1);
}

const cases = [
  ["A", "right", "B"],   // straight across
  ["A", "down", "D"],    // straight down
  ["B", "left", "A"],
  ["E", "right", "F"],
  ["D", "right", "E"],
  ["F", "up", "C"],      // up a column
  ["C", "right", null],  // nothing to the right — must not wrap
  ["A", "up", null],     // nothing above — must not wrap
  ["D", "up", "A"]
];

let pass = 0;
for (const [from, dir, want] of cases) {
  document.activeElement = els.find((e) => e.name === from);
  const got = gp.pick(dir);
  const name = got ? got.name : null;
  const ok = name === want;
  if (ok) pass++;
  console.log(`${ok ? "ok  " : "FAIL"} ${from} + ${dir.padEnd(5)} -> ` +
              `${String(name).padEnd(4)} (want ${want})`);
}

// off-axis preference: a close-but-skewed target must lose to an aligned one
els.push(mk("SKEW", 105, 300));
document.activeElement = els.find((e) => e.name === "A");
const down = gp.pick("down");
const alignedWins = down && down.name === "D";
console.log(`${alignedWins ? "ok  " : "FAIL"} aligned target beats a skewed one ` +
            `-> ${down && down.name} (want D)`);
if (alignedWins) pass++;

const total = cases.length + 1;
console.log(`\n${pass}/${total} spatial navigation cases passed`);
process.exit(pass === total ? 0 : 1);
