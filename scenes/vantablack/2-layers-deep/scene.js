// Vantablack layers deep.
// The depth opens up front to back: the grey front sheet slides in from the
// left, then each layer behind it slides out from under the one above, a
// little further right each time, out of the dark. Halfway through, the back
// sheet at the right fades up where it lies, and with it a floor in its colour
// under everything, so the last layers slide over paper rather than black.

// Timings in seconds. OFFSET is how far left a sheet starts, in wallpaper
// pixels; FRONT_FROM how far left the front sheet starts.
const FRONT = 0.15, SLIDE = 1.2, OPEN = 0.75, STAGGER = 0.085, JITTER = 0.03, BACK = 2.2, FLOOR = 1.0, EXACT = 4.5
const OFFSET = 900, FRONT_FROM = 1800

themotion.scene({
  beats: { front: FRONT, open: OPEN, back: BACK, still: EXACT },
  idleLength: 8,

  setup(api) {
    const { meta } = api, k = meta.mask_scale
    // Deepest first, so the last is the front sheet; the rest open from the
    // top of the stack down. The back sheet is the biggest after the front.
    const sheets = meta.sheets, n = sheets.length
    const back = sheets.slice(0, -1).reduce((a, b) => (b.area > a.area ? b : a))
    const r = api.rng(0x2d7)
    this.floor = api.layer("floor")
    this.floorScale = meta.floor_scale
    this.sheets = sheets.map((s, rank) => {
      const front = rank === n - 1, j = n - 2 - rank
      const l = api.layer(s.name)
      return {
        mask: l.img, x: l.x * k, y: l.y * k, w: l.w * k, h: l.h * k, front, back: s === back,
        start: front ? FRONT : s === back ? BACK : OPEN + STAGGER * j + JITTER * r(),
        from: front ? FRONT_FROM : OFFSET * (0.8 + 0.4 * r()),
      }
    })
    // Each sheet is cut from the still through its mask as it is drawn, in
    // one scratch canvas, so it is the wallpaper's own pixels and the sheets
    // tile the picture exactly. The masks are quarter size, scaled up without
    // smoothing just as they were cut; a kept, cut canvas per sheet would not
    // fit in the renderer's memory at 7680x4320.
    const scratch = document.createElement("canvas")
    scratch.width = Math.max(...this.sheets.map(s => s.w))
    scratch.height = Math.max(...this.sheets.map(s => s.h))
    const g = scratch.getContext("2d")
    this.cut = s => {
      g.globalCompositeOperation = "copy"
      g.imageSmoothingEnabled = false
      g.drawImage(s.mask, 0, 0, s.w, s.h)
      g.globalCompositeOperation = "source-in"
      g.drawImage(api.still, s.x, s.y, s.w, s.h, 0, 0, s.w, s.h)
      return scratch
    }
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, lerp } = api
    if (t >= EXACT) { ctx.drawImage(api.still, 0, 0, W, H); return }
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, W, H)
    // Whatever is left of the slides is eased onto exactly zero by EXACT.
    const home = ease.inOutCubic(seg(t, EXACT - 0.5, EXACT))

    // The floor: the back sheet's colour carried under every gap.
    const up = ease.inOutCubic(seg(t, BACK, BACK + FLOOR))
    if (up > 0) {
      ctx.globalAlpha = up
      ctx.drawImage(this.floor.img, 0, 0, this.floor.w * this.floorScale, this.floor.h * this.floorScale)
      ctx.globalAlpha = 1
    }

    for (const s of this.sheets) {
      const p = seg(t, s.start, s.start + (s.back ? FLOOR : SLIDE))
      if (p <= 0) continue
      if (s.back) {
        // It reaches the screen's right edge, so it stays put and fades up.
        ctx.globalAlpha = up
        ctx.drawImage(this.cut(s), 0, 0, s.w, s.h, s.x, s.y, s.w, s.h)
        ctx.globalAlpha = 1
        continue
      }
      // Straight in from the left, with no overshoot: a sheet's left edge is
      // the edge of the sheet above it, and passing it would open a black gap.
      const dx = -s.from * (1 - lerp(ease.outCubic(p), 1, home))
      const img = this.cut(s)
      ctx.globalAlpha = s.front ? 1 : ease.outCubic(seg(p, 0, 0.45))
      ctx.drawImage(img, 0, 0, s.w, s.h, s.x + dx, s.y, s.w, s.h)
      ctx.globalAlpha = 1
    }
  },
})
