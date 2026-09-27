// Ristretto colour curves.
// The colour bands fan open one after another, outermost first: each swings
// up from below the screen along its own curve, overshoots and springs back
// into place. Last, the dark dome at the bottom rises into the middle of the
// fan with a stretch and a squash.
themotion.scene({
  beats: { fan: 0.3, dome: 2.55, still: 4.3 },
  idleLength: 8,

  setup(api) {
    const { meta, W, H } = api
    // Every piece is cut from the still through its mask, so it is the
    // wallpaper's own pixels, and the pieces tile the picture exactly.
    const cut = name => {
      const l = api.layer(name), c = document.createElement("canvas")
      c.width = l.w; c.height = l.h
      const g = c.getContext("2d")
      g.drawImage(l.img, 0, 0)
      g.globalCompositeOperation = "source-in"
      g.drawImage(api.still, -l.x, -l.y, W, H)
      return { img: c, x: l.x, y: l.y, w: l.w, h: l.h }
    }
    this.ground = cut("ground")
    this.bg = `rgb(${meta.ground_color.join(",")})`
    this.pivot = meta.pivot
    this.aspect = meta.aspect
    const n = meta.bands.length, r = api.rng(5)
    this.bands = meta.bands.map((b, i) => ({
      ...cut(b.name),
      // The last band is the dome; the rest fan in one after another.
      start: i === n - 1 ? DOME : FAN + STAGGER * i,
      swing: SWING * (0.85 + 0.3 * r()),
      dome: i === n - 1,
    }))
    // The dome's base: the middle of its bottom edge.
    const d = this.bands[n - 1]
    this.base = [d.x + d.w / 2, d.y + d.h]
  },

  // Draw a piece turned by angle a about the pivot, along the pivot's ellipse
  // so the curves travel along themselves.
  swung(ctx, base, p, a) {
    const [px, py] = this.pivot, k = this.aspect, c = Math.cos(a), s = Math.sin(a)
    const m = new DOMMatrix([c, s / k, -s * k, c, 0, 0])
    const t = base.multiply(new DOMMatrix().translate(px, py)).multiply(m).multiply(new DOMMatrix().translate(-px, -py))
    ctx.setTransform(t)
    ctx.drawImage(p.img, p.x, p.y)
  },

  // Clip to the wedge of the pivot's ellipse from the left end up to angle `to`.
  wedge(ctx, to) {
    const [px, py] = this.pivot, k = this.aspect, R = 8000
    ctx.beginPath(); ctx.moveTo(px, py)
    for (let a = -0.4; a < to; a += 0.04) ctx.lineTo(px - R * Math.cos(a), py - R * Math.sin(a) / k)
    ctx.lineTo(px - R * Math.cos(to), py - R * Math.sin(to) / k)
    ctx.closePath(); ctx.clip()
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, lerp } = api, base = ctx.getTransform()
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)
    ctx.drawImage(this.ground.img, this.ground.x, this.ground.y)

    // Whatever the springs have left is eased onto exactly zero by EXACT.
    const home = ease.inOutCubic(seg(t, EXACT - 0.6, EXACT))

    for (const b of this.bands) {
      const p = seg(t, b.start, b.start + LAND)
      if (p <= 0) continue
      if (t >= EXACT) { ctx.setTransform(base); ctx.drawImage(b.img, b.x, b.y); continue }

      if (b.dome) {
        // The dome rises from its base, stretching tall as it overshoots and
        // squashing wide as it drops back.
        const sy = lerp(ease.spring(p, 4.2, 12), 1, home), sx = lerp(1 / Math.sqrt(Math.max(sy, 0.25)), 1, home)
        const [bx, by] = this.base
        ctx.setTransform(base.multiply(new DOMMatrix([sx, 0, 0, sy, bx * (1 - sx), by * (1 - sy)])))
        ctx.drawImage(b.img, b.x, b.y)
        continue
      }

      // A front runs along the band's curve from its left end, and the band
      // slides along behind it, overshoots and springs back.
      const front = HEAD * ease.outCubic(seg(t, b.start, b.start + SWEEP))
      const a = -b.swing * (1 - lerp(ease.spring(p, 5.4, 11), 1, home))
      ctx.save()
      if (front < HEAD) this.wedge(ctx, front)
      this.swung(ctx, base, b, a)
      ctx.restore()
    }
    ctx.setTransform(base)
  },
})

// Timings in seconds; the swing in radians.
const FAN = 0.3, STAGGER = 0.2, SWEEP = 1.1, LAND = 1.6, SWING = 0.35, DOME = 2.55, EXACT = 4.3
// Where a front has run past every band: just beyond the right end.
const HEAD = Math.PI + 0.3
