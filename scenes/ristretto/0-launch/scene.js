// Ristretto launch.
// The five stripes lift off from the bottom edge like a rocket's trail: a
// rumble on the pad, then each stripe shoots up, the centre one first, with a
// spark at its tip and a wiggle in its trail. Once all five run the full
// height, they pinch in and spring outward into their curves, the outer
// stripes a beat ahead and the tails whipping out last.
themotion.scene({
  beats: { liftoff: 0.3, trails: 2.1, bend: 2.25, settle: 4.4 },
  idleLength: 8,

  setup(api) {
    const { meta, H } = api
    this.bg = `rgb(${meta.background.join(",")})`
    this.bend = meta.bend
    this.stripes = meta.stripes.map((s, k) => {
      // Each strip of STRIP rows: its edges, and the columns it touches.
      const strips = []
      for (let y = 0; y < H; y += STRIP) {
        const rows = s.rows.slice(y, Math.min(H, y + STRIP)), n = rows.length
        strips.push({
          y, h: n,
          L: rows.reduce((a, r) => a + r[0], 0) / n,
          R: rows.reduce((a, r) => a + r[1], 0) / n,
          first: Math.min(...rows.map(r => r[2])),
          last: Math.max(...rows.map(r => r[3])),
        })
      }
      const ring = Math.abs(k - 2)
      return {
        layer: api.layer(`stripe${k}`), strips, straight: s.straight, ring, side: Math.sign(k - 2),
        color: s.color.map(Math.round).join(","),
        launch: LAUNCH + LAG * ring, bendAt: BEND + BEND_LAG * (2 - ring),
      }
    })
  },

  // The tip of a stripe's trail, in wallpaper rows: below the picture before
  // launch, above it once the stripe has shot through. The climb accelerates.
  head(s, t, H) {
    return H + 40 - (H + TIP + 80) * Math.pow(themotion.seg(t, s.launch, s.launch + RISE), 2.1)
  },

  // How far a row of stripe s has bent from straight (0) into its curve (1).
  bent(s, y, t, api) {
    const { seg, ease, lerp, H } = api
    const t0 = s.bendAt + WHIP * seg(y, this.bend, H)
    const pinch = -PINCH * Math.sin(Math.PI * seg(t, t0 - 0.3, t0))
    return lerp(ease.spring(seg(t, t0, t0 + 1.9), 4.6, 11) + pinch, 1, ease.inOutCubic(seg(t, 3.8, SETTLED)))
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, TAU } = api
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)

    // Settled: the stripes exactly as the wallpaper has them.
    if (t >= SETTLED) {
      for (let k = 0; k < 5; k++) api.put(`stripe${k}`)
      return
    }

    // The rumble on the pad, and the wiggle in the trails as they climb.
    const rumble = Math.sin(Math.PI * seg(t, 0.2, 1.0))
    const sway = SWAY * ease.outCubic(seg(t, 0.5, 1.1)) * (1 - ease.inOutCubic(seg(t, 1.6, 2.4)))

    // Strips land on whole device rows, so neighbours tile without seams at any scale.
    const a = ctx.getTransform().d
    const sparks = []
    for (const s of this.stripes) {
      const head = this.head(s, t, H), l = s.layer
      if (head >= H) continue
      const shake = rumble * 7 * Math.sin(t * 83 + s.ring * 2.1 + s.side)
      for (const p of s.strips) {
        const y = p.y + p.h / 2, d = y - head
        if (d <= 0) continue
        const b = this.bent(s, y, t, api)
        let lo = s.straight[0] * (1 - b) + p.L * b, hi = s.straight[1] * (1 - b) + p.R * b
        // The tip narrows to a point, like a flame.
        if (d < TIP) {
          const f = Math.pow(d / TIP, 0.55), c = (lo + hi) / 2
          lo = c + (lo - c) * f; hi = c + (hi - c) * f
        }
        // Anchored at the pad, free higher up.
        const off = shake + sway * Math.min(1, (H - y) / 900) * Math.sin(TAU * y / WAVE - 7 * t + s.ring * 0.6)
        const k = (hi - lo) / (p.R - p.L), y0 = Math.round(p.y * a), y1 = Math.round((p.y + p.h) * a)
        if (y1 === y0) continue
        ctx.drawImage(l.img, p.first - l.x, p.y - l.y, p.last - p.first, p.h,
          lo + (p.first - p.L) * k + off, y0 / a, (p.last - p.first) * k, (y1 - y0) / a)
      }
      if (head > -TIP) sparks.push([(s.straight[0] + s.straight[1]) / 2, Math.max(head, -60), s])
    }

    // A small, crisp spark at each tip.
    for (const [x, y, s] of sparks) {
      api.blocks.glow(ctx, x, y + 30, 110, s.color, 0.75)
      api.blocks.glow(ctx, x, y + 20, 34, "255,244,225", s.ring === 0 ? 0.95 : 0.7)
    }
  },

  // A slow wave that rolls down the trails and returns every idleLength.
  idle(ctx, t, api) {
    const { W, H, TAU } = api, w = TAU / this.idleLength
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)
    const a = ctx.getTransform().d
    for (const s of this.stripes) {
      const l = s.layer
      for (const p of s.strips) {
        const y0 = Math.round(p.y * a), y1 = Math.round((p.y + p.h) * a)
        if (y1 === y0) continue
        const off = 6 * Math.sin(w * t - TAU * p.y / H + s.ring) * Math.min(1, p.y / 600)
        ctx.drawImage(l.img, p.first - l.x, p.y - l.y, p.last - p.first, p.h, p.first + off, y0 / a, p.last - p.first, (y1 - y0) / a)
      }
    }
  },
})

// Rows per strip; timings in seconds; sizes in wallpaper pixels.
const STRIP = 2
const LAUNCH = 0.3, LAG = 0.12, RISE = 1.55, TIP = 420, SWAY = 26, WAVE = 1500
const BEND = 2.25, BEND_LAG = 0.05, WHIP = 0.3, PINCH = 0.06, SETTLED = 4.4
