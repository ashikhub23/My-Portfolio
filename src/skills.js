// Skills & tools as a small orrery: three tilted rings of logos orbiting a
// glowing core. Same discipline as the other scenes - one clock, staged beats
// (wake -> rim lights flicker on -> a spark sweeps each ring -> logos surface
// far-to-near -> core speaks -> live), then the pointer and scroll own it.
//
// Plain 2D canvas for the rings, embers and glow; the logos are real <button>s
// so they are focusable, named and clickable. Runs only while on screen.

const TAU = Math.PI * 2;
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const ease = (v) => v * v * (3 - 2 * v);
const easeOut = (v) => 1 - Math.pow(1 - v, 3);
const easeBack = (v) => { const c = 1.70158; return 1 + (c + 1) * Math.pow(v - 1, 3) + c * Math.pow(v - 1, 2); };
const span = (a, b, t) => clamp((t - a) / (b - a));

// seconds from the moment the section is first seen
const T = { wake: [0, 0.9], rings: [0.35, 1.5], spark: [0.7, 2.1], items: [1.1, 3.1], core: [1.5, 2.4], live: 3.2 };

const RINGS = [
  { r: 0.36, y: 0.10, speed: 0.20, dir: 1 },
  { r: 0.62, y: 0.00, speed: 0.14, dir: -1 },
  { r: 0.88, y: -0.10, speed: 0.095, dir: 1 },
];

