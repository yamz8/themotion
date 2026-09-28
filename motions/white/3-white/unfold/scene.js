// White stationery.
// Each piece of paper slides in along the picture's diagonal, folded over on
// itself, and unfolds as it lands: the flap drops flat with a small paper
// bounce. The bottom sheet first, then the left sheet, the folder, and the two
// card stacks. The last stack lands with a tap that nudges its neighbour, and
// the folder's corner flicks up once before everything lies still.
themotion.scene({
  beats: { bottom: 0.3, left: 0.6, folder: 0.95, cards: 1.85, stack: 2.2, tap: 3.05, corner: 3.55 },
  idleLength: 8,

  setup(api) {
    const { meta, W, H, still } = api
    this.fill = api.layer("fill")
    this.pieces = ORDER.map(name => {
      const m = meta.pieces[name], plan = PLAN[name], l = api.layer("cut-" + name)
      // Pieces that run off the picture get a margin of stretched edge, so an
      // overshoot never shows where the photo ends.
      const pad = { l: m.off.left ? PAD : 0, t: m.off.top ? PAD : 0, r: m.off.right ? PAD : 0, b: m.off.bottom ? PAD : 0 }
      const cv = document.createElement("canvas")
      cv.width = l.w + pad.l + pad.r; cv.height = l.h + pad.t + pad.b
      const g = cv.getContext("2d")
      blit(g, still, l.x, l.y, l.w, l.h, pad)
      // The mask goes on its own canvas first: destination-in clears whatever
      // a single draw doesn't cover.
      const mask = document.createElement("canvas")
      mask.width = cv.width; mask.height = cv.height
      blit(mask.getContext("2d"), l.img, 0, 0, l.w, l.h, pad)
      g.globalCompositeOperation = "destination-in"
      g.drawImage(mask, 0, 0)
      const outline = m.outline.map(([x, y]) => [
        x < 0 ? x - PAD : x > W ? x + PAD : x,
        y < 0 ? y - PAD : y > H ? y + PAD : y,
      ])
      const c = outline.reduce((a, p) => [a[0] + p[0] / outline.length, a[1] + p[1] / outline.length], [0, 0])
      const fold = plan.fold, n = norm(fold.n)
      return { name, ...plan, cv, x: l.x - pad.l, y: l.y - pad.t, outline, c, fold: { P: fold.P, n }, dir: norm(plan.dir) }
    })
  },

  enter(ctx, t, api) {
    const { W, H } = api, base = ctx.getTransform()
    // The table: the still, with the bare table filled in under every piece.
    ctx.drawImage(api.still, 0, 0, W, H)
    ctx.drawImage(this.fill.img, 0, 0, W, H)

    // Landed pieces first, pieces still in the air on top of them.
    const states = this.pieces.map(p => ({ p, s: this.state(p, t, api) })).filter(({ s }) => s)
    states.sort((a, b) => (a.s.air > 0) - (b.s.air > 0) || a.p.slide[0] - b.p.slide[0])
    for (const { p, s } of states) {
      this.draw(ctx, base, p, s)
      ctx.setTransform(base)
    }
  },

  // Where a piece is at time t: its offset, spin, how far its flap is folded
  // (1 over, 0 flat), how much of its baked shadow shows and how high it is.
  state(p, t, api) {
    const { seg, ease } = api, [a, b] = p.slide, [u0, u1] = p.unfold
    if (t < a) return null
    const q = seg(t, a, b), e = ease.outBack(q, 1.25)
    let dx = -p.dir[0] * p.dist * (1 - e), dy = -p.dir[1] * p.dist * (1 - e)
    const rot = p.spin * (1 - ease.outCubic(q))
    let fold = drop(seg(t, u0, u1)), corner = 0
    if (p.nudge) {
      // Knocked by its neighbour landing: a short shove along the diagonal that springs back.
      const w = ease.wobble(t - p.nudge.at, 1, 7, 15)
      dx += p.nudge.v[0] * w; dy += p.nudge.v[1] * w
    }
    if (p.corner) corner = p.corner.lift * drop(seg(t, p.corner.at, p.corner.at + 0.7), true)
    const air = Math.max(1 - q, fold)
    return { dx, dy, rot, fold, corner, air, margin: seg(t, u1 - 0.3, u1 + 0.05) }
  },

  draw(ctx, base, p, s) {
    // The piece's own motion about its centre.
    const m = new DOMMatrix().translate(p.c[0] + s.dx, p.c[1] + s.dy).rotate(s.rot * 180 / Math.PI).translate(-p.c[0], -p.c[1])
    const moved = base.multiply(m)
    ctx.setTransform(moved)
    const still = s.fold <= 0 && s.corner <= 0 && s.rot === 0

    // A soft shadow under the piece while it is in the air.
    if (s.air > 0.001) {
      ctx.save()
      ctx.filter = `blur(${Math.max(1, 26 * s.air * base.a)}px)`
      ctx.fillStyle = `rgba(60,60,64,${0.3 * Math.min(1, s.air * 1.6)})`
      ctx.translate(-70 * s.air, 90 * s.air)
      this.shape(ctx, p, s)
      ctx.fill()
      ctx.restore()
    }

    if (still) {
      // Flat and in place: the whole cut, its baked shadow fading in as it lands.
      if (s.margin >= 1) { ctx.drawImage(p.cv, p.x, p.y); return }
      if (s.margin > 0) { ctx.globalAlpha = s.margin; ctx.drawImage(p.cv, p.x, p.y); ctx.globalAlpha = 1 }
      ctx.save(); path(ctx, p.outline); ctx.clip(); ctx.drawImage(p.cv, p.x, p.y); ctx.restore()
      return
    }

    // The flap folds about its line; the corner flick is a second, small flap.
    const flap = s.corner > 0 ? { ...p.corner, P: p.corner.P, n: norm(p.corner.n) } : p.fold
    const f = s.corner > 0 ? s.corner : s.fold
    // The part that stays down.
    if (s.margin > 0) {
      ctx.save(); ctx.globalAlpha = s.margin; half(ctx, flap, -1); ctx.clip(); ctx.drawImage(p.cv, p.x, p.y); ctx.restore()
    }
    ctx.save(); path(ctx, p.outline); ctx.clip(); half(ctx, flap, -1); ctx.clip(); ctx.drawImage(p.cv, p.x, p.y); ctx.restore()
    // The margin on the flap's side, around the paper but not under it.
    if (s.margin > 0) {
      ctx.save(); ctx.globalAlpha = s.margin; half(ctx, flap, 1); ctx.clip()
      ctx.beginPath(); ctx.rect(p.x - PAD, p.y - PAD, p.cv.width + 2 * PAD, p.cv.height + 2 * PAD)
      p.outline.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath()
      ctx.clip("evenodd"); ctx.drawImage(p.cv, p.x, p.y); ctx.restore()
    }

    // The flap: squashed towards its fold line by cos(angle), mirrored once it passes upright.
    const ang = Math.PI * f, k = Math.cos(ang), [nx, ny] = flap.n, d = flap.P[0] * nx + flap.P[1] * ny
    const F = new DOMMatrix([1 - (1 - k) * nx * nx, -(1 - k) * nx * ny, -(1 - k) * nx * ny, 1 - (1 - k) * ny * ny, (1 - k) * d * nx, (1 - k) * d * ny])
    ctx.setTransform(moved.multiply(F))
    ctx.save()
    path(ctx, p.outline); ctx.clip(); half(ctx, flap, 1); ctx.clip()
    ctx.drawImage(p.cv, p.x, p.y)
    // Shading: darkest edge-on, a little grey on its back.
    const shade = 0.13 * Math.sin(ang) + (k < 0 ? 0.05 : 0)
    if (shade > 0.002) { ctx.fillStyle = `rgba(40,40,48,${shade})`; ctx.fillRect(p.x - PAD, p.y - PAD, p.cv.width + 2 * PAD, p.cv.height + 2 * PAD) }
    ctx.restore()
    // A crisp crease along the fold while the flap is lifted.
    const crease = Math.min(1, f * 5) * 0.35
    if (crease > 0.01) {
      ctx.save(); path(ctx, p.outline); ctx.clip()
      ctx.strokeStyle = `rgba(255,255,255,${crease})`; ctx.lineWidth = 3
      const L = 9000; ctx.beginPath()
      ctx.moveTo(flap.P[0] - ny * L, flap.P[1] + nx * L); ctx.lineTo(flap.P[0] + ny * L, flap.P[1] - nx * L); ctx.stroke()
      ctx.restore()
    }
  },

  // The piece's footprint on the table, flap included, for its shadow.
  shape(ctx, p, s) {
    const flap = s.corner > 0 ? { P: p.corner.P, n: norm(p.corner.n) } : p.fold
    const k = Math.cos(Math.PI * (s.corner > 0 ? s.corner : s.fold)), [nx, ny] = flap.n
    ctx.beginPath()
    for (const [x, y] of p.outline) {
      const a = (x - flap.P[0]) * nx + (y - flap.P[1]) * ny
      const pull = a > 0 ? a * (1 - Math.max(k, 0)) : 0
      ctx.lineTo(x - pull * nx, y - pull * ny)
    }
    ctx.closePath()
  },
})

