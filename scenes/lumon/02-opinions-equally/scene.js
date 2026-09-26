// Enjoy each opinion equally.
// An old terminal boots: the tube switches on as a line across the middle that
// opens into the screen. The status labels type themselves on behind a block
// cursor, the data rows print left to right, and the mark loads row by row like
// a picture coming down a slow line. OMARCHY types on a letter at a time, the
// tagline follows behind the cursor, and the rule below fills in steps like a
// progress bar. No glows or flares: everything arrives in hard steps.
//
// Every glowing layer is light added to the field, so it is drawn "lighter".
themotion.scene({
  beats: { tube: 0.05, labels: 0.55, data: 0.9, mark: 1.35, OMARCHY: 2.4, tagline: 3.1, rule: 3.85 },

  setup(api) {
    const { meta, layers } = api
    this.ink = meta.ink.map(Math.round).join(",")
    this.flat = `rgb(${meta.flat.join(",")})`
    const run = (name, n) => Array.from({ length: n }, (_, i) => layers[`${name}${i}`])
    this.words = run("word", meta.words)
    this.tags = run("tag", meta.tags)
    this.term = run("term", meta.term)
    this.branch = run("branch", meta.branch)
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

  // The tube switches on: a line grows across the middle, then opens into the
  // field.
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
  },

  // A block cursor after the last glyph typed, blinking once the line is done.
  cursor(ctx, t, glyphs, typed, from, to) {
    if (t < from || t >= to || (typed.length === glyphs.length && Math.floor(t * 4) % 2)) return
    const last = typed.at(-1) || glyphs[0], x = typed.length ? last.x + last.w + 6 : last.x
    const top = Math.min(...glyphs.map(l => l.y)), h = Math.max(...glyphs.map(l => l.y + l.h)) - top
    ctx.fillStyle = `rgba(${this.ink},0.5)`; ctx.fillRect(x, top + 4, h * 0.55, h - 8)
  },

  typed(glyphs, t, start, step) {
    return glyphs.filter((_, i) => t >= start + i * step)
  },

  // TERMINAL: ONLINE types on behind a block cursor, then BRANCH: 501.
  drawLabels(ctx, t, api) {
    const term = this.typed(this.term, t, 0.55, 0.045)
    term.forEach(l => api.put(l.name))
    this.cursor(ctx, t, this.term, term, 0.45, 1.9)
    this.typed(this.branch, t, 0.75, 0.045).forEach(l => api.put(l.name))
  },

  // The data rows print left to right, a character column at a time.
  drawData(ctx, t, api) {
    const data = api.layer("data"), col = 26
    const cols = Math.ceil(data.w / col), shown = Math.floor(api.seg(t, 0.9, 1.5) * cols)
    if (!shown) return
    ctx.save(); ctx.beginPath(); ctx.rect(data.x, data.y, shown * col, data.h); ctx.clip(); api.put("data")
    ctx.restore()
  },

  // The mark loads top to bottom in rows of blocks, like a picture coming down a
  // slow line: the row being loaded fills left to right.
  drawMark(ctx, t, api) {
    const logo = api.layer("logo"), size = 46
    const rows = Math.ceil(logo.h / size), cols = Math.ceil(logo.w / size)
    const cells = Math.floor(api.seg(t, 1.35, 2.2) * rows * cols)
    if (!cells) return
    const full = Math.floor(cells / cols), part = cells % cols
    ctx.save(); ctx.beginPath()
    ctx.rect(logo.x, logo.y, logo.w, full * size)
    if (part) ctx.rect(logo.x, logo.y + full * size, part * size, size)
    ctx.clip(); api.put("logo"); ctx.restore()
  },

  // OMARCHY types on, a letter at a time.
  drawWordmark(ctx, t, api) {
    this.typed(this.words, t, 2.4, 0.1).forEach(l => api.put(l.name))
  },

  // The tagline types on behind the cursor.
  drawTagline(ctx, t, api) {
    const tags = this.typed(this.tags, t, 3.1, 0.03)
    tags.forEach(l => api.put(l.name))
    this.cursor(ctx, t, this.tags, tags, 3.0, 4.6)
  },

  // The rule fills in steps, like a progress bar.
  drawRule(ctx, t, api) {
    const l = api.layer("rule"), steps = 16
    const n = Math.floor(api.seg(t, 3.85, 4.5) * steps)
    if (!n) return
    // The dashes span about the tagline's width; the layer's faint ends reach further.
    const from = this.tags[0].x, to = this.tags.at(-1).x + this.tags.at(-1).w
    const edge = n < steps ? from + (to - from) * n / steps : l.x + l.w
    ctx.save(); ctx.beginPath(); ctx.rect(l.x, l.y, edge - l.x, l.h); ctx.clip(); api.put("rule"); ctx.restore()
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
