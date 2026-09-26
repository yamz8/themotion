// Hackerman synth scape.
// A cyan horizon line draws out across the dark from the valley. The grid
// floor unrolls from it toward the viewer, then the left and right mountain
// ranges spring up out of it. The sun rises through the valley as the sky
// dawns, and a scan pulse runs out along the wireframe before it settles.

// Timings in seconds, and the void under the horizon (Hackerman's darker background).
const LINE = 0.35, FLOOR = 1.0, LEFT = 1.7, RIGHT = 1.95, SUN = 2.2, PULSE = 3.7
const VOID = "#06060c"

// A spring up with one clear overshoot, landing exactly on 1.
const rise = (ease, p) => (p >= 1 ? 1 : ease.spring(p, 5, 9))

themotion.scene({
  beats: { line: LINE, floor: FLOOR, mountains: LEFT, sun: SUN, pulse: PULSE },

  setup(api) {
    const { meta } = api
    // The terrain layer is only an outline: fill it with the still's pixels.
    const l = this.terrain = api.layer("terrain"), cut = document.createElement("canvas")
    cut.width = l.w; cut.height = l.h
    const c = cut.getContext("2d")
    c.drawImage(l.img, 0, 0)
    c.globalCompositeOperation = "source-in"
    c.drawImage(api.still, l.x, l.y, l.w, l.h, 0, 0, l.w, l.h)
    l.img = cut
    this.wire = api.layer("wire")
    this.hy = meta.horizon
    this.valley = meta.valley
    this.line = meta.line.join(",")
    const [, cy, r] = meta.sun
    // The sun starts with its top just under the horizon.
    this.sunDrop = this.hy - (cy - r) + 40
  },

  // Part of the terrain between source columns x0..x1 and rows y0..y1,
  // stretched vertically by s about the horizon.
  part(ctx, x0, x1, y0, y1, s) {
    const l = this.terrain, hy = this.hy
    if (s <= 0.002) return
    ctx.drawImage(l.img, x0 - l.x, y0 - l.y, x1 - x0, y1 - y0, x0, hy + (y0 - hy) * s, x1 - x0, (y1 - y0) * s)
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, blocks } = api, hy = this.hy, l = this.terrain

    // Night: the sky dims to near black until the sun brings the dawn.
    const dawn = ease.inOutCubic(seg(t, SUN, SUN + 2.2))
    api.put("sky")
    ctx.fillStyle = `rgba(0,0,0,${0.85 * (1 - dawn)})`
    ctx.fillRect(0, 0, W, hy)

    // The sun and its glow, rising from behind the horizon.
    const drop = this.sunDrop * (1 - ease.outCubic(seg(t, SUN, SUN + 2.0)))
    const sun = api.layer("sun"), rows = Math.min(sun.h, hy - sun.y - drop)
    if (rows > 0) {
      ctx.globalAlpha = 0.5 + 0.5 * dawn
      ctx.drawImage(sun.img, 0, 0, sun.w, rows, sun.x, sun.y + drop, sun.w, rows)
      ctx.globalAlpha = 1
    }

    // Below the horizon, the void the floor unrolls over.
    ctx.fillStyle = VOID
    ctx.fillRect(0, hy, W, H - hy)

    // The terrain: the floor unrolls down, then each range springs up.
    const floor = ease.outCubic(seg(t, FLOOR, FLOOR + 1.0))
    const left = rise(ease, seg(t, LEFT, LEFT + 1.3))
    const right = rise(ease, seg(t, RIGHT, RIGHT + 1.3))
    if (floor === 1 && left === 1 && right === 1) {
      api.put("terrain")
    } else {
      this.part(ctx, 0, W, hy, H, floor)
      this.part(ctx, 0, this.valley, l.y, hy + 1, left)
      this.part(ctx, this.valley - 1, W, l.y, hy + 1, right)
    }

    // The horizon line draws out from the valley, then hands over to the floor.
    const reach = ease.outExpo(seg(t, LINE, LINE + 0.7)) * Math.max(this.valley, W - this.valley)
    const lineA = seg(t, LINE, LINE + 0.1) * (1 - ease.inOutCubic(seg(t, FLOOR + 0.2, FLOOR + 0.8)))
    if (lineA > 0) {
      const x0 = Math.max(0, this.valley - reach), x1 = Math.min(W, this.valley + reach)
      const g = ctx.createLinearGradient(0, hy - 60, 0, hy + 60)
      g.addColorStop(0, `rgba(${this.line},0)`)
      g.addColorStop(0.5, `rgba(${this.line},${0.45 * lineA})`)
      g.addColorStop(1, `rgba(${this.line},0)`)
      ctx.fillStyle = g
      ctx.fillRect(x0, hy - 60, x1 - x0, 120)
      ctx.fillStyle = `rgba(${this.line},${lineA})`
      ctx.fillRect(x0, hy - 4, x1 - x0, 8)
      blocks.glow(ctx, this.valley, hy, 260, "220,255,255", 0.8 * lineA * (1 - seg(t, LINE, LINE + 0.9)))
    }

    // The floor's leading edge glows as it unrolls.
    if (floor > 0 && floor < 1) {
      const y = hy + (H - hy) * floor, a = 1 - floor
      ctx.fillStyle = `rgba(${this.line},${0.8 * a})`
      ctx.fillRect(0, y - 3, W, 6)
    }

    // The scan pulse: the wireframe lights up in a band that runs from the
    // horizon down to the viewer and up the mountains to their peaks.
    const p = seg(t, PULSE, PULSE + 1.1)
    if (p > 0 && p < 1) {
      const fade = Math.sin(Math.PI * p)
      ctx.globalCompositeOperation = "lighter"
      this.band(ctx, hy + (H - hy) * Math.pow(p, 1.6), 50 + 300 * p, 2.2 * fade)
      this.band(ctx, hy - (hy - l.y) * ease.outCubic(p), 90, 1.8 * fade)
      ctx.globalCompositeOperation = "source-over"
      ctx.globalAlpha = 1
    }
  },

  // A soft horizontal band of the wireframe, added on top: rows around y
  // within half-height h, strongest in the middle.
  band(ctx, y, h, strength) {
    const l = this.wire, n = 12
    for (let i = 0; i < n; i++) {
      const a = y - h + (2 * h * i) / n, b = a + (2 * h) / n
      const y0 = Math.max(a, l.y), y1 = Math.min(b, l.y + l.h)
      if (y1 <= y0) continue
      const k = (a + b) / 2 - y
      // Past 1 the lines are drawn again, which takes them from cyan to white.
      for (let s = strength * Math.exp(-3 * (k / h) ** 2); s > 0.005; s -= 1) {
        ctx.globalAlpha = Math.min(1, s)
        ctx.drawImage(l.img, 0, y0 - l.y, l.w, y1 - y0, l.x, y0, l.w, y1 - y0)
      }
    }
  },
})
