// United in severance.
// Each rule arrives in two halves from the screen's edges and joins in the
// middle. The globe's rim traces itself round from both sides, the parallels
// open out and the globe spins in, and LUMON rises into its band. The tagline
// types itself on, and SEVERANCE flickers on like a fluorescent tube.
themotion.scene({
  beats: { rules: 0.15, globe: 1.0, spin: 1.8, LUMON: 2.55, typing: 3.55, SEVERANCE: 4.2 },

  setup(api) {
    const { meta, layers } = api
    this.ink = meta.ink.map(Math.round).join(",")
    // A meridian of half-width w is a great circle at longitude asin(w / rim).
    this.rim = meta.a - 5
    this.lons = meta.halfwidths.map(w => Math.asin(w / this.rim))
    // The meridians' measured curves, as offsets from their own axis (which
    // sits a few pixels right of the rim's centre), carried on to the poles
    // as ellipses.
    const bulge = y => Math.sqrt(Math.max(0, 1 - Math.pow((y - meta.cy) / meta.mb, 2)))
    this.curves = meta.curves.map(c => {
      const axis = c.right.reduce((s, r, i) => s + r - c.left[i], 0) / c.y.length / 2
      const side = s => {
        const off = c.y.map((y, i) => s * (s > 0 ? c.right[i] : c.left[i]) - axis)
        const cap = (end, pole) => Array.from({ length: 12 }, (_, j) => {
          const y = c.y[end] + (pole - c.y[end]) * (j + 1) / 12
          return [off[end] * bulge(y) / bulge(c.y[end]), y]
        })
        const top = cap(0, meta.cy - meta.mb).reverse(), bottom = cap(c.y.length - 1, meta.cy + meta.mb)
        return [...top, ...c.y.map((y, i) => [off[i], y]), ...bottom]
      }
      return { axis: meta.cx + axis, points: [...side(1), ...side(-1).reverse()] }
    })
    this.rules = [0, 1, 2, 3, 4].map(i => layers[`rule${i}`])
    this.tags = Object.values(layers).filter(l => l.name.startsWith("tag"))
    this.letters = [0, 1, 2, 3, 4].map(i => layers[`letter${i}`])
  },

  // Each rule's halves slide in from the edges and meet in the middle.
  drawRules(ctx, t, api) {
    const { seg, ease, blocks, W } = api, { cx } = api.meta
    for (const [k, i] of [2, 1, 3, 0, 4].entries()) {
      const start = 0.15 + k * 0.1, p = ease.inOutCubic(seg(t, start, start + 0.8))
      if (p <= 0) continue
      const l = this.rules[i], y = api.meta.rules[i]
      ctx.save(); ctx.beginPath()
      ctx.rect(0, l.y, cx * p, l.h); ctx.rect(W - (W - cx) * p, l.y, (W - cx) * p, l.h)
      ctx.clip(); api.put(l.name); ctx.restore()
      if (p < 1) {
        blocks.glow(ctx, cx * p, y, 60, WHITE, 0.7 * p)
        blocks.glow(ctx, W - (W - cx) * p, y, 60, WHITE, 0.7 * p)
      }
      const join = start + 0.8
      blocks.glow(ctx, cx, y, 150, WHITE, 0.4 * Math.exp(-Math.pow((t - join) / 0.12, 2)) * (t > join - 0.05))
    }
  },

  // The rim traces round from the left in both directions and closes on the
  // right; the parallels open out from the middle.
  drawFrame(ctx, t, api) {
    const { seg, ease, blocks, TAU } = api, { cx, cy, a, b } = api.meta
    const p = ease.inOutCubic(seg(t, 1.0, 1.8))
    if (p > 0) {
      ctx.save(); ctx.beginPath(); ctx.moveTo(cx, cy)
      ctx.ellipse(cx, cy, a * 2, b * 2, 0, Math.PI - p * Math.PI, Math.PI + p * Math.PI); ctx.closePath()
      ctx.clip(); api.put("ring"); ctx.restore()
      // A small tight light at each pen tip, no wider than a few strokes.
      if (p < 1) for (const s of [-1, 1]) {
        const phi = Math.PI + s * p * Math.PI
        blocks.glow(ctx, cx + (a - 5) * Math.cos(phi), cy + (b - 5) * Math.sin(phi), 16, WHITE, 0.6)
      }
      blocks.glow(ctx, cx + a - 5, cy, 22, WHITE, 0.6 * Math.exp(-Math.pow((t - 1.8) / 0.08, 2)) * (t > 1.75))
    }
    const q = ease.outCubic(seg(t, 1.6, 2.15))
    if (q > 0) {
      const l = api.layer("parallels"), half = l.w / 2 * q
      ctx.save(); ctx.beginPath(); ctx.rect(cx - half, l.y, half * 2, l.h); ctx.clip(); api.put("parallels"); ctx.restore()
    }
  },

  // The globe spins in half a turn, rings back and settles. While it turns
  // each meridian is its measured curve, squeezed to the width its longitude
  // gives; it then hands over to the wallpaper's own strokes.
  drawMeridians(ctx, t, api) {
    const { seg, ease, TAU } = api, { cx, cy, mb, gap } = api.meta
    const on = seg(t, 1.8, 2.1)
    if (on <= 0) return
    // The spring's last ringing is closed off so the turn lands exactly on 0.
    const p = seg(t, 1.8, 3.5)
    const turn = -Math.PI * (1 - ease.spring(p, 4.2, 8)) * (1 - ease.inOutCubic(seg(p, 0.7, 1)))
    const exact = ease.inOutCubic(seg(t, 3.4, 3.7))
    if (exact < 1) {
      ctx.save()
      ctx.beginPath(); ctx.ellipse(cx, cy, this.rim, mb, 0, 0, TAU)
      ctx.rect(cx - this.rim, gap[0], this.rim * 2, gap[1] - gap[0]); ctx.clip("evenodd")
      ctx.globalAlpha = on * (1 - exact)
      ctx.strokeStyle = `rgb(${this.ink})`; ctx.lineWidth = 10.5
      // Two great circles, plus two more that only show while it turns.
      const extra = 1 - ease.inOutCubic(seg(t, 2.7, 3.35))
      for (let i = 0; i < 4; i++) {
        const base = this.lons[i % 2], { axis, points } = this.curves[i % 2]
        const k = Math.abs(Math.sin(base + (i < 2 ? 0 : Math.PI / 2) + turn)) / Math.sin(base)
        ctx.globalAlpha = on * (1 - exact) * (i < 2 ? 1 : extra)
        if (k * 100 < 1 || ctx.globalAlpha <= 0) continue
        ctx.beginPath()
        points.forEach(([x, y], j) => j ? ctx.lineTo(axis + x * k, y) : ctx.moveTo(axis + x * k, y))
        ctx.closePath(); ctx.stroke()
      }
      ctx.restore()
    }
    if (exact > 0) { ctx.globalAlpha = exact; api.put("meridians"); ctx.globalAlpha = 1 }
  },

  // LUMON rises into its band letter by letter.
  drawWordmark(ctx, t, api) {
    const { seg, ease } = api, [top, bottom] = api.meta.band
    ctx.save(); ctx.beginPath(); ctx.rect(api.meta.cx - api.meta.a, top - 4, api.meta.a * 2, bottom - top + 8); ctx.clip()
    this.letters.forEach((l, i) => {
      const start = 2.55 + i * 0.09, p = seg(t, start, start + 0.55)
      if (p <= 0) return
      api.put(l.name, 0, (1 - ease.outBack(p, 1.6)) * (bottom - top + 12))
    })
    ctx.restore()
  },

  // UNITED IN types on behind a block cursor; SEVERANCE flickers on.
  drawTagline(ctx, t, api) {
    const { seg, rng } = api, n = api.meta.first_word
    const typed = Math.floor(seg(t, 3.55, 3.55 + n * 0.075) * n + 1e-9)
    const shown = t < 3.55 ? 0 : Math.min(n, typed + 1)
    this.tags.slice(0, shown).forEach(l => api.put(l.name))
    const cursorOn = t > 3.3 && t < 4.3 && (t < 3.55 || shown < n || Math.floor(t * 4) % 2 === 0)
    if (cursorOn) {
      const last = shown ? this.tags[shown - 1] : null, first = this.tags[0]
      const x = last ? last.x + last.w + 8 : first.x
      ctx.fillStyle = `rgba(${this.ink},0.85)`; ctx.fillRect(x, first.y + 1, 18, first.h - 2)
    }
    // Fluorescent start: a few stutters, then steady.
    const p = seg(t, 4.2, 4.75)
    if (p <= 0) return
    const frame = Math.floor(t * 30), lit = p >= 1 || rng(frame * 7919 + 13)() < 0.25 + 0.75 * p
    if (!lit) return
    ctx.globalAlpha = p >= 1 ? 1 : 0.55 + 0.45 * p
    this.tags.slice(n).forEach(l => api.put(l.name))
    ctx.globalAlpha = 1
    api.blocks.glow(ctx, (this.tags[n].x + this.tags.at(-1).x) / 2, this.tags[n].y + 18, 260, this.ink, 0.25 * (1 - p))
  },

  enter(ctx, t, api) {
    api.put("backdrop")
    this.drawRules(ctx, t, api)
    this.drawMeridians(ctx, t, api)
    this.drawFrame(ctx, t, api)
    this.drawWordmark(ctx, t, api)
    this.drawTagline(ctx, t, api)
  },
})

const WHITE = "242,252,255"
