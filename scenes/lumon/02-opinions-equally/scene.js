// Enjoy each opinion equally.
// The terminal warms up like a tube: a line across the middle opens into the
// screen. The status labels type themselves on and the branch number rolls to
// 501. The data rows flicker on outward from the middle, the mark resolves
// cell by cell and sends out a square pulse, and OMARCHY opens letter by
// letter from its centre line. The tagline's letters light in no particular
// order, each one equally, and the rule below fills like a progress bar.
//
// Every glowing layer is light added to the field, so it is drawn "lighter".
themotion.scene({
  beats: { tube: 0.05, labels: 0.55, data: 0.9, mark: 1.35, OMARCHY: 2.4, tagline: 3.1, rule: 3.85 },

  setup(api) {
    const { meta, layers, rng, W } = api
    this.ink = meta.ink.map(Math.round).join(",")
    this.flat = `rgb(${meta.flat.join(",")})`
    const run = (name, n) => Array.from({ length: n }, (_, i) => layers[`${name}${i}`])
    this.words = run("word", meta.words)
    this.tags = run("tag", meta.tags)
    this.term = run("term", meta.term)
    this.branch = run("branch", meta.branch)

    // The data rows light in columns, outward from the middle.
    const data = layers.data, r = rng(0x501)
    this.columns = []
    for (let x = data.x; x < data.x + data.w; x += 26) {
      const d = Math.abs(x + 13 - W / 2) / (W / 2)
      this.columns.push({ x, on: 0.9 + d * 0.75 + r() * 0.18 })
    }

    // The mark resolves in cells, roughly top-left to bottom-right, over the
    // whole layer so its glow comes too.
    const [x0, y0, x1, y1] = meta.logo, size = 46, r2 = rng(0xe0e), logo = layers.logo
    this.cells = []
    for (let y = logo.y; y < logo.y + logo.h; y += size) {
      for (let x = logo.x; x < logo.x + logo.w; x += size) {
        const d = ((x - x0) / (x1 - x0) + (y - y0) / (y1 - y0)) / 2
        this.cells.push({ x, y, size, on: 1.35 + d * 0.45 + r2() * 0.35 })
      }
    }

    // The tagline's letters take turns in a shuffled order.
    const r3 = rng(0xe9a1), order = this.tags.map((_, i) => i)
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(r3() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]
    }
    this.tagOn = []
    order.forEach((i, k) => { this.tagOn[i] = 3.1 + k * 0.03 + r3() * 0.05 })
  },

  // A bright horizontal beam, fading to either side of `y`.
  beam(ctx, y, x0, x1, thick, strength) {
    if (strength <= 0.005 || x1 <= x0) return
    const g = ctx.createLinearGradient(0, y - thick, 0, y + thick)
    g.addColorStop(0, `rgba(${WHITE},0)`)
    g.addColorStop(0.5, `rgba(${WHITE},${strength})`)
    g.addColorStop(1, `rgba(${WHITE},0)`)
    ctx.fillStyle = g
    ctx.fillRect(x0, y - thick, x1 - x0, thick * 2)
  },

  // The tube warms up: a line grows across the middle, then opens into the
  // field; a faint refresh bar rolls down until the picture settles.
  drawTube(ctx, t, api) {
    const { seg, ease, W, H } = api, cy = H / 2
    ctx.fillStyle = this.flat; ctx.fillRect(0, 0, W, H)
    const line = ease.outCubic(seg(t, 0.05, 0.35)), open = ease.inOutCubic(seg(t, 0.3, 0.85))
    const half = open * H / 2
    if (open > 0) {
      ctx.save(); ctx.beginPath(); ctx.rect(0, cy - half, W, half * 2); ctx.clip(); api.put("backdrop"); ctx.restore()
    }
    ctx.globalCompositeOperation = "lighter"
    const fade = 1 - seg(t, 0.75, 1.1)
    if (open < 1) this.beam(ctx, cy, W / 2 * (1 - line), W / 2 * (1 + line), 14 + 30 * open, 0.9 * fade)
    for (const s of [-1, 1]) this.beam(ctx, cy + s * half, 0, W, 20, 0.45 * open * fade)
    const bar = seg(t, 0.9, 4.6)
    if (bar > 0 && bar < 1) this.beam(ctx, H * (bar * 1.6 - 0.3), 0, W, 260, 0.03 * Math.sin(Math.PI * bar))
  },

  // TERMINAL: ONLINE types on behind a block cursor; BRANCH: types on and
  // its number rolls in, digit by digit.
  drawLabels(ctx, t, api) {
    const { seg, ease } = api
    const typed = (glyphs, start) => glyphs.filter((_, i) => t >= start + i * 0.045)
    const term = typed(this.term, 0.55)
    term.forEach(l => api.put(l.name))
    if (t > 0.45 && t < 1.9 && (term.length < this.term.length || Math.floor(t * 4) % 2 === 0)) {
      const last = term.at(-1) || this.term[0], x = term.length ? last.x + last.w + 6 : last.x
      ctx.fillStyle = `rgba(${this.ink},0.5)`; ctx.fillRect(x, last.y + 4, 26, last.h - 8)
    }
    const word = this.branch.slice(0, -3), digits = this.branch.slice(-3)
    typed(word, 0.75).forEach(l => api.put(l.name))
    digits.forEach((l, i) => {
      const start = 1.0, stop = 1.35 + i * 0.16, p = seg(t, start, stop)
      if (p <= 0) return
      // A drum of the digit itself, spinning down to rest.
      const travel = (1 - ease.outCubic(p)) * (5 + i) * l.h, off = travel % l.h
      ctx.save(); ctx.beginPath(); ctx.rect(l.x - 4, l.y, l.w + 8, l.h); ctx.clip()
      ctx.globalAlpha = p < 1 ? 0.8 : 1
      api.put(l.name, 0, off); if (off > 0) api.put(l.name, 0, off - l.h)
      ctx.restore(); ctx.globalAlpha = 1
    })
  },

  // The data rows flicker on in columns, outward from the middle.
  drawData(ctx, t, api) {
    const { rng } = api, data = api.layer("data"), frame = Math.floor(t * 30)
    ctx.save(); ctx.beginPath()
    let any = false
    for (const c of this.columns) {
      if (t < c.on) continue
      if (t < c.on + 0.12 && rng(frame * 131 + c.x)() < 0.45) continue
      ctx.rect(c.x, data.y, 26, data.h); any = true
    }
    if (any) { ctx.clip(); api.put("data") }
    ctx.restore()
  },

  // The mark resolves cell by cell, each cell flaring as it lands, then sends
  // a square pulse out from its frame.
  drawMark(ctx, t, api) {
    const { seg, ease, blocks } = api, [x0, y0, x1, y1] = api.meta.logo
    const lit = this.cells.filter(c => t >= c.on)
    if (!lit.length) return
    ctx.save(); ctx.beginPath()
    lit.forEach(c => ctx.rect(c.x, c.y, c.size, c.size)); ctx.clip(); api.put("logo")
    ctx.restore()
    // Fresh cells flare: the mark drawn again through them, fading.
    for (const [from, to, strength] of [[0, 0.1, 0.9], [0.1, 0.2, 0.5], [0.2, 0.32, 0.2]]) {
      const hot = lit.filter(c => t - c.on >= from && t - c.on < to)
      if (!hot.length) continue
      ctx.save(); ctx.beginPath(); hot.forEach(c => ctx.rect(c.x, c.y, c.size, c.size)); ctx.clip()
      ctx.globalAlpha = strength; api.put("logo"); ctx.restore(); ctx.globalAlpha = 1
    }
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2
    const land = 2.2, pulse = seg(t, land, land + 0.9)
    blocks.glow(ctx, mx, my, 900, this.ink, 0.32 * Math.exp(-Math.pow((t - land - 0.05) / 0.16, 2)))
    if (pulse > 0 && pulse < 1) {
      const grow = ease.outExpo(pulse) * 520
      ctx.save(); ctx.globalAlpha = 0.55 * (1 - pulse)
      ctx.strokeStyle = `rgb(${this.ink})`; ctx.lineWidth = 12 * (1 - pulse) + 2
      ctx.strokeRect(x0 - grow, y0 - grow * 0.9, x1 - x0 + grow * 2, y1 - y0 + grow * 1.8)
      ctx.restore()
    }
  },

  // OMARCHY opens letter by letter from its centre line, middle letters first.
  drawWordmark(ctx, t, api) {
    const { seg, ease } = api, mid = (this.words.length - 1) / 2
    this.words.forEach((l, i) => {
      const start = 2.4 + Math.abs(i - mid) * 0.1, p = seg(t, start, start + 0.5)
      if (p <= 0) return
      const s = Math.max(0.02, ease.outBack(p, 2.4)), cy = l.y + l.h / 2
      ctx.save(); ctx.translate(0, cy); ctx.scale(1, s); ctx.translate(0, -cy)
      ctx.globalAlpha = Math.min(1, p * 4); api.put(l.name)
      ctx.restore(); ctx.globalAlpha = 1
      this.beam(ctx, cy, l.x, l.x + l.w, 10, 0.8 * (1 - seg(p, 0, 0.45)))
    })
  },

  // Each of the tagline's letters lights on its own turn, with a flare.
  drawTagline(ctx, t, api) {
    this.tags.forEach((l, i) => {
      const on = this.tagOn[i]
      if (t < on) return
      api.put(l.name)
      const flare = 1 - api.seg(t, on, on + 0.22)
      if (flare > 0) { ctx.globalAlpha = flare; api.put(l.name); ctx.globalAlpha = 1 }
    })
  },

  // The rule fills like a progress bar, then flashes once when it completes.
  drawRule(ctx, t, api) {
    const { seg, ease, blocks } = api, l = api.layer("rule")
    const p = ease.inOutCubic(seg(t, 3.85, 4.5))
    if (p <= 0) return
    // The dashes span about the tagline's width; the layer's faint ends reach further.
    const from = this.tags[0].x, to = this.tags.at(-1).x + this.tags.at(-1).w
    const head = from + (to - from) * p, edge = p < 1 ? head : l.x + l.w
    ctx.save(); ctx.beginPath(); ctx.rect(l.x, l.y, edge - l.x, l.h); ctx.clip(); api.put("rule"); ctx.restore()
    if (p < 1) blocks.glow(ctx, head, l.y + l.h / 2, 90, WHITE, 0.6)
    const flash = Math.exp(-Math.pow((t - 4.55) / 0.08, 2)) * (t > 4.45)
    if (flash > 0.01) { ctx.globalAlpha = flash; api.put("rule"); ctx.globalAlpha = 1 }
  },

  enter(ctx, t, api) {
    this.drawTube(ctx, t, api)
    ctx.globalCompositeOperation = "lighter"
    this.drawData(ctx, t, api)
    this.drawLabels(ctx, t, api)
    this.drawMark(ctx, t, api)
    this.drawWordmark(ctx, t, api)
    this.drawTagline(ctx, t, api)
    this.drawRule(ctx, t, api)
    ctx.globalCompositeOperation = "source-over"
  },
})

const WHITE = "242,252,255"
