// Rose Pine dot map.
// A seed dot pops at the heart of the band with a ring. A front spreads out
// from it along the band, and every dot it passes spins into place on a
// spring. A ripple runs out through the grid like a drop in water, then the
// darkest dots twinkle before the map settles.
themotion.scene({
  beats: { seed: 0.45, front: 0.6, ripple: 2.9, twinkle: 3.9 },
  idleLength: 8,

  setup(api) {
    const { meta, rng } = api, [ox, oy] = meta.origin, [ax, ay] = meta.axis, half = meta.box / 2
    this.layer = api.layer("dots")
    this.box = meta.box
    this.bg = `rgb(${meta.coef.map(c => c[0].toFixed(1)).join(",")})`
    this.origin = { x: ox, y: oy }

    const r = rng(7)
    this.dots = meta.dots.map(([bx, by, strength, rgb]) => {
      const x = bx + half, y = by + half, dx = x - ox, dy = y - oy, dist = Math.hypot(dx, dy) || 1
      // The front runs faster along the band than across it.
      const along = dx * ax + dy * ay, across = -dx * ay + dy * ax
      return {
        bx, by, x, y, strength, dist, ux: dx / dist, uy: dy / dist,
        reach: Math.hypot(along, across * 2.2), jitter: r(), spin: r() < 0.5 ? -1 : 1,
        color: [rgb >> 16 & 255, rgb >> 8 & 255, rgb & 255].join(","),
      }
    })
    const far = Math.max(...this.dots.map(d => d.reach))
    this.maxDist = Math.max(...this.dots.map(d => d.dist))
    for (const d of this.dots) {
      d.arrive = FRONT_START + FRONT_TIME * Math.pow(d.reach / far, 0.85) - 0.2 * d.strength + 0.15 * d.jitter
    }

    // The seed is the strongest dot near the band's centre; the twinklers are
    // the darkest few percent, each with its own moment.
    const near = this.dots.filter(d => d.dist < 160)
    this.seed = near.reduce((a, b) => (b.strength > a.strength ? b : a), near[0])
    this.seed.arrive = SEED
    const cut = [...this.dots].sort((a, b) => b.strength - a.strength)[Math.floor(this.dots.length * 0.03)].strength
    const tw = rng(11)
    this.dots.forEach(d => { d.twinkle = d.strength >= cut && d !== this.seed ? 3.9 + 0.5 * tw() : null })
  },

  // Draw one dot about its centre, scaled by s, turned by rot and shifted by (dx, dy).
  dot(ctx, base, d, s, rot, dx, dy) {
    const l = this.layer, B = this.box, c = Math.cos(rot) * s, n = Math.sin(rot) * s
    ctx.setTransform(base.a * c, base.a * n, -base.a * n, base.a * c, base.a * (d.x + dx), base.a * (d.y + dy))
    ctx.drawImage(l.img, d.bx - l.x, d.by - l.y, B, B, -B / 2, -B / 2, B, B)
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, blocks } = api, base = ctx.getTransform()
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)

    // A soft halo in its own colour behind the seed as it pops.
    blocks.glow(ctx, this.seed.x, this.seed.y, 100, this.seed.color, 0.4 * Math.sin(Math.PI * seg(t, SEED, SEED + 0.8)))

    // The ripple: a packet travelling out from the centre, gone by 4.4 s.
    const front = (t - RIPPLE) * RIPPLE_SPEED, calm = 1 - ease.inOutCubic(seg(t, 3.6, 4.4))
    const ripple = t > RIPPLE && calm > 0

    for (const d of this.dots) {
      const p = seg(t, d.arrive, d.arrive + POP)
      if (p <= 0) continue
      // Spin in on a spring, pushed out from the centre as it lands.
      let s = ease.outBack(p, 2.4), rot = d.spin * (1 - ease.outCubic(p)) * Math.PI / 2
      let push = -40 * (1 - ease.outCubic(p))
      if (ripple) {
        const k = (front - d.dist) / 260, env = Math.exp(-k * k) * calm
        s *= 1 + 0.75 * env
        push += 18 * Math.sin(k * 2.2) * env
      }
      if (d.twinkle !== null) {
        // A twinkle: a swell with a twist out to 45 degrees and back.
        const q = Math.sin(Math.PI * seg(t, d.twinkle, d.twinkle + TWINKLE))
        s *= 1 + 0.8 * q
        rot += d.spin * q * Math.PI / 4
      }
      if (s <= 0.01) continue
      this.dot(ctx, base, d, s, rot, d.ux * push, d.uy * push)
    }
    ctx.setTransform(base)

    // The seed's ring as it pops.
    ctx.globalCompositeOperation = "multiply"
    blocks.shockwave(ctx, this.seed.x, this.seed.y, 10, 900, this.seed.color, seg(t, SEED, SEED + 1.1), 8)
    ctx.globalCompositeOperation = "source-over"
  },

  // A slow swell that breathes out from the centre and returns every idleLength.
  idle(ctx, t, api) {
    const { W, H, TAU } = api, base = ctx.getTransform(), w = TAU / this.idleLength
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, W, H)
    for (const d of this.dots) {
      const k = 0.5 + 0.5 * Math.sin(w * t - TAU * d.dist / this.maxDist)
      this.dot(ctx, base, d, 1 + 0.25 * k * k * k, 0, 0, 0)
    }
    ctx.setTransform(base)
  },
})

// Timings in seconds and the ripple's speed in wallpaper pixels a second.
const SEED = 0.45, FRONT_START = 0.6, FRONT_TIME = 1.9, POP = 0.55, RIPPLE = 2.9, RIPPLE_SPEED = 2600, TWINKLE = 0.45
