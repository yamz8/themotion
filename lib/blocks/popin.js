// Pop a layer into place: it rises a little, scales up with overshoot, and
// bobs and rocks until `settle`, landing exactly where the wallpaper has it.
//
//   themotion.blocks.popIn(ctx, api.layer("sprite3"), t, { start: 3.1, settle: 5.0, seed: 3 })
themotion.blocks.popIn = function (ctx, layer, t, { start, duration = 0.5, settle, rise = 70, bob = 10, overshoot = 2.2, seed = 1 }) {
  const { TAU, seg, rng, ease } = themotion
  const p = seg(t, start, start + duration)
  if (p <= 0) return
  const r = rng(seed)
  const amp = bob * (0.6 + r()), ph = r() * TAU, f = 2.2 + r() * 1.6
  const calm = 1 - ease.inOutCubic(seg(t, settle - 0.9, settle))
  const dy = (1 - ease.outCubic(p)) * rise + Math.sin((t - start) * f * TAU / 2 + ph) * amp * calm
  const rot = Math.sin((t - start) * 3 + ph) * 0.12 * calm
  const s = ease.outBack(p, overshoot)
  ctx.save()
  ctx.translate(layer.x + layer.w / 2, layer.y + layer.h / 2 + dy)
  ctx.rotate(rot); ctx.scale(s, s)
  ctx.drawImage(layer.img, -layer.w / 2, -layer.h / 2)
  ctx.restore()
}
