// Flexoki orb.
// A single ink block blinks on the paper like a cursor, then the ball grows
// out of it dot by dot. Light swings in like a pendulum, clearing the dots it
// falls on, and comes to rest on the wallpaper's own shading.
// Every dot drawn is one of the wallpaper's, cut from the still at its exact
// place, so once the light rests the frame already is the wallpaper.
themotion.scene({
  beats: { cursor: 0.7, grow: 1.45, light: 2.4, rest: 4.4 },
  idleLength: 8,

  setup(api) {
    const m = api.meta
    this.paper = `rgb(${m.paper.join(",")})`
    const [x0, y0, x1, y1] = m.box
    const cols = x1 - x0, rows = y1 - y0
    this.box = { x0, y0, cols, rows }
    this.final = this.light(m.shade)
    const [cx, cy, R] = this.sphere = m.sphere

    // The wallpaper's ink cells, with their tone under the resting light.
    const bits = m.bits.join("")
    this.cells = []
    for (let k = 0; k < bits.length; k++) {
      if (bits[k] !== "1") continue
      const i = x0 + k % cols, j = y0 + Math.floor(k / cols)
      this.cells.push({ i, j, rest: this.tone(i, j, cx, cy, R, this.final) })
    }
    const ink = new Set(this.cells.map(c => c.j * 1e5 + c.i))

    // The cursor is the wallpaper's own 2x2 ink block nearest the centre.
    let best = Infinity
    for (const { i, j } of this.cells) {
      const d = Math.hypot(i + 0.5 - cx, j + 0.5 - cy)
      if (d < best && [[1, 0], [0, 1], [1, 1]].every(([a, b]) => ink.has((j + b) * 1e5 + i + a))) {
        best = d; this.cursor = [i, j]
      }
    }

    // The ball grows from the cursor: each dot appears once the growth
    // passes it, give or take a random lag, so the edge is ragged dot by dot.
    const r = api.rng(0x0eb), [ci, cj] = this.cursor
    for (const c of this.cells) {
      c.grow = Math.hypot(c.i - ci - 0.5, c.j - cj - 0.5) + 0.15 * R * r()
      c.clear = 0.03 + 0.2 * r()
    }
    this.reach = Math.max(...this.cells.map(c => c.grow))
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

  // Draw the wallpaper's own ink cells that pass `show`, cut from the still.
  dots(ctx, api, show) {
    const m = api.meta, c = m.cell, [ox, oy] = m.origin
    ctx.save()
    ctx.beginPath()
    for (const cell of this.cells) if (show(cell)) ctx.rect(ox + cell.i * c, oy + cell.j * c, c, c)
    ctx.clip()
    ctx.drawImage(api.still, 0, 0, api.W, api.H)
    ctx.restore()
  },

  // A cell stays inked unless light L makes it clearly lighter than it is at
  // rest; the margin varies per cell so the light clears dots, not areas.
  lit(cell, L) {
    const [cx, cy, R] = this.sphere
    return this.tone(cell.i, cell.j, cx, cy, R, L) < cell.rest - cell.clear
  },

  // The resting light turned by `swing` radians about the view axis.
  aim(swing) {
    const F = this.final, [x, y, z] = F.dir
    const phi = Math.atan2(y, x) + swing, s = Math.hypot(x, y)
    return { ...F, dir: [s * Math.cos(phi), s * Math.sin(phi), z] }
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, lerp, meta } = api
    ctx.fillStyle = this.paper; ctx.fillRect(0, 0, W, H)

    // A cursor blinks where the orb will be.
    const blink = (t > 0.7 && t < 0.95) || (t > 1.15 && t < 1.45)

    // The ball grows out of it, dot by dot...
    const g = this.reach * ease.outCubic(seg(t, 1.45, 2.6))
    const [ci, cj] = this.cursor
    const cursor = cell => cell.i - ci >= 0 && cell.i - ci < 2 && cell.j - cj >= 0 && cell.j - cj < 2
    // ...then the light swings in like a pendulum, clearing the dots
    // it falls on, and comes to rest by 4.4 s.
    const p = seg(t, 2.4, 4.4), rest = t >= 4.4
    const swing = 1.3 * ease.inOutCubic(seg(t, 2.4, 2.9)) * Math.exp(-3.2 * p) * Math.cos(api.TAU * 1.1 * p)
      * (1 - ease.inOutCubic(seg(t, 3.9, 4.4)))
    const L = this.aim(swing)
    this.dots(ctx, api, cell => {
      if (t < 1.45) return blink && cursor(cell)
      if (!cursor(cell) && cell.grow > g) return false
      return rest || !this.lit(cell, L)
    })

    // The dots are the wallpaper's; fade onto the still for the WebP's faint
    // ink fringe on the paper around them.
    const f = ease.inOutCubic(seg(t, 4.4, 4.6))
    if (f > 0) { ctx.globalAlpha = f; ctx.drawImage(api.still, 0, 0, W, H); ctx.globalAlpha = 1 }
  },

  // The light sways gently around its resting place and returns every idleLength.
  idle(ctx, t, api) {
    const { W, H, TAU } = api, p = TAU * t / this.idleLength
    ctx.fillStyle = this.paper; ctx.fillRect(0, 0, W, H)
    const F = this.final, d = [F.dir[0] + 0.12 * Math.sin(p), F.dir[1] + 0.08 * Math.sin(2 * p), F.dir[2]]
    const len = Math.hypot(...d), L = { ...F, dir: d.map(v => v / len) }
    this.dots(ctx, api, cell => !this.lit(cell, L))
  },
})