export function initSkills() {
  const root = document.getElementById('orbit');
  if (!root) return;
  const section = root.closest('.skills');
  const cv = root.querySelector('.orbit__cv');
  const core = root.querySelector('.orbit__core');
  const kEl = root.querySelector('.orbit__k');
  const vEl = root.querySelector('.orbit__v');
  const sEl = root.querySelector('.orbit__s');
  const ctx = cv.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover: hover)').matches;

  // ---- data from the markup ------------------------------------------------
  const buttons = [...root.querySelectorAll('.ob')];
  const items = buttons.map((el) => ({
    el,
    ring: +el.dataset.ring,
    name: el.dataset.name,
    groups: el.dataset.group.split('|'),
    k: 0, n: 0, order: 0,
    hot: 0, dim: 0, shown: 0,
  }));
  RINGS.forEach((_, ri) => {
    const on = items.filter((i) => i.ring === ri);
    on.forEach((i, k) => { i.k = k; i.n = on.length; });
  });
  // far -> near surfacing order: outer ring first, as the gallery builds from the back
  [...items].sort((a, b) => b.ring - a.ring || a.k - b.k).forEach((i, o) => { i.order = o; });
  const legend = [...section.querySelectorAll('.orbit__legend button')];
  const groupItems = (g) => items.filter((i) => i.groups.includes(g)).map((i) => i.name);

  // ---- state -----------------------------------------------------------------
  let W = 0, H = 0, dpr = 1, U = 300, sx = 1, tile = 64;
  let started = false, t0 = 0, visible = false, raf = 0, last = 0;
  const angle = RINGS.map((_, i) => i * 1.7);
  let spin = 0;                              // scroll-driven extra spin
  let scrollY = scrollY0();
  const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
  let hovered = -1, pinned = -1, hoverGroup = null, lockGroup = null;
  const embers = Array.from({ length: 70 }, (_, i) => ({
    x: Math.random(), y: Math.random(), v: 0.02 + Math.random() * 0.05,
    r: 0.6 + Math.random() * 1.6, a: 0.15 + Math.random() * 0.45, p: Math.random() * TAU, d: i,
  }));

  function scrollY0() { return window.scrollY || 0; }

  // ---- readout in the core -----------------------------------------------------
  const idle = () => ({ k: 'Skills & tools', v: `${items.length} logos`, s: fine ? 'Hover to explore' : 'Tap to explore' });
  function readout() {
    const sel = pinned >= 0 ? pinned : hovered;
    const g = lockGroup || hoverGroup;
    let r;
    if (sel >= 0) r = { k: items[sel].groups[0], v: items[sel].name, s: '' };
    else if (g) r = { k: 'Group', v: g, s: groupItems(g).join(' \u00b7 ') };
    else r = idle();
    kEl.textContent = r.k; vEl.textContent = r.v; sEl.textContent = r.s;
  }

  // ---- sizing ---------------------------------------------------------------------
  function resize() {
    const r = root.getBoundingClientRect();
    W = r.width; H = r.height;
    dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    tile = clamp(W * 0.058, 46, 76);
    root.style.setProperty('--tile', `${tile}px`);
    sx = W > 900 ? 1.38 : W > 600 ? 1.2 : 1.0;
    const half = tile / 2 + 10;
    const outer = RINGS[2].r;
    const uX = (W / 2 - half) / (outer * sx);
    const sinP = Math.sin(0.86);
    const uY = (H / 2 - half - 8) / (outer * sinP + 0.12 * sinP);
    U = Math.max(120, Math.min(uX, uY));
    core.style.setProperty('--core', `${clamp(RINGS[0].r * U * sx * 1.35, 104, 168)}px`);
  }

  // ---- projection: circle in a tilted plane, viewed from above ---------------------
  const PITCH = 0.86;
  function project(R, th, yo, pitch, yawX, yawY, scale) {
    const X = R * Math.cos(th) * U * sx * scale;
    const Z = R * Math.sin(th) * U * scale;
    const Y = yo * U * scale;
    const sp = Math.sin(pitch), cp = Math.cos(pitch);
    const zc = Z * cp + Y * sp;                      // toward the camera
    const f = U * 2.8;
    const pf = f / (f - zc);
    return {
      x: W / 2 + yawX + X * pf,
      y: H / 2 + yawY + (Z * sp - Y * cp) * pf,
      zc, pf, depth: clamp((zc / (U * 0.95) + 1) / 2),
    };
  }

  // ---- frame ---------------------------------------------------------------------------
  function frame(now) {
    raf = visible ? requestAnimationFrame(frame) : 0;
    const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
    last = now;
    const t = started ? (reduced ? 99 : (now - t0) / 1000) : 0;

    // pointer + scroll
    mouse.x = lerp(mouse.x, mouse.tx, 0.06);
    mouse.y = lerp(mouse.y, mouse.ty, 0.06);
    const sy = window.scrollY;
    spin = spin * Math.pow(0.04, dt) + (sy - scrollY) * 0.0016;   // scrolling spins the rings
    scrollY = sy;
    const rect = root.getBoundingClientRect();
    const sp = clamp((rect.top + rect.height / 2 - innerHeight / 2) / innerHeight, -1, 1);
    const pitch = PITCH + mouse.y * 0.07 + sp * 0.06;
    const yawX = mouse.x * 26, yawY = mouse.y * 14 + sp * 10;
    const dolly = 1 + (1 - Math.abs(sp)) * 0.05;

    const wake = ease(span(...T.wake, t));
    const sel = pinned >= 0 ? pinned : hovered;
    const grp = lockGroup || hoverGroup;

    // ring angles; the ring holding the pointer slows almost to a stop
    RINGS.forEach((rg, i) => {
      const holding = sel >= 0 && items[sel].ring === i;
      const target = (reduced || !started || t < T.live - 0.6) ? (reduced ? 0 : 0.35) : (holding ? 0.04 : 1);
      rg.mul = lerp(rg.mul ?? 1, target, 0.08);
      angle[i] += dt * rg.speed * rg.dir * rg.mul + spin * rg.dir * (1 + i * 0.35) * (reduced ? 0 : 1);
    });

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const cx = W / 2 + yawX, cy = H / 2 + yawY;

    // ---- core glow ----
    const pulse = 0.88 + 0.12 * Math.sin(now / 900);
    const gr = U * 0.95;
    const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, gr);
    g.addColorStop(0, `rgba(222,27,28,${0.55 * wake * pulse})`);
    g.addColorStop(0.35, `rgba(150,12,14,${0.28 * wake})`);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    // light column up from the core, like the gallery's overhead structure
    const col = ctx.createLinearGradient(0, 0, 0, cy);
    col.addColorStop(0, 'rgba(255,120,90,0)');
    col.addColorStop(1, `rgba(255,90,70,${0.09 * wake})`);
    ctx.fillStyle = col;
    ctx.fillRect(cx - U * 0.09, 0, U * 0.18, cy);

    // ---- rings ----
    RINGS.forEach((rg, ri) => {
      const ignite = span(T.rings[0] + ri * 0.18, T.rings[1] + ri * 0.18, t);
      const flick = ignite >= 1 ? 1 : ignite * (0.5 + 0.5 * Math.abs(Math.sin(ignite * 19)));
      const a = (reduced ? 1 : flick);
      if (a <= 0) return;
      const N = 140;
      const pts = [];
      for (let s = 0; s <= N; s++) pts.push(project(rg.r, (s / N) * TAU, rg.y, pitch, yawX, yawY, dolly));
      for (const front of [false, true]) {                    // back half dim, front half bright
        ctx.beginPath();
        let pen = false;
        for (let s = 0; s <= N; s++) {
          const p = pts[s];
          if ((p.zc > 0) === front) { pen ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y); pen = true; } else pen = false;
        }
        ctx.strokeStyle = front ? `rgba(255,80,70,${0.58 * a})` : `rgba(222,27,28,${0.3 * a})`;
        ctx.lineWidth = front ? 1.3 : 1;
        ctx.stroke();
      }
      // tick marks
      for (let s = 0; s < 48; s++) {
        const p = pts[Math.floor((s / 48) * N)];
        ctx.fillStyle = `rgba(244,226,206,${(p.zc > 0 ? 0.28 : 0.1) * a})`;
        ctx.fillRect(p.x - 0.8, p.y - 0.8, 1.6, 1.6);
      }
      // travelling highlight (and the ignition spark that sweeps once)
      const sweep = span(T.spark[0] + ri * 0.2, T.spark[1] + ri * 0.2, t);
      const hl = angle[ri] * 1.6 + ri * 2.0;
      const arcs = [[hl, 0.9, 0.7]];
      if (sweep > 0 && sweep < 1) arcs.push([sweep * TAU * 1.4, 0.35, 1.0]);
      for (const [start, len, strength] of arcs) {
        ctx.beginPath();
        for (let s = 0; s <= 24; s++) {
          const p = project(rg.r, start + (s / 24) * len, rg.y, pitch, yawX, yawY, dolly);
          s ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
        }
        // glow = a wide faint pass under a thin bright one (shadowBlur is far too slow)
        ctx.lineCap = 'round';
        ctx.strokeStyle = `rgba(255,50,40,${0.22 * strength * a})`;
        ctx.lineWidth = 8;
        ctx.stroke();
        ctx.strokeStyle = `rgba(255,150,120,${0.9 * strength * a})`;
        ctx.lineWidth = 2.2;
        ctx.stroke();
      }
    });

    // ---- logos ----
    const placed = items.map((it) => {
      const rg = RINGS[it.ring];
      const lt = clamp((span(...T.items, t) * 1.0) * 1.55 - it.order * 0.045, 0, 1) ;
      const ip = reduced ? 1 : clamp(lt / 0.55);
      const rad = lerp(0.0, 1, easeBack(ip));
      const th = angle[it.ring] + (it.k / it.n) * TAU + it.ring * 0.6;
      const p = project(rg.r * rad, th, rg.y * rad, pitch, yawX, yawY, dolly);
      return { it, p, ip };
    });
    for (const { it, p, ip } of placed) {
      it.hot = lerp(it.hot, items.indexOf(it) === sel ? 1 : 0, 0.18);
      const dimT = grp && !it.groups.includes(grp) ? 1 : 0;
      it.dim = lerp(it.dim, dimT, 0.14);
      const depthA = lerp(0.42, 1, p.depth);
      const op = clamp(ip * 1.6) * depthA * (1 - 0.84 * it.dim);
      const sc = lerp(0.74, 1.14, p.depth) * p.pf * (0.4 + 0.6 * easeOut(ip)) * (1 + 0.42 * it.hot);
      it.el.style.transform = `translate3d(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px,0) translate(-50%,-50%) scale(${sc.toFixed(3)})`;
      it.el.style.opacity = op.toFixed(3);
      it.el.style.zIndex = String(10 + Math.round(p.depth * 100) + Math.round(it.hot * 200));
      it.el.style.filter = ip < 1 ? `blur(${((1 - ip) * 7).toFixed(1)}px)` : 'none';
      it.el.classList.toggle('is-hot', it.hot > 0.5);
      it.p = p;
    }

    // line from the core to the chosen logo + a ring around it
    if (sel >= 0 && items[sel].p) {
      const p = items[sel].p;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(p.x, p.y);
      ctx.strokeStyle = 'rgba(255,60,50,0.55)';
      ctx.setLineDash([3, 6]);
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(p.x, p.y, tile * 0.78 * lerp(0.74, 1.14, p.depth), 0, TAU);
      ctx.strokeStyle = 'rgba(255,40,30,0.25)';
      ctx.lineWidth = 7;
      ctx.stroke();
      ctx.strokeStyle = 'rgba(255,80,70,0.85)';
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }

    // ---- embers, additive, drifting up through everything ----
    if (!reduced) {
      ctx.globalCompositeOperation = 'lighter';
      for (const e of embers) {
        e.y -= e.v * dt;
        if (e.y < -0.05) { e.y = 1.05; e.x = Math.random(); }
        const x = (e.x + Math.sin(now / 2600 + e.p) * 0.012) * W, y = e.y * H;
        ctx.beginPath();
        ctx.arc(x, y, e.r, 0, TAU);
        ctx.fillStyle = `rgba(255,${90 + (e.d % 5) * 20},60,${e.a * wake * 0.55})`;
        ctx.fill();
      }
      ctx.globalCompositeOperation = 'source-over';
    }

    // ---- the core overlay follows the glow ----
    const coreIn = ease(span(...T.core, t));
    core.style.transform = `translate(${cx.toFixed(1)}px,${cy.toFixed(1)}px) translate(-50%,-50%) scale(${(0.6 + 0.4 * coreIn).toFixed(3)})`;
    core.style.opacity = coreIn.toFixed(3);
  }

  function start() { if (!raf && visible) { last = performance.now(); raf = requestAnimationFrame(frame); } }

  // ---- interaction ---------------------------------------------------------------
  items.forEach((it, i) => {
    const b = it.el;
    b.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') { hovered = i; readout(); } });
    b.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && hovered === i) { hovered = -1; readout(); } });
    b.addEventListener('focus', () => { hovered = i; readout(); });
    b.addEventListener('blur', () => { if (hovered === i) { hovered = -1; readout(); } });
    b.addEventListener('click', () => { pinned = pinned === i ? -1 : i; readout(); });
  });
  legend.forEach((b) => {
    const g = b.dataset.group;
    b.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') { hoverGroup = g; readout(); } });
    b.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse') { hoverGroup = null; readout(); } });
    b.addEventListener('focus', () => { hoverGroup = g; readout(); });
    b.addEventListener('blur', () => { hoverGroup = null; readout(); });
    b.addEventListener('click', () => {
      lockGroup = lockGroup === g ? null : g;
      pinned = -1;
      legend.forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.group === lockGroup)));
      readout();
    });
  });
  root.addEventListener('pointermove', (e) => {
    const r = root.getBoundingClientRect();
    mouse.tx = ((e.clientX - r.left) / r.width - 0.5) * 2;
    mouse.ty = ((e.clientY - r.top) / r.height - 0.5) * 2;
  });
  root.addEventListener('pointerleave', () => { mouse.tx = 0; mouse.ty = 0; });
  document.addEventListener('click', (e) => {            // tap outside clears a pinned logo
    if (pinned >= 0 && !e.target.closest('.ob')) { pinned = -1; readout(); }
  });

  new ResizeObserver(resize).observe(root);
  resize();
  readout();
  section.classList.add('is-orbit');

  new IntersectionObserver((entries) => {
    for (const en of entries) {
      visible = en.isIntersecting;
      if (visible && !started) { started = true; t0 = performance.now(); }
      if (visible) start();
    }
  }, { threshold: 0.18 }).observe(root);
}
