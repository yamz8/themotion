// Hackerman geometric.
// A seed of light kindles in the dense core of the network. The picture,
// cut into shards along its own vertices, bursts out of it: each shard flies
// out spinning and small, springs into place and flashes as it locks on,
// the core first and the loose strands in the upper left last.

// Timings in seconds: the seed, the first and last shard launches, and how
// long a shard flies.
const SEED = 0.25, FIRST = 0.75, LAST = 3.25, FLIGHT = 1.15
const LIGHT = "124,248,247", SPARK = "210,252,255"

themotion.scene({
  beats: { seed: SEED, burst: FIRST, strands: LAST, locked: LAST + FLIGHT },

  setup(api) {
    const { meta, rng, W, H } = api
    const [cx, cy] = this.core = meta.core
    const pts = meta.points
    const reach = Math.max(Math.hypot(cx, cy), Math.hypot(W - cx, cy), Math.hypot(cx, H - cy), Math.hypot(W - cx, H - cy))
    // Launch time by distance from the core, so the burst spreads outward.
    const launch = (x, y, jitter) => FIRST + (LAST - FIRST) * Math.pow(Math.hypot(x - cx, y - cy) / reach, 0.8) + jitter

    const r = rng(7)
    this.shards = meta.shards.map(([a, b, c]) => {
      const p = [pts[a], pts[b], pts[c]]
      const mx = (p[0][0] + p[1][0] + p[2][0]) / 3, my = (p[0][1] + p[1][1] + p[2][1]) / 3
      const x0 = Math.floor(Math.min(p[0][0], p[1][0], p[2][0])), x1 = Math.ceil(Math.max(p[0][0], p[1][0], p[2][0]))
      const y0 = Math.floor(Math.min(p[0][1], p[1][1], p[2][1])), y1 = Math.ceil(Math.max(p[0][1], p[1][1], p[2][1]))
      const start = Math.max(FIRST, launch(mx, my, (r() - 0.5) * 0.3))
      return {
        p, mx, my, x0, y0, w: x1 - x0, h: y1 - y0, start,
        // Where it starts: part of the way out from the core, a little off line.
        from: 0.35 + 0.2 * r(), side: (r() - 0.5) * 300,
        spin: (r() < 0.5 ? -1 : 1) * (0.6 + 1.2 * r()),
      }
    })
    this.nodes = meta.nodes.map(i => {
      const [x, y] = pts[i]
      return { x, y, lock: launch(x, y, 0) + FLIGHT }
    })
    this.done = Math.max(...this.shards.map(s => s.start)) + FLIGHT
  },

  // One shard, cut from the still along its triangle, at progress e of its
  // flight (1 when in place), drawn at alpha a.
  shard(ctx, api, s, e, a) {
    if (a <= 0.003) return
    const [cx, cy] = this.core, k = 1 - e
    const dx = cx - s.mx, dy = cy - s.my, d = Math.hypot(dx, dy) || 1
    const back = (1 - s.from) * k
    const ox = dx * back - (dy / d) * s.side * k, oy = dy * back + (dx / d) * s.side * k
    const scale = 1 - 0.8 * k, rot = s.spin * k
    ctx.save()
    ctx.globalAlpha = a
    ctx.translate(s.mx + ox, s.my + oy)
    ctx.rotate(rot)
    ctx.scale(scale, scale)
    ctx.translate(-s.mx, -s.my)
    ctx.beginPath()
    ctx.moveTo(s.p[0][0], s.p[0][1]); ctx.lineTo(s.p[1][0], s.p[1][1]); ctx.lineTo(s.p[2][0], s.p[2][1])
    ctx.closePath()
    ctx.clip()
    ctx.drawImage(api.still, s.x0, s.y0, s.w, s.h, s.x0, s.y0, s.w, s.h)
    ctx.restore()
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, blocks } = api
    const [cx, cy] = this.core

    ctx.fillStyle = "#000"
    ctx.fillRect(0, 0, W, H)
    if (t >= this.done + 0.6) { ctx.drawImage(api.still, 0, 0, W, H); return }

    // The background is black, so the shards add up like light: overlapping
    // in flight they glow, and cut edges sum back to the exact picture.
    ctx.globalCompositeOperation = "lighter"

    // The seed swells in the core, bursts as the shards leave, and fades.
    const swell = ease.outCubic(seg(t, SEED, FIRST + 0.1)), fade = 1 - ease.inOutCubic(seg(t, FIRST, FIRST + 1.6))
    blocks.glow(ctx, cx, cy, 120 + 700 * swell, LIGHT, 0.6 * swell * fade)
    blocks.glow(ctx, cx, cy, 40 + 160 * swell, SPARK, swell * fade)

    for (const s of this.shards) {
      const p = seg(t, s.start, s.start + FLIGHT)
      if (p <= 0) continue
      // Out fast, a small overshoot, then exactly in place.
      const e = p >= 1 ? 1 : ease.outBack(ease.outCubic(p), 1.2)
      this.shard(ctx, api, s, e, ease.outCubic(seg(p, 0, 0.35)))
      // It flashes as it locks on.
      const flash = seg(t, s.start + FLIGHT * 0.55, s.start + FLIGHT * 0.55 + 0.6)
      if (flash > 0 && flash < 1) this.shard(ctx, api, s, e, 0.9 * Math.pow(1 - flash, 2))
    }

    // Each dot sparks as the shards around it lock on.
    for (const n of this.nodes) {
      const q = seg(t, n.lock - FLIGHT * 0.5, n.lock)
      if (q <= 0 || q >= 1) continue
      const a = Math.sin(Math.PI * q)
      blocks.glow(ctx, n.x, n.y, 70, LIGHT, 0.6 * a)
      blocks.glow(ctx, n.x, n.y, 18, "255,255,255", a)
    }

    ctx.globalCompositeOperation = "source-over"
  },
})