// Pieces in the order they arrive. dir is the way a piece travels, along the
// picture's diagonals; fold is its flap's line (P) and the side the flap is
// on (n); slide and unfold are their times in seconds.
const ORDER = ["bottom", "left", "folder", "cards", "stack"]
const PLAN = {
  bottom: { dir: [0.795, -0.606], dist: 1500, spin: -0.05, slide: [0.3, 1.3], unfold: [1.0, 1.85], fold: { P: [3136, 3019], n: [0.08, -0.997] } },
  left: { dir: [0.808, -0.589], dist: 1500, spin: 0.04, slide: [0.6, 1.6], unfold: [1.3, 2.15], fold: { P: [939, 2306], n: [0.99, 0.12] } },
  folder: { dir: [0.66, 0.75], dist: 1700, spin: 0.035, slide: [0.95, 2.1], unfold: [1.8, 2.75], fold: { P: [1673, 1562], n: [0.542, 0.84] },
    corner: { at: 3.55, lift: 0.4, P: [2098, 1911], n: [-0.14, 0.99] } },
  cards: { dir: [-0.8, 0.6], dist: 1900, spin: -0.06, slide: [1.85, 2.65], unfold: [2.3, 3.05], fold: { P: [4400, 712], n: [-0.971, -0.239] },
    nudge: { at: 3.05, v: [-0.6, -0.8].map(v => v * 45) } },
  stack: { dir: [-0.793, -0.609], dist: 1700, spin: 0.05, slide: [2.2, 3.0], unfold: [2.55, 3.05], fold: { P: [5328, 1512], n: [-0.986, -0.168] } },
}
const PAD = 400

