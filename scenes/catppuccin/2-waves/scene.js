// Catppuccin waves.
// A signal line draws across the screen, rippling, then the waves swell out of
// it from left to right on a spring. They ring, calm, and a pulse of light
// runs along them before the picture settles.
themotion.scene({
  beats: { line: 0.15, swell: 1.05, pulse: 3.3, calm: 4.4 },
  idleLength: 8,

  setup(api) {
    const { meta } = api
    this.ribbon = api.layer("ribbon")
    this.axis = meta.axis
    this.bg = `rgb(${meta.background.join(",")})`
    this.stops = meta.stops
  },

  // The line colour at x, as "r,g,b".
  color(x, W) {
    const u = themotion.clamp(x / W), s = this.stops
    let i = 1
    while (i < s.length - 1 && s[i][0] < u) i++
    const [u0, c0] = s[i - 1], [u1, c1] = s[i], k = (u - u0) / (u1 - u0)
    return c0.map((c, j) => Math.round(c + (c1[j] - c) * k)).join(",")
  },

  // Draw the ribbon in vertical strips, each stretched about the axis by
  // scale(x) and shifted by lift(x).
  strips(ctx, from, to, scale, lift) {
    const l = this.ribbon, a = this.axis
    for (let x = Math.max(l.x, from); x < Math.min(l.x + l.w, to); x += STRIP) {
      const w = Math.min(STRIP, l.x + l.w - x), s = scale(x + w / 2)
      if (s <= 0.002) continue
      ctx.drawImage(l.img, x - l.x, 0, w, l.h, x, a + (l.y - a) * s + lift(x + w / 2), w, l.h * s)
    }
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, blocks, lerp } = api, a = this.axis
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)

    // The line draws on from the left edge, its head a spark of light.
    const head = W * ease.inOutCubic(seg(t, 0.15, 1.15)) * 1.04

    // A travelling ripple, strongest while the waves are swelling.
    const ripple = 70 * ease.outCubic(seg(t, 0.3, 1.2)) * (1 - ease.inOutCubic(seg(t, 2.6, 4.4)))
    const lift = x => ripple * Math.sin(api.TAU * (x / W) * 2.2 - t * 6.5)

    // Each column swells on a spring, left before right, and is eased onto
    // exactly 1 before the settle.
    const scale = x => {
      const t0 = 1.05 + 0.8 * x / W
      return lerp(ease.spring(seg(t, t0, t0 + 2.1), 4.4, 12), 1, ease.inOutCubic(seg(t, 4.2, 4.9)))
    }

    this.strips(ctx, 0, head, scale, lift)

    // The flat line, fading where the waves have opened out.
    ctx.lineWidth = 5; ctx.lineCap = "round"
    for (let x = 0; x < Math.min(head, W); x += LINE) {
      const on = 1 - seg(scale(x + LINE / 2), 0.05, 0.45)
      if (on <= 0) continue
      ctx.strokeStyle = `rgba(${this.color(x, W)},${on})`
      ctx.beginPath(); ctx.moveTo(x, a + lift(x)); ctx.lineTo(x + LINE, a + lift(x + LINE)); ctx.stroke()
    }
    if (head > 0 && head < W * 1.02) {
      const hx = Math.min(head, W), c = this.color(hx, W), y = a + lift(hx)
      blocks.glow(ctx, hx, y, 220, c, 0.9)
      blocks.glow(ctx, hx, y, 40, "255,255,255", 0.9)
    }

    // A pulse of light runs along the waves.
    const p = seg(t, 3.3, 4.5)
    if (p > 0 && p < 1) {
      const cx = lerp(-0.15, 1.15, ease.inOutCubic(p)) * W, spread = 0.09 * W
      ctx.globalCompositeOperation = "lighter"
      for (let x = Math.max(0, cx - 2.5 * spread); x < Math.min(W, cx + 2.5 * spread); x += STRIP) {
        ctx.globalAlpha = 0.5 * Math.exp(-Math.pow((x - cx) / spread, 2))
        this.strips(ctx, x, x + STRIP, scale, lift)
      }
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over"
    }
  },

  // A slow swell that breathes through the waves and returns every idleLength.
  idle(ctx, t, api) {
    const { W, H, TAU } = api, w = TAU / this.idleLength
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)
    this.strips(ctx, 0, W, x => 1 + 0.06 * Math.sin(w * t - TAU * x / W), x => 10 * Math.sin(2 * w * t + TAU * x / W))
  },
})

// Strip and line-segment widths, in wallpaper pixels.
const STRIP = 4, LINE = 24
