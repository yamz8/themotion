// Starfield: seeded stars that twinkle in, then optionally spiral into a
// point with short tapering streaks.
//
//   const stars = themotion.blocks.starfield({ cx, cy, width, height, colors })
//   stars.draw(ctx, t, { appear: [0.15, 0.95], pull: [0.9, 1.8] })
themotion.blocks.starfield = function ({ cx, cy, width, height, count = 220, seed = 0x70707, size = [1.6, 5.2], colors = ["255,255,255"] }) {
  const { TAU, clamp, seg, rng, ease } = themotion
  const r = rng(seed)
  const stars = Array.from({ length: count }, () => {
    const a = r() * TAU, d = Math.sqrt(r()) * 0.5 + 0.1
    return {
      x: cx + Math.cos(a) * width * d * 1.05, y: cy + Math.sin(a) * height * d * 1.25,
      s: size[0] + r() * (size[1] - size[0]), ph: r() * TAU, tw: 2 + r() * 5,
      born: r(), pull: 0.95 + r() * 0.55, spin: (r() < 0.5 ? -1 : 1) * (0.6 + r() * 0.9),
      color: colors[Math.floor(r() * colors.length)],
    }
  })

  function at(s, t, pull) {
    const p = pull ? ease.inCubic(clamp(seg(t, pull[0], pull[1]) * s.pull)) : 0
    const dx = s.x - cx, dy = s.y - cy
    const a = Math.atan2(dy, dx) + p * s.spin * 1.6, d = Math.hypot(dx, dy) * (1 - p)
    return [cx + Math.cos(a) * d, cy + Math.sin(a) * d, p]
  }

  return {
    draw(ctx, t, { appear = [0.15, 0.95], pull = null } = {}) {
      const span = appear[1] - appear[0]
      for (const s of stars) {
        const on = ease.outCubic(seg(t, appear[0] + s.born * span * 0.5, appear[0] + s.born * span * 0.5 + span * 0.5))
        if (on <= 0) continue
        const [x, y, p] = at(s, t, pull)
        const alpha = on * (0.6 + 0.4 * Math.sin(t * s.tw + s.ph)) * (1 - seg(p, 0.85, 1))
        if (alpha <= 0) continue
        const rad = s.s * (1 - 0.5 * p)
        if (p > 0.02) {
          const [x0, y0] = at(s, t - 0.07, pull)
          const g = ctx.createLinearGradient(x0, y0, x, y)
          g.addColorStop(0, `rgba(${s.color},0)`)
          g.addColorStop(1, `rgba(${s.color},${alpha * 0.6})`)
          ctx.strokeStyle = g; ctx.lineWidth = rad * 1.4; ctx.lineCap = "round"
          ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x, y); ctx.stroke()
        }
        ctx.fillStyle = `rgb(${s.color})`
        ctx.globalAlpha = alpha; ctx.beginPath(); ctx.arc(x, y, rad, 0, TAU); ctx.fill()
        ctx.globalAlpha = alpha * 0.25; ctx.beginPath(); ctx.arc(x, y, rad * 3, 0, TAU); ctx.fill()
      }
      ctx.globalAlpha = 1
    },
  }
}
