// Rose Pine Omarchy plants.
// The sun rises from behind the hill. The plants spring up out of the ground
// in a wave from each edge towards the middle, whipping upright as they grow,
// and the sprouts pop up around them. The letters of OMARCHY drop in one by
// one and land with a squash, then a breeze runs through the plants from left
// to right before everything settles.

// Timings in seconds. The plants wave in over GROW_SPREAD and each column
// springs for GROW_TIME; from STILL they are drawn as they are in the wallpaper.
const SUN = 0.55, GROW = 1.2, GROW_SPREAD = 0.35, GROW_TIME = 1.6, SPROUTS = 2.3, LETTERS = 2.45, FALL = 0.42
const BREEZE = 3.7, STILL = 4.95
// Wallpaper px the warp may reach beyond a cluster sideways.
const MARGIN = 160

themotion.scene({
  beats: { sun: SUN, plants: GROW, letters: LETTERS, sprouts: SPROUTS, breeze: BREEZE },
  idleLength: 8,

  setup(api) {
    const { meta, W, rng } = api
    this.letters = [...Array(7).keys()].map(j => ({ layer: api.layer(`letter${j}`), bottom: meta.letters[j] }))
    this.sprouts = Object.values(api.layers).filter(l => l.name.startsWith("sprout"))
    this.clusters = ["plantsL", "plantsR"].map((name, i) => {
      const layer = api.layer(name), r = rng(5 + i)
      return {
        layer, base: meta.base[name], height: meta.base[name] - layer.y,
        // Each cluster grows from its outer edge in.
        outer: i === 0 ? layer.x : layer.x + layer.w, dir: i === 0 ? 1 : -1,
        phase: [r(), r(), r()].map(v => v * api.TAU),
      }
    })
    // The sky above the ground's edge, for the sun to rise behind the hill.
    const e = meta.edge, step = meta.edge_step
    this.sky = new Path2D()
    this.sky.moveTo(0, 0); this.sky.lineTo(W, 0); this.sky.lineTo(W, e[e.length - 1])
    for (let k = e.length - 2; k >= 0; k--) this.sky.lineTo(k * step, e[k])
    this.sky.closePath()
    this.horizon = e[Math.round(meta.sun[0] / step)]
  },

  // How far a column of plants has grown (springing past 1 and back) and how
  // far it bends, at wallpaper x and time t.
  growth(c, x, t, api) {
    const { seg, ease, W } = api, [a, b, d] = c.phase
    const noise = (Math.sin(x / 97 + a) + Math.sin(x / 53 + b) + Math.sin(x / 211 + d)) / 3
    const start = GROW + GROW_SPREAD * Math.abs(x - c.outer) / c.layer.w + 0.08 * noise
    const p = seg(t, start, start + GROW_TIME)
    // A damped spring that lands exactly on 1 when p does.
    const g = 1 - Math.exp(-3.5 * p) * Math.cos(8 * p) * (1 - p)
    // Grown plants whip upright from a lean towards where the wave came from.
    let bend = -c.dir * 0.15 * Math.pow(1 - ease.outCubic(p), 2)
    // The breeze: a gust that runs left to right and rings out.
    const calm = 1 - ease.inOutCubic(seg(t, 4.3, 4.95))
    bend += 0.16 * ease.wobble(t - BREEZE - 0.6 * x / W, 1, 2.4, 7) * calm
    return { g, bend }
  },

  // Draw a cluster warped column by column: each column scaled up from the
  // ground by g and bent sideways by bend times the square of the height.
  // Resampled per device pixel, so neighbouring columns leave no seams.
  warp(ctx, c, t, api, field) {
    const k = ctx.getTransform().a, L = c.layer
    if (!c.src || c.k !== k) this.prepare(c, k)
    const { src, sw, sh, ox, oy } = c
    const x0 = Math.floor((L.x - MARGIN) * k), x1 = Math.ceil((L.x + L.w + MARGIN) * k)
    const y0 = Math.floor((c.base - 1.3 * c.height) * k), y1 = Math.ceil((L.y + L.h) * k)
    const dw = x1 - x0, dh = y1 - y0
    if (!c.out || c.out.width !== dw || c.out.height !== dh) {
      c.out = document.createElement("canvas"); c.out.width = dw; c.out.height = dh
      c.octx = c.out.getContext("2d")
    }
    const img = c.octx.createImageData(dw, dh), o = img.data, H = c.height
    for (let X = 0; X < dw; X++) {
      const x = (x0 + X + 0.5) / k, { g, bend } = field(c, x, t, api)
      if (g <= 0.002) continue
      for (let Y = 0; Y < dh; Y++) {
        const y = (y0 + Y + 0.5) / k, hs = (c.base - y) / g
        const u = (x - bend * hs * hs / H) * k - ox - 0.5, v = (c.base - hs) * k - oy - 0.5
        if (u < -1 || v < -1 || u >= sw || v >= sh) continue
        // Bilinear, on premultiplied colour so edges don't darken.
        const i = Math.floor(u), j = Math.floor(v), fu = u - i, fv = v - j
        let r = 0, gg = 0, bb = 0, al = 0
        for (let q = 0; q < 4; q++) {
          const ii = i + (q & 1), jj = j + (q >> 1)
          if (ii < 0 || jj < 0 || ii >= sw || jj >= sh) continue
          const wgt = (q & 1 ? fu : 1 - fu) * (q >> 1 ? fv : 1 - fv), s = (jj * sw + ii) * 4
          r += src[s] * wgt; gg += src[s + 1] * wgt; bb += src[s + 2] * wgt; al += src[s + 3] * wgt
        }
        if (al <= 0) continue
        const d = (Y * dw + X) * 4
        o[d] = r / al * 255; o[d + 1] = gg / al * 255; o[d + 2] = bb / al * 255; o[d + 3] = al * 255
      }
    }
    c.octx.putImageData(img, 0, 0)
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.drawImage(c.out, x0, y0); ctx.restore()
  },

  // The cluster at device scale k, as premultiplied floats.
  prepare(c, k) {
    const L = c.layer, ox = Math.floor(L.x * k), oy = Math.floor(L.y * k)
    const sw = Math.ceil((L.x + L.w) * k) - ox + 1, sh = Math.ceil((L.y + L.h) * k) - oy + 1
    const cv = document.createElement("canvas"); cv.width = sw; cv.height = sh
    const cx = cv.getContext("2d")
    cx.setTransform(k, 0, 0, k, L.x * k - ox, L.y * k - oy); cx.drawImage(L.img, 0, 0)
    const data = cx.getImageData(0, 0, sw, sh).data, src = new Float32Array(data.length)
    for (let s = 0; s < data.length; s += 4) {
      const a = data[s + 3] / 255
      src[s] = data[s] * a / 255; src[s + 1] = data[s + 1] * a / 255; src[s + 2] = data[s + 2] * a / 255; src[s + 3] = a
    }
    Object.assign(c, { src, sw, sh, ox, oy, k })
  },

  enter(ctx, t, api) {
    const { seg, ease, blocks, meta } = api
    api.put("backdrop")

    // The sun rises from behind the hill and springs into place.
    const sun = api.layer("sun"), [, cy, R] = meta.sun
    const rise = (1 - ease.outBack(seg(t, SUN, SUN + 1.5), 1.4)) * (this.horizon - cy + R + 20)
    if (rise < this.horizon - cy + R) {
      ctx.save(); ctx.clip(this.sky); api.put("sun", 0, rise); ctx.restore()
    }

    for (const c of this.clusters) {
      if (t >= STILL) api.put(c.layer.name)
      else if (t >= GROW - 0.3) this.warp(ctx, c, t, api, this.growth)
    }

    this.sprouts.forEach((l, i) => {
      const from = Math.min(l.x, api.W - l.x - l.w) / (api.W / 2)
      blocks.popIn(ctx, l, t, { start: SPROUTS + 0.9 * from + 0.05 * (i % 3), duration: 0.45, settle: 4.6, rise: 40, bob: 6, seed: i + 3 })
    })

    // The letters drop in from above one by one and land with a squash,
    // anchored at their own bottom edge.
    this.letters.forEach(({ layer: l, bottom }, j) => {
      const start = LETTERS + j * 0.13, land = start + FALL
      if (t < start) return
      const fall = (1 - ease.inCubic(seg(t, start, land))) * (bottom + 40)
      const sq = t < land + 1.2 ? ease.wobble(t - land, 0.28, 6.5, 17) : 0
      const cx = l.x + l.w / 2
      ctx.save()
      ctx.translate(cx, bottom - fall); ctx.scale(1 + sq * 0.6, 1 - sq); ctx.translate(-cx, -bottom)
      ctx.drawImage(l.img, l.x, l.y)
      ctx.restore()
    })
  },

  // A slow breeze through the plants that repeats every idleLength.
  idle(ctx, t, api) {
    const w = api.TAU / this.idleLength
    api.put("backdrop"); api.put("sun")
    for (const c of this.clusters) {
      this.warp(ctx, c, t, api, (c, x) => ({ g: 1, bend: 0.025 * Math.sin(w * t - x / 700) }))
    }
    for (const l of this.sprouts) ctx.drawImage(l.img, l.x, l.y)
    for (const { layer: l } of this.letters) ctx.drawImage(l.img, l.x, l.y)
  },
})
