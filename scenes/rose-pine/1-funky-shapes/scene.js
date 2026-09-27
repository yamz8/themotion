// Rose Pine funky shapes.
// The pastel blobs pop in one after another on a jelly spring, squashing,
// shearing and turning into place. Then the doodles draw on: the thin curves
// run left to right, the rings sweep round from the inside out, the wavy
// strokes slide in from the right and the brown dashes flick on. The white
// blob squashes down and springs up, flinging its white dashes out to where
// they belong.
themotion.scene({
  beats: { blobs: 0.3, white: 1.3, curves: 1.9, rings: 2.0, waves: 2.4, dashes: 2.5, fling: 2.95 },
  idleLength: 8,

  setup(api) {
    const { meta, rng, W, H } = api, r = rng(5)
    this.blobs = meta.blobs.map(b => {
      // The pivot: on the frame edge (or corner) the blob is cut by, else its centre.
      const left = b.x0 <= 4, right = b.x1 >= W - 5, top = b.y0 <= 4, bottom = b.y1 >= H - 5
      const px = left ? 0 : right ? W : b.cx, py = top ? 0 : bottom ? H : b.cy
      return { ...b, px, py, edgeX: left || right, edgeY: top || bottom,
        start: POPS[b.name], ph: r() * 6, ph2: r() * 6, spin: r() < 0.5 ? -1 : 1 }
    })
    this.white = this.blobs.find(b => b.name === "blob_white")
    this.rings = Object.entries(meta.rings).map(([side, set]) => ({
      ...set, start: RINGS[side], turn: side === "tl" ? 1 : -1,
      rings: [...set.rings].sort((a, b) => a.r - b.r),
    }))

    // Brown dashes flick on outward from their cluster's middle; white ones
    // fly out of the white blob, nearest first.
    const d = rng(9), dashes = meta.dashes.map(x => ({ ...x, jitter: d(), spin: d() < 0.5 ? -1 : 1 }))
    const brown = dashes.filter(x => x.kind === "brown"), white = dashes.filter(x => x.kind === "white")
    const mx = brown.reduce((s, x) => s + x.cx, 0) / brown.length, my = brown.reduce((s, x) => s + x.cy, 0) / brown.length
    const far = pts => Math.max(...pts.map(x => x.dist))
    brown.forEach(x => { x.dist = Math.hypot(x.cx - mx, x.cy - my) })
    brown.forEach((x, _, all) => { x.start = BROWN + 0.6 * x.dist / far(all) + 0.1 * x.jitter })
    const w = this.white
    white.forEach(x => { x.dist = Math.hypot(x.cx - w.cx, x.cy - w.cy) })
    white.forEach((x, _, all) => { x.start = FLING + 0.45 * x.dist / far(all) + 0.08 * x.jitter })
    this.brown = brown; this.whiteDashes = white
  },

  // A blob on a jelly spring about its centre: it pops from nothing past its
  // size and back, squashing, shearing and turning as it lands.
  blob(ctx, t, api, b) {
    const { seg, ease } = api, l = api.layer(b.name), p = seg(t, b.start, b.start + POP)
    if (p <= 0) return
    let sx = 1, sy = 1, sh = 0, sv = 0, rot = 0
    if (p < 1) {
      const k = t - b.start, calm = 1 - ease.inOutCubic(seg(p, 0.65, 1))
      const s = 1 + (ease.spring(p, 5.4, 11) - 1) * calm
      const q = 0.16 * Math.exp(-3 * k) * Math.sin(13 * k + b.ph) * calm
      const lean = 0.12 * Math.exp(-3 * k) * Math.sin(9 * k + b.ph2) * calm
      // A blob cut off by the frame grows out of that edge and only leans
      // along it, so its cut edge never shows; a free one also turns.
      if (!b.edgeX) sh = lean
      else if (!b.edgeY) sv = lean
      if (!b.edgeX && !b.edgeY) rot = b.spin * 0.35 * (1 - ease.outCubic(p))
      sx = s * (1 + q); sy = s * (1 - q)
    }
    // The white blob's fling: a squash down onto its bottom, then a stretch
    // up that rings out.
    let fx = 1, fy = 1
    if (b === this.white) {
      const down = Math.sin(Math.PI / 2 * seg(t, FLING - 0.3, FLING)) * (1 - ease.outCubic(seg(t, FLING, FLING + 0.08)))
      const up = ease.wobble(t - FLING, 0.12, 5, 19) * (1 - ease.inOutCubic(seg(t, FLING + 0.5, FLING + 0.9)))
      fx = 1 + 0.1 * down - up; fy = 1 - 0.14 * down + up
    }
    if (sx === 1 && sy === 1 && sh === 0 && sv === 0 && rot === 0 && fx === 1 && fy === 1) {
      ctx.drawImage(l.img, l.x, l.y); return
    }
    if (sx <= 0.002 || sy <= 0.002) return
    ctx.save()
    ctx.translate(b.cx, b.y1); ctx.scale(fx, fy); ctx.translate(b.px - b.cx, b.py - b.y1)
    ctx.rotate(rot); ctx.transform(1, sv, sh, 1, 0, 0); ctx.scale(sx, sy); ctx.translate(-b.px, -b.py)
    ctx.drawImage(l.img, l.x, l.y)
    ctx.restore()
  },

  // A set of rings, each sweeping round its centre and turning into place,
  // from the inside out.
  ringSet(ctx, t, api, set) {
    const { seg, ease, TAU } = api
    set.rings.forEach((ring, i) => {
      const l = api.layer(ring.name), p = seg(t, set.start + i * RING_STAGGER, set.start + i * RING_STAGGER + RING)
      if (p <= 0) return
      if (p >= 1) { ctx.drawImage(l.img, l.x, l.y); return }
      const e = ease.inOutCubic(p), a0 = -Math.PI / 2 + set.turn * 0.5 * (1 - ease.outCubic(p))
      const reach = ring.r * 3 + 200
      ctx.save()
      ctx.beginPath(); ctx.moveTo(set.cx, set.cy)
      ctx.arc(set.cx, set.cy, reach, a0, a0 + set.turn * e * TAU, set.turn < 0)
      ctx.closePath(); ctx.clip()
      ctx.translate(set.cx, set.cy); ctx.rotate(set.turn * 0.5 * (1 - ease.outCubic(p))); ctx.translate(-set.cx, -set.cy)
      ctx.drawImage(l.img, l.x, l.y)
      ctx.restore()
    })
  },

  // A dash drawn from one end to the other while it pops up to size.
  flick(ctx, t, api, d) {
    const { seg, ease } = api, l = api.layer(d.name), p = seg(t, d.start, d.start + FLICK)
    if (p <= 0) return
    const q = seg(t, d.start, d.start + FLICK_POP)
    if (q >= 1) { ctx.drawImage(l.img, l.x, l.y); return }
    const s = 0.55 + 0.45 * ease.outBack(q, 3), ang = Math.atan2(d.dy, d.dx), half = d.len / 2
    ctx.save()
    ctx.translate(d.cx, d.cy); ctx.rotate(ang); ctx.scale(s, s)
    ctx.beginPath(); ctx.rect(-half - 4, -200, (d.len + 8) * ease.outCubic(p), 400); ctx.clip()
    ctx.rotate(-ang); ctx.translate(-d.cx, -d.cy)
    ctx.drawImage(l.img, l.x, l.y)
    ctx.restore()
  },

  // A white dash flung out of the white blob, spinning, landing on a spring.
  fling(ctx, t, api, d) {
    const { seg, ease } = api, l = api.layer(d.name), p = seg(t, d.start, d.start + FLIGHT)
    if (p <= 0) return
    if (p >= 1) { ctx.drawImage(l.img, l.x, l.y); return }
    const e = ease.outBack(p, 1.3), w = this.white
    const x = w.cx + (d.cx - w.cx) * e, y = w.cy + (d.cy - w.cy) * e - Math.sin(Math.PI * p) * 60
    const s = 0.35 + 0.65 * ease.outCubic(p), rot = d.spin * Math.PI * 1.5 * (1 - ease.outCubic(p))
    ctx.save()
    ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s); ctx.translate(-d.cx, -d.cy)
    ctx.drawImage(l.img, l.x, l.y)
    ctx.restore()
  },

  // A layer revealed by a straight edge moving across it; from = -1 runs
  // right to left and slides the layer in from the right as it goes.
  wipe(ctx, t, api, name, a, b, x0, x1, from = 1) {
    const { seg, ease } = api, l = api.layer(name), p = seg(t, a, b)
    if (p <= 0) return
    if (p >= 1) { ctx.drawImage(l.img, l.x, l.y); return }
    const e = from > 0 ? ease.inOutCubic(p) : ease.outCubic(p), span = x1 - x0 + 40
    ctx.save()
    ctx.beginPath()
    if (from > 0) ctx.rect(x0 - 20, 0, span * e, api.H)
    else ctx.rect(x1 + 20 - span * e, 0, span * e + 400, api.H)
    ctx.clip()
    ctx.drawImage(l.img, l.x + (from > 0 ? 0 : 140 * (1 - e)), l.y)
    ctx.restore()
  },

  enter(ctx, t, api) {
    const { W, H, meta, seg } = api
    ctx.fillStyle = `rgb(${meta.paper.join(",")})`; ctx.fillRect(0, 0, W, H)

    for (const b of this.blobs) this.blob(ctx, t, api, b)

    this.wipe(ctx, t, api, "curves", CURVES, CURVES + 1.4, meta.curves.x0, meta.curves.x1)
    for (const set of this.rings) this.ringSet(ctx, t, api, set)
    meta.waves.forEach((w, i) => this.wipe(ctx, t, api, w.name, WAVES + i * 0.1, WAVES + i * 0.1 + 0.75, w.x0, w.x1, -1))
    for (const d of this.brown) this.flick(ctx, t, api, d)
    for (const d of this.whiteDashes) this.fling(ctx, t, api, d)

    // The last level or two of antialiasing, once everything has landed.
    const k = seg(t, 3.7, 4.1)
    if (k > 0) {
      const l = api.layer("polish")
      ctx.globalAlpha = k; ctx.drawImage(l.img, l.x, l.y); ctx.globalAlpha = 1
    }
  },

  // The blobs breathe out of phase, each a few percent about its centre.
  idle(ctx, t, api) {
    const { W, H, meta, TAU } = api, w = TAU / this.idleLength
    ctx.fillStyle = `rgb(${meta.paper.join(",")})`; ctx.fillRect(0, 0, W, H)
    this.blobs.forEach((b, i) => {
      const l = api.layer(b.name), s = 1 + 0.015 * Math.sin(w * t + i * 1.3)
      ctx.save(); ctx.translate(b.cx, b.cy); ctx.scale(s, 2 - s); ctx.translate(-b.cx, -b.cy)
      ctx.drawImage(l.img, l.x, l.y); ctx.restore()
    })
    for (const l of Object.values(api.layers)) if (!l.name.startsWith("blob_")) ctx.drawImage(l.img, l.x, l.y)
  },
})

// When each blob pops, and the seconds its spring takes to settle.
const POPS = { blob_pink_left: 0.3, blob_teal_top: 0.5, blob_lav: 0.68, blob_pink_right: 0.86, blob_teal_left: 1.04, blob_white: 1.3 }
const POP = 1.5
// Doodles: start times in seconds, and how long each piece takes.
const CURVES = 1.9, RINGS = { tl: 2.0, br: 2.3 }, RING = 0.75, RING_STAGGER = 0.07, WAVES = 2.4
const BROWN = 2.5, FLICK = 0.2, FLICK_POP = 0.4, FLING = 2.95, FLIGHT = 0.5
