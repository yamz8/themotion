// Totoro moonrise.
// Stars spiral into the centre, where the moon springs open with a pulse of
// light. Totoro rises into it and lands with a small squash, his whiskers draw
// out, the soot sprites pop in, he glances around and blinks.
themotion.scene({
  beats: { stars: 0.2, moon: 1.55, Totoro: 2.35, sprites: 2.95, blink: 4.3 },
  idleLength: 8,

  setup(api) {
    const { meta, W, H, blocks } = api
    this.cx = meta.cx; this.cy = meta.cy; this.R = meta.R
    this.ink = `rgb(${meta.ink.join(",")})`
    this.bg = `rgb(${meta.background.join(",")})`
    this.stars = blocks.starfield({ cx: this.cx, cy: this.cy, width: W, height: H, colors: [PINK, MAUVE, MAUVE] })
    this.sprites = Object.values(api.layers).filter(l => l.name.startsWith("sprite"))
  },

  // Totoro, whiskers, pupils and an optional blink, in wallpaper coordinates.
  totoro(ctx, api, { whiskers = 1, look = 0, lid = 0 }) {
    api.put("body"); api.put("belly")
    if (whiskers > 0) {
      // The face covers about ±240 px around the centre; whiskers end near ±440.
      const l = api.layer("whisker"), half = 240 + 215 * whiskers
      ctx.save(); ctx.beginPath(); ctx.rect(this.cx - half, l.y - 10, half * 2, l.h + 20); ctx.clip()
      api.put("whisker"); ctx.restore()
    }
    api.put("pupil", look, 0)
    if (lid > 0) {
      ctx.fillStyle = this.ink
      for (const [ex, ey] of EYES) {
        ctx.save(); ctx.beginPath(); ctx.arc(ex, ey, EYE_R, 0, api.TAU); ctx.clip()
        ctx.fillRect(ex - EYE_R - 2, ey - EYE_R - 2, EYE_R * 2 + 4, (EYE_R * 2 + 4) * lid); ctx.restore()
      }
    }
  },

  enter(ctx, t, api) {
    const { seg, ease, blocks, TAU } = api, { cx, cy, R } = this
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, api.W, api.H)

    // Stars twinkle in, then spiral into the centre.
    if (t < 2) this.stars.draw(ctx, t, { appear: [0.15, 0.95], pull: [0.9, 1.8] })

    // The moon: a bright seed, a shockwave, and the disc springing open.
    const moon = 1.55
    const rad = R * ease.spring(seg(t, moon, 2.85))
    blocks.glow(ctx, cx, cy, 160, PINK, 0.95 * Math.exp(-Math.pow((t - moon) / 0.22, 2)))
    blocks.halo(ctx, cx, cy, rad, MAUVE, Math.sin(Math.PI * seg(t, moon, 4.7)) * 0.55)
    blocks.shockwave(ctx, cx, cy, R * 0.2, R * 2.1, PINK, seg(t, moon, moon + 1.1))
    if (rad <= 0.5) return

    ctx.save()
    ctx.beginPath(); ctx.arc(cx, cy, rad, 0, TAU); ctx.fillStyle = blocks.plane(ctx, api.meta.coef, cx, cy, R); ctx.fill()
    ctx.clip()

    // Totoro rises from below the moon's edge and lands with a squash,
    // scaled about the moon's bottom edge.
    const up = (1 - ease.outBack(seg(t, 2.35, 3.45), 1.25)) * 1150
    const squash = ease.wobble(t - 3.45, 0.045)
    ctx.save()
    ctx.translate(cx, cy + R + up); ctx.scale(1 - squash * 0.6, 1 + squash); ctx.translate(-cx, -(cy + R))
    const glance = t => ease.inOutCubic(seg(t, 3.55, 3.85)) * -9 + ease.inOutCubic(seg(t, 4.1, 4.45)) * 18 + ease.inOutCubic(seg(t, 4.75, 5.0)) * -9
    this.totoro(ctx, api, {
      whiskers: ease.outCubic(seg(t, 3.25, 3.8)),
      look: glance(t),
      lid: Math.sin(Math.PI * seg(t, 4.3, 4.52)),
    })
    ctx.restore()

    // Soot sprites pop in, left cluster slightly after the right.
    this.sprites.forEach((l, i) => {
      blocks.popIn(ctx, l, t, { start: 2.95 + (i % 6) * 0.13 + (l.x < cx ? 0.07 : 0) + ((i * 37) % 10) / 80, settle: 5.0, seed: i + 7 })
    })
    ctx.restore()
  },

  // Settled picture with gentle motion that repeats every idleLength seconds:
  // sprites drift, the moon breathes, Totoro blinks once.
  idle(ctx, t, api) {
    const { TAU, blocks } = api, { cx, cy, R } = this, w = TAU / this.idleLength
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, api.W, api.H)
    blocks.halo(ctx, cx, cy, R, MAUVE, 0.12 + 0.08 * Math.sin(w * t))
    ctx.save()
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.fillStyle = blocks.plane(ctx, api.meta.coef, cx, cy, R); ctx.fill(); ctx.clip()
    this.totoro(ctx, api, { lid: Math.sin(Math.PI * api.seg(t, 3.0, 3.22)) })
    this.sprites.forEach((l, i) => {
      const dy = Math.sin(w * t * (1 + (i % 3)) + i) * 6, dx = Math.cos(w * t + i * 1.7) * 3
      ctx.drawImage(l.img, l.x + dx, l.y + dy)
    })
    ctx.restore()
  },
})

const PINK = "245,194,231", MAUVE = "203,166,247"
const EYES = [[1790, 1294], [2066, 1292]], EYE_R = 47
