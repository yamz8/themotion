// Flexoki orb.
// A single ink pixel blinks on the paper like a cursor, then springs open into
// a dark dithered ball. Light tips in and swings like a pendulum: the shadow
// sweeps across the ball, the lit side dissolves into the paper, and the
// dither settles cell by cell onto the wallpaper's.
themotion.scene({
  beats: { cursor: 0.7, inflate: 1.35, light: 2.3, rest: 3.9 },
  idleLength: 8,

  setup(api) {
    const m = api.meta
    this.paper = `rgb(${m.paper.join(",")})`
    this.ink = `rgb(${m.ink.map(Math.round).join(",")})`
    const [x0, y0, x1, y1] = m.box
    this.box = { x0, y0, cols: x1 - x0, rows: y1 - y0 }
    this.sphere = m.sphere
    this.final = this.light(m.shade)

    // Per-cell nudges that make the fitted shading dither to exactly the
    // wallpaper's cells under the final light.
    const { cols, rows } = this.box, cx = m.sphere[0], cy = m.sphere[1]
    this.nudge = new Float32Array(cols * rows)
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
      const gi = x0 + i, gj = y0 + j, bit = m.bits[j][i] === "1"
      const tone = this.tone(gi, gj, cx, cy, m.sphere[2], this.final), thr = this.threshold(gi, gj, m)
      if (bit && tone <= thr) this.nudge[j * cols + i] = thr - tone + 1e-4
      else if (!bit && tone > thr) this.nudge[j * cols + i] = thr - tone - 1e-4
    }
  },

  // Shading as ambient `a`, light direction `dir` (unit), strength `k` and gamma.
  light(p) {
    const k = Math.hypot(p[1], p[2], p[3])
    return { a: p[0], dir: [p[1] / k, p[2] / k, p[3] / k], k, gamma: p[4] }
  },

  // Ink tone 0..1 of cell (i, j) on a sphere at (cx, cy) with radius r, in cells.
  tone(i, j, cx, cy, r, L) {
    const nx = (i - cx) / r, ny = (j - cy) / r, q = nx * nx + ny * ny
    if (q >= 1) return 0
    const v = L.a + L.k * (L.dir[0] * nx + L.dir[1] * ny + L.dir[2] * Math.sqrt(1 - q))
    return Math.pow(themotion.clamp(v), L.gamma)
  },

  threshold(i, j, m) {
    return (m.bayer[(j + m.phase[1]) % 4][(i + m.phase[0]) % 4] + 0.5) / 16
  },

  // Dither the sphere: scale s about its centre, light L, nudges weighted by w.
  orb(ctx, api, s, L, w) {
    const m = api.meta, c = m.cell, [ox, oy] = m.origin, [cx, cy, R] = this.sphere, r = R * s
    const { x0, y0, cols, rows } = this.box
    if (r < 0.5) return
    ctx.fillStyle = this.ink
    ctx.beginPath()
    for (let j = Math.floor(cy - r); j <= Math.ceil(cy + r); j++) {
      for (let i = Math.floor(cx - r); i <= Math.ceil(cx + r); i++) {
        let tone = this.tone(i, j, cx, cy, r, L)
        const bi = i - x0, bj = j - y0
        if (w > 0 && bi >= 0 && bj >= 0 && bi < cols && bj < rows) tone += w * this.nudge[bj * cols + bi]
        if (tone > this.threshold(i, j, m)) ctx.rect(ox + i * c, oy + j * c, c, c)
      }
    }
    ctx.fill()
  },

  // The final light tipped to polar angle `tilt` (0 faces the viewer, which
  // leaves the ball dark all over), turned by `swing` radians about the view
  // axis, with ambient `a`.
  aim(tilt, swing, a) {
    const F = this.final, [x, y, z] = F.dir
    const phi = Math.atan2(y, x) + swing, theta = Math.acos(themotion.clamp(z, -1, 1)) * tilt
    return { ...F, a, dir: [Math.sin(theta) * Math.cos(phi), Math.sin(theta) * Math.sin(phi), Math.cos(theta)] }
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, lerp, meta } = api
    ctx.fillStyle = this.paper; ctx.fillRect(0, 0, W, H)

    // A cursor blinks where the orb will be.
    const [cx, cy] = this.sphere, c = meta.cell
    if ((t > 0.7 && t < 0.95) || (t > 1.15 && t < 1.45)) {
      ctx.fillStyle = this.ink
      ctx.fillRect(meta.origin[0] + (Math.round(cx) - 1) * c, meta.origin[1] + (Math.round(cy) - 1) * c, 2 * c, 2 * c)
    }

    // It springs open into a ball, dark all over...
    const s = lerp(ease.spring(seg(t, 1.35, 2.4), 6, 9), 1, ease.inOutCubic(seg(t, 2.2, 2.6)))
    // ...then the light tips in and swings like a pendulum, the shadow
    // sweeping across the ball before it comes to rest.
    const tip = ease.inOutCubic(seg(t, 2.3, 3.1)), p = seg(t, 2.3, 4.3)
    const swing = lerp(1.3 * Math.exp(-3.2 * p) * Math.cos(api.TAU * 1.1 * p), 0, ease.inOutCubic(seg(t, 3.9, 4.4)))
    const L = this.aim(tip, swing, lerp(0.35, this.final.a, tip))
    this.orb(ctx, api, s, L, ease.inOutCubic(seg(t, 3.9, 4.4)))

    // The dither is now the wallpaper's cell for cell; fade onto the still so
    // its ink fringe arrives gently, well before the handoff.
    const f = ease.inOutCubic(seg(t, 4.35, 4.85))
    if (f > 0) { ctx.globalAlpha = f; ctx.drawImage(api.still, 0, 0, W, H); ctx.globalAlpha = 1 }
  },

  // The light sways gently around its resting place and returns every idleLength.
  idle(ctx, t, api) {
    const { W, H, TAU } = api, p = TAU * t / this.idleLength
    ctx.fillStyle = this.paper; ctx.fillRect(0, 0, W, H)
    const F = this.final, d = [F.dir[0] + 0.12 * Math.sin(p), F.dir[1] + 0.08 * Math.sin(2 * p), F.dir[2]]
    const len = Math.hypot(...d)
    this.orb(ctx, api, 1, { ...F, dir: d.map(v => v / len) }, 1 - Math.abs(Math.sin(p / 2)))
  },
})
