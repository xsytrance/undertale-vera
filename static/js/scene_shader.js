/* ShaderField — the living, route-reactive backdrop (WebGL).
 *
 * A fullscreen fragment shader behind everything: a slow drifting ember/haze field
 * colour-graded by the save's ROUTE. Pacifist drifts warm and gold; Genocide
 * desaturates to ash and CORRUPTS (scanline tear, RGB split, glitch bursts);
 * undetermined is a cold murk. A `glitch()` pulse is the hook for the Fun-value
 * anomaly — when the save brushes a Gaster threshold, the field tears for a beat.
 *
 * Pure vanilla, no build step. Degrades cleanly: if WebGL is unavailable,
 * `supported` stays false and scene.js keeps the CSS gradient fallback. */
(function () {
  "use strict";

  var VERT =
    "attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }";

  var FRAG = [
    "precision mediump float;",
    "uniform float uTime; uniform vec2 uRes;",
    "uniform vec3 uColA; uniform vec3 uColB;",
    "uniform float uCorrupt; uniform float uGlitch; uniform float uEmber;",
    "float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }",
    "float noise(vec2 p){ vec2 i=floor(p), f=fract(p);",
    "  float a=hash(i), b=hash(i+vec2(1.,0.)), c=hash(i+vec2(0.,1.)), d=hash(i+vec2(1.,1.));",
    "  vec2 u=f*f*(3.-2.*f); return mix(mix(a,b,u.x),mix(c,d,u.x),u.y); }",
    "float fbm(vec2 p){ float s=0.,a=.5; for(int i=0;i<5;i++){ s+=a*noise(p); p*=2.02; a*=.5;} return s; }",
    "void main(){",
    "  vec2 uv = gl_FragCoord.xy / uRes;",
    "  vec2 p = uv; p.x *= uRes.x/uRes.y;",
    "  float g = uGlitch + uCorrupt*0.6;",
    // horizontal band tearing (corruption + glitch bursts)
    "  float band = step(0.62, hash(vec2(floor(uv.y*42.0), floor(uTime*9.0))));",
    "  uv.x += (hash(vec2(floor(uv.y*30.0), floor(uTime*13.0)))-0.5) * g * band * 0.07;",
    "  p = uv; p.x *= uRes.x/uRes.y;",
    // drifting haze
    "  float n  = fbm(p*2.5 + vec2(uTime*0.05, -uTime*0.08));",
    "  float n2 = fbm(p*5.0 - vec2(uTime*0.03,  uTime*0.06));",
    "  float field = mix(n, n2, 0.5);",
    "  vec3 col = mix(uColA, uColB, smoothstep(0.15, 0.85, field));",
    // rising ember flecks
    "  float em = 0.0;",
    "  for(int i=0;i<3;i++){ float fi=float(i);",
    "    vec2 ep = p*8.0 + vec2(fi*13.1, -uTime*(0.6+fi*0.22));",
    "    vec2 gid=floor(ep); vec2 lf=fract(ep)-0.5;",
    "    float h=hash(gid+fi*7.0); float tw=0.5+0.5*sin(uTime*3.0+h*31.0);",
    "    em += smoothstep(0.42,0.0,length(lf))*step(0.93,h)*tw; }",
    "  col += uColB * em * uEmber * 1.3;",
    // scanlines (stronger under corruption)
    "  float scan = 0.92 + 0.08*sin(uv.y*uRes.y*1.4);",
    "  col *= mix(1.0, scan, 0.3 + 0.5*uCorrupt);",
    // cheap RGB split on glitch/corruption
    "  col.r += g*0.10*sin(uv.y*80.0 + uTime*20.0);",
    "  col.b -= g*0.08*sin(uv.y*70.0 - uTime*15.0);",
    // desaturate toward ash under corruption
    "  float lum = dot(col, vec3(0.299,0.587,0.114));",
    "  col = mix(col, vec3(lum)*vec3(1.05,0.96,0.9), uCorrupt*0.5);",
    // vignette + backdrop dim
    "  col *= smoothstep(1.25, 0.30, length(uv-0.5));",
    "  col *= 0.85;",
    "  gl_FragColor = vec4(col, 1.0);",
    "}"
  ].join("\n");

  // route → {a:[r,g,b], b:[r,g,b], corrupt, ember}  (0..1 colours)
  var PALETTES = {
    pacifist:     { a: [0.07, 0.06, 0.04], b: [0.91, 0.63, 0.30], corrupt: 0.0, ember: 1.0 },
    neutral:      { a: [0.05, 0.05, 0.07], b: [0.42, 0.36, 0.54], corrupt: 0.08, ember: 0.5 },
    genocide:     { a: [0.06, 0.03, 0.04], b: [0.56, 0.18, 0.23], corrupt: 0.85, ember: 0.7 },
    undetermined: { a: [0.05, 0.05, 0.06], b: [0.16, 0.20, 0.25], corrupt: 0.0, ember: 0.25 }
  };

  var gl, prog, canvas, raf = 0, start = 0;
  var u = {};                       // uniform locations
  // current + target animated state (lerped each frame)
  var cur = { a: [0.05,0.05,0.06], b: [0.16,0.20,0.25], corrupt: 0, ember: 0.25 };
  var tgt = { a: cur.a.slice(), b: cur.b.slice(), corrupt: 0, ember: 0.25 };
  var glitch = 0;                   // decays toward 0
  var supported = false;

  function compile(type, src) {
    var s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      console.warn("ShaderField compile failed:", gl.getShaderInfoLog(s)); return null;
    }
    return s;
  }

  function resize() {
    if (!canvas) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.floor(innerWidth * dpr);
    canvas.height = Math.floor(innerHeight * dpr);
    if (gl) gl.viewport(0, 0, canvas.width, canvas.height);
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  function frame(now) {
    if (!start) start = now;
    var t = (now - start) / 1000;
    var k = 0.05;                                   // transition smoothing
    for (var i = 0; i < 3; i++) {
      cur.a[i] = lerp(cur.a[i], tgt.a[i], k);
      cur.b[i] = lerp(cur.b[i], tgt.b[i], k);
    }
    cur.corrupt = lerp(cur.corrupt, tgt.corrupt, k);
    cur.ember = lerp(cur.ember, tgt.ember, k);
    glitch *= 0.90;                                 // glitch pulse decay

    gl.uniform1f(u.uTime, t);
    gl.uniform2f(u.uRes, canvas.width, canvas.height);
    gl.uniform3fv(u.uColA, cur.a);
    gl.uniform3fv(u.uColB, cur.b);
    gl.uniform1f(u.uCorrupt, cur.corrupt);
    gl.uniform1f(u.uEmber, cur.ember);
    gl.uniform1f(u.uGlitch, Math.min(glitch, 1.0));
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    raf = requestAnimationFrame(frame);
  }

  function init(canvasEl) {
    canvas = canvasEl;
    try {
      gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    } catch (e) { gl = null; }
    if (!gl) { supported = false; return false; }

    var vs = compile(gl.VERTEX_SHADER, VERT), fs = compile(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) { supported = false; return false; }
    prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { supported = false; return false; }
    gl.useProgram(prog);

    // fullscreen triangle
    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    ["uTime", "uRes", "uColA", "uColB", "uCorrupt", "uGlitch", "uEmber"].forEach(function (n) {
      u[n] = gl.getUniformLocation(prog, n);
    });

    supported = true;
    resize();
    window.addEventListener("resize", resize);
    raf = requestAnimationFrame(frame);
    return true;
  }

  function setRoute(route) {
    var key = (route || "undetermined").toLowerCase();
    var pal = PALETTES[key] || PALETTES.undetermined;
    tgt.a = pal.a.slice(); tgt.b = pal.b.slice();
    tgt.corrupt = pal.corrupt; tgt.ember = pal.ember;
  }

  // a one-shot tear — the Fun-value anomaly hook
  function pulse(strength) { glitch = Math.max(glitch, strength || 1.0); }

  window.ShaderField = {
    init: init, setRoute: setRoute, pulse: pulse,
    get supported() { return supported; }
  };
})();
