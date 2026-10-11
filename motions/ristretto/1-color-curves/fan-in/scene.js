// Ristretto colour curves.
// The colour bands fan open one after another, outermost first: each swings
// up from below the screen along its own curve, overshoots and springs back
// into place. Last, the dark dome at the bottom rises into the middle of the
// fan with a stretch and a squash.
themotion.scene({
  beats: { fan: 0.3, dome: 2.55, still: 4.3 },
  idleLength: 8,

  setup(api) {
    const { meta } = api
    // Every band is a whole strip: the split carried each one on under the
    // bands above it and past the screen's edges, so a band moving on its own
    // shows no corners, no cut ends and no colour of its neighbours, and drawn
    // back in place, bottom first, the bands are the wallpaper.
    const cut = name => {
      const l = api.layer(name)
      return { img: l.img, x: l.x, y: l.y, w: l.w, h: l.h }
    }
    this.ground = cut("ground")
    this.bg = `rgb(${meta.ground_color.join(",")})`
    this.pivot = meta.pivot
    this.aspect = meta.aspect
    // Bands are listed in drawing order; each enters by its slot, outermost first.
    const slots = Math.max(...meta.bands.map(b => b.slot)) + 1, r = api.rng(5)
    const swing = Array.from({ length: slots }, () => SWING * (0.85 + 0.3 * r()))
    this.bands = meta.bands.map(b => ({
      ...cut(b.name),
      // The dome rises last; the rest fan in one after another.
      start: b.dome ? DOME : FAN + STAGGER * b.slot,
      swing: swing[b.slot],
      dome: !!b.dome,
      base: b.base,
    }))
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

  // Draw a piece turned by a, shown only up to the front at angle `to` around
  // the pivot's ellipse, fading out over `soft` radians before it, so the
  // band's leading end is never a hard straight cut.
  fronted(ctx, base, p, a, to, soft) {
    const c = ctx.canvas
    if (!this.buf || this.buf.width !== c.width || this.buf.height !== c.height) {
      this.buf = document.createElement("canvas")
      this.buf.width = c.width; this.buf.height = c.height
    }
    const g = this.buf.getContext("2d")
    g.setTransform(1, 0, 0, 1, 0, 0)
    g.globalCompositeOperation = "source-over"
    g.clearRect(0, 0, c.width, c.height)
    this.swung(g, base, p, a)
    // A conic gradient about the pivot, squeezed into its ellipse: canvas
    // angle pi + phi is the pivot's angle phi (0 at the left end, pi at the right).
    const [px, py] = this.pivot, k = this.aspect, from = -0.5, turn = 2 * Math.PI
    g.setTransform(base.multiply(new DOMMatrix().translate(px, py).scale(1, 1 / k)))
    const mask = g.createConicGradient(Math.PI + from, 0, 0)
    const at = phi => Math.min(1, Math.max(0, (phi - from) / turn))
    mask.addColorStop(0, "#000")
    mask.addColorStop(at(to - soft), "#000")
    mask.addColorStop(at(to), "rgba(0,0,0,0)")
    mask.addColorStop(1, "rgba(0,0,0,0)")
    g.globalCompositeOperation = "destination-in"
    g.fillStyle = mask
    g.fillRect(-1e5, -1e5, 2e5, 2e5)
    g.globalCompositeOperation = "source-over"
    ctx.save()
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.drawImage(this.buf, 0, 0)
    ctx.restore()
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
        const [bx, by] = b.base
        ctx.setTransform(base.multiply(new DOMMatrix([sx, 0, 0, sy, bx * (1 - sx), by * (1 - sy)])))
        ctx.drawImage(b.img, b.x, b.y)
        continue
      }

      // A front runs along the band's curve from its left end, and the band
      // slides along behind it, overshoots and springs back. The front's soft
      // edge is half as wide as it travels in a frame, and never under SOFT.
      const u = seg(t, b.start, b.start + SWEEP)
      const front = HEAD * ease.outCubic(u)
      const speed = HEAD * 3 * (1 - u) ** 2 / SWEEP / api.spec.fps
      const a = -b.swing * (1 - lerp(ease.spring(p, 5.4, 11), 1, home))
      if (front < HEAD) this.fronted(ctx, base, b, a, front, SOFT + speed / 2)
      else this.swung(ctx, base, b, a)
    }
    ctx.setTransform(base)
    // In place, the bands differ from the still only in the thin rims along
    // their edges; ease the still in while nothing moves, so the handoff
    // changes nothing.
    const still = ease.inOutCubic(seg(t, EXACT, EXACT + SETTLE))
    if (still > 0) {
      ctx.globalAlpha = still
      ctx.drawImage(api.still, 0, 0, W, H)
      ctx.globalAlpha = 1
    }
  },
})

// Timings in seconds; the swing in radians.
const FAN = 0.3, STAGGER = 0.2, SWEEP = 1.1, LAND = 1.6, SWING = 0.35, DOME = 2.55, EXACT = 4.3, SETTLE = 0.6
// Where a front has run past every band: just beyond the right end.
const HEAD = Math.PI + 0.3
// The narrowest soft edge of a front, in radians.
const SOFT = 0.04
