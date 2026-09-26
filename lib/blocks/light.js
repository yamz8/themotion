// Light effects built from radial gradients. Colours are "r,g,b" strings.

// A soft round glow; strength 0..1.
themotion.blocks.glow = function (ctx, x, y, radius, color, strength) {
  if (strength <= 0.005) return
  const g = ctx.createRadialGradient(x, y, 0, x, y, radius)
  g.addColorStop(0, `rgba(${color},${strength})`)
  g.addColorStop(1, `rgba(${color},0)`)
  ctx.fillStyle = g
  ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2)
}

// A halo hugging the outside of a circle of radius r; strength 0..1.
themotion.blocks.halo = function (ctx, x, y, r, color, strength, spread = 1.9) {
  if (strength <= 0.005 || r <= 1) return
  const g = ctx.createRadialGradient(x, y, r * 0.92, x, y, r * spread)
  g.addColorStop(0, `rgba(${color},${0.42 * strength})`)
  g.addColorStop(0.35, `rgba(${color},${0.12 * strength})`)
  g.addColorStop(1, `rgba(${color},0)`)
  ctx.fillStyle = g
  ctx.fillRect(x - r * spread, y - r * spread, r * spread * 2, r * spread * 2)
}

// A thin ring that races outward and fades; p is progress 0..1.
themotion.blocks.shockwave = function (ctx, x, y, from, to, color, p, width = 5) {
  if (p <= 0 || p >= 1) return
  ctx.save()
  ctx.globalAlpha = (1 - p) * 0.7
  ctx.strokeStyle = `rgb(${color})`
  ctx.lineWidth = width * (1 - p) + 1
  ctx.beginPath(); ctx.arc(x, y, from + themotion.ease.outExpo(p) * (to - from), 0, themotion.TAU); ctx.stroke()
  ctx.restore()
}

// A fill style reproducing a plane gradient fitted by split.fit_plane
// (colour = a + b*x + c*y per channel) across a circle of radius r at (x, y),
// or the whole canvas when r is omitted.
themotion.blocks.plane = function (ctx, coef, x, y, r) {
  const L = Math.hypot(coef[0][1], coef[0][2]) || 1, ux = coef[0][1] / L, uy = coef[0][2] / L
  const col = (px, py) => `rgb(${coef.map(c => themotion.clamp(c[0] + c[1] * px + c[2] * py, 0, 255).toFixed(1)).join(",")})`
  const g = ctx.createLinearGradient(x - ux * r, y - uy * r, x + ux * r, y + uy * r)
  g.addColorStop(0, col(x - ux * r, y - uy * r))
  g.addColorStop(1, col(x + ux * r, y + uy * r))
  return g
}
