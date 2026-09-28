// Vantablack layers stacked.
// The papercut stack is laid down sheet by sheet out of the dark, deepest
// first: each strip drops onto the pile from above, a little large and up and
// to the left like a sheet held over the others, and lands with a small
// spring. Last, the grey front sheet slides in from the left over everything.

// Timings in seconds. LIFT is how much larger a strip starts; OFFSET how far
// up and left it starts, in wallpaper pixels; SLIDE_FROM how far left the
// front sheet starts.
const STACK = 0.25, STAGGER = 0.065, JITTER = 0.05, DROP = 1.0, FRONT = 2.95, SLIDE = 1.2, EXACT = 4.5
const LIFT = 0.16, OFFSET = [140, 200], SLIDE_FROM = 3600

themotion.scene({
  beats: { stack: STACK, front: FRONT, still: EXACT },
  idleLength: 8,

  setup(api) {
    const { meta, W, H } = api
    // Every strip is cut from the still through its mask, so it is the
    // wallpaper's own pixels, and the strips tile the picture exactly.
    const cut = name => {
      const l = api.layer(name), c = document.createElement("canvas")
      c.width = l.w; c.height = l.h
      const g = c.getContext("2d")
      g.drawImage(l.img, 0, 0)
      g.globalCompositeOperation = "source-in"
      g.drawImage(api.still, -l.x, -l.y, W, H)
      return { img: c, x: l.x, y: l.y, w: l.w, h: l.h }
    }
    const sheets = meta.sheets
    // The front sheet is the biggest; it arrives on its own at the end.
    const front = sheets.reduce((a, b) => (b.area > a.area ? b : a))
    const rest = sheets.filter(s => s !== front)
    const r = api.rng(0x3a1)
    this.sheets = sheets.map(s => {
      const k = rest.indexOf(s)
      return {
        ...cut(s.name), c: s.centroid, front: s === front,
        start: s === front ? FRONT : STACK + STAGGER * k + JITTER * r(),
        lift: LIFT * (0.8 + 0.4 * r()),
      }
    })
  },

  enter(ctx, t, api) {
    const { W, H, seg, ease, lerp } = api, base = ctx.getTransform()
    ctx.fillStyle = "#000"; ctx.fillRect(0, 0, W, H)
    // Whatever the springs have left is eased onto exactly zero by EXACT.
    const home = ease.inOutCubic(seg(t, EXACT - 0.5, EXACT))

    for (const s of this.sheets) {
      const p = seg(t, s.start, s.start + (s.front ? SLIDE : DROP))
      if (p <= 0) continue
      if (t >= EXACT) { ctx.setTransform(base); ctx.drawImage(s.img, s.x, s.y); continue }

      if (s.front) {
        // Slides in from the left edge, overshoots once and eases back from
        // the right, so its curved edge only ever covers strips already laid.
        // Its flat grey left column is stretched to the screen's edge, so no
        // black shows behind it while it overshoots.
        const dx = -SLIDE_FROM * (1 - lerp(ease.outBack(p, 1.2), 1, home))
        ctx.setTransform(base)
        ctx.drawImage(s.img, s.x + dx, s.y)
        if (dx > 0) ctx.drawImage(s.img, 0, 0, 1, s.h, s.x, s.y, dx + 1, s.h)
        continue
      }

      // Held above the pile: larger about its middle, up and to the left
      // (away from the light's shadows), and faint; it drops and springs.
      const q = 1 - lerp(ease.spring(p, 5.0, 11), 1, home)
      const k = 1 + s.lift * q, [cx, cy] = s.c
      const dx = -OFFSET[0] * s.lift / LIFT * q, dy = -OFFSET[1] * s.lift / LIFT * q
      ctx.setTransform(base.multiply(new DOMMatrix([k, 0, 0, k, cx * (1 - k) + dx, cy * (1 - k) + dy])))
      ctx.globalAlpha = ease.outCubic(seg(p, 0, 0.35))
      ctx.drawImage(s.img, s.x, s.y)
      ctx.globalAlpha = 1
    }
    ctx.setTransform(base)
  },
})