function norm([x, y]) { const l = Math.hypot(x, y); return [x / l, y / l] }

// A flap falling flat: it drops like paper, then bounces twice. With `flick`
// it rises first (a corner lifting) and falls back the same way.
function drop(p, flick = false) {
  if (p <= 0) return flick ? 0 : 1
  if (p >= 1) return 0
  if (flick) {
    if (p < 0.35) return Math.sin(Math.PI / 2 * p / 0.35)
    p = (p - 0.35) / 0.65
  }
  const hop = (a, b, h) => { const q = (p - a) / (b - a); return 4 * h * q * (1 - q) }
  if (p < 0.6) return 1 - Math.pow(p / 0.6, 2)
  if (p < 0.84) return hop(0.6, 0.84, 0.13)
  return hop(0.84, 1, 0.04)
}

function path(ctx, pts) {
  ctx.beginPath(); pts.forEach(([x, y]) => ctx.lineTo(x, y)); ctx.closePath()
}

// One side of a fold line: side 1 is the flap's, -1 the rest.
function half(ctx, { P, n }, side) {
  const L = 20000, [nx, ny] = n, tx = -ny, ty = nx
  ctx.beginPath()
  ctx.moveTo(P[0] - tx * L, P[1] - ty * L); ctx.lineTo(P[0] + tx * L, P[1] + ty * L)
  ctx.lineTo(P[0] + tx * L + side * nx * L, P[1] + ty * L + side * ny * L)
  ctx.lineTo(P[0] - tx * L + side * nx * L, P[1] - ty * L + side * ny * L)
  ctx.closePath()
}

// Draw a rect of img at `pad` into g, stretching its outermost pixels across
// any padded side.
function blit(g, img, sx, sy, sw, sh, pad) {
  g.drawImage(img, sx, sy, sw, sh, pad.l, pad.t, sw, sh)
  g.imageSmoothingEnabled = false
  if (pad.l) g.drawImage(img, sx, sy, 1, sh, 0, pad.t, pad.l, sh)
  if (pad.r) g.drawImage(img, sx + sw - 1, sy, 1, sh, pad.l + sw, pad.t, pad.r, sh)
  if (pad.t) g.drawImage(img, sx, sy, sw, 1, pad.l, 0, sw, pad.t)
  if (pad.b) g.drawImage(img, sx, sy + sh - 1, sw, 1, pad.l, pad.t + sh, sw, pad.b)
  g.imageSmoothingEnabled = true
}
