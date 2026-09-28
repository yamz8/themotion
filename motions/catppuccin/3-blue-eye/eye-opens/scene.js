// Blue eye opens.
// A seed of light at the centre, the swirl of rays shoots out of the pupil,
// and a glowing pen sweeps once around to trace the ring of petals, which spins
// down into place. The ring closes with a pulse; the eye blinks, its pupil
// dilates, and it glances left and right before settling.
themotion.scene({
  beats: { seed: 0.3, rays: 0.55, trace: 1.25, pulse: 2.55, blink: 3.15, glance: 3.75 },
  idleLength: 8,

  setup(api) {
    const { meta } = api
    this.cx = meta.cx; this.cy = meta.cy
    this.pupil = meta.pupil; this.seam = meta.seam; this.outer = meta.outer
    this.bg = `rgb(${meta.background.join(",")})`
  },

  // The whole eye, squashed by `lid` (1 open, 0 shut) and pulsed by `pulse`,
  // with a halo of strength `glow` outside it.
  eye(ctx, api, { lid = 1, pulse = 0, glow = 0, rays = this.seam, spinRays = 0, trace = api.TAU, spinPetals = 0, look = 0, dilate = 0 }) {
    const { cx, cy, pupil, seam } = this, TAU = api.TAU
    ctx.save()
    ctx.translate(cx, cy); ctx.scale(1 + pulse, (1 + pulse) * lid); ctx.translate(-cx, -cy)

    // The halo block fills its inside too, so keep it outside the eye.
    if (glow > 0.005) {
      const out = this.outer * 2
      ctx.save()
      ctx.beginPath(); ctx.rect(cx - out, cy - out, out * 2, out * 2); ctx.arc(cx, cy, this.outer * 0.97, 0, TAU); ctx.clip("evenodd")
      api.blocks.halo(ctx, cx, cy, this.outer, BLUE, glow)
      ctx.restore()
    }

    // The rays, clipped to the circle they have grown to, looking sideways inside the ring.
    if (rays > pupil) {
      ctx.save()
      ctx.beginPath(); ctx.arc(cx, cy, Math.min(rays, seam), 0, TAU); ctx.clip()
      spin(ctx, cx, cy, look, spinRays, () => api.put("rays"))
      ctx.beginPath(); ctx.arc(cx + look, cy, pupil * (1 + dilate), 0, TAU); ctx.fillStyle = this.bg; ctx.fill()
      ctx.restore()
    }

    // The petals, revealed clockwise from the top by the pen's sweep.
    if (trace > 0) {
      ctx.save()
      if (trace < TAU) {
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, this.outer * 1.2, -TAU / 4, -TAU / 4 + trace); ctx.closePath(); ctx.clip()
      }
      spin(ctx, cx, cy, look * 0.2, spinPetals, () => api.put("petals"))
      ctx.restore()
    }
    ctx.restore()
  },

  enter(ctx, t, api) {
    const { seg, ease, blocks, TAU } = api, { cx, cy, pupil, seam, outer } = this
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, api.W, api.H)

    // A seed of light where the pupil will be.
    blocks.glow(ctx, cx, cy, seam * 1.1, BLUE, 0.9 * Math.exp(-Math.pow((t - 0.45) / 0.28, 2)))

    // The rays shoot out and twist into place.
    const grow = ease.outCubic(seg(t, 0.55, 1.35))
    const rays = pupil + (seam - pupil) * grow

    // The pen sweeps around once; the petals spin down behind it.
    const sweep = seg(t, 1.25, 2.45)
    const trace = TAU * ease.inOutCubic(sweep)

    // Blink, then the pupil dilates as the eye opens and eases back.
    const lid = 1 - 0.96 * Math.sin(Math.PI * seg(t, 3.15, 3.45))
    const dilate = 0.55 * ease.outCubic(seg(t, 3.3, 3.65)) * (1 - ease.inOutCubic(seg(t, 3.95, 4.85)))
    const look = ease.inOutCubic(seg(t, 3.75, 4.0)) * -34 + ease.inOutCubic(seg(t, 4.2, 4.5)) * 68 + ease.inOutCubic(seg(t, 4.7, 4.95)) * -34

    this.eye(ctx, api, {
      lid, dilate, look, rays, trace,
      glow: Math.sin(Math.PI * seg(t, 2.4, 4.8)) * 0.45,
      pulse: ease.wobble(t - 2.5, 0.06, 4.5, 15),
      spinRays: -(1 - ease.outCubic(seg(t, 0.55, 1.7))) * 1.3,
      spinPetals: -(1 - ease.outCubic(seg(t, 1.25, 2.8))) * 0.8,
    })

    // A bright front on the growing rays.
    if (grow > 0 && grow < 1) ring(ctx, cx, cy, rays, INK, (1 - grow) * 0.9, 6, TAU)

    // The pen: a light on the sweep's edge with a fading trail.
    if (sweep > 0 && sweep < 1) {
      const on = Math.sin(Math.PI * sweep), mid = (seam + outer) / 2
      for (let k = 0; k < 8; k++) {
        const a = -TAU / 4 + trace - k * 0.06
        blocks.glow(ctx, cx + Math.cos(a) * mid, cy + Math.sin(a) * mid, 150 - k * 12, SKY, on * 0.75 * Math.pow(0.7, k))
      }
      const a = -TAU / 4 + trace
      ctx.save()
      ctx.globalAlpha = on * 0.8; ctx.strokeStyle = `rgb(${INK})`; ctx.lineWidth = 4; ctx.lineCap = "round"
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * seam, cy + Math.sin(a) * seam); ctx.lineTo(cx + Math.cos(a) * outer, cy + Math.sin(a) * outer); ctx.stroke()
      ctx.restore()
    }

  },

  // Settled picture: the halo breathes, the pupil breathes, one blink.
  idle(ctx, t, api) {
    const { TAU, seg } = api, w = TAU / this.idleLength
    ctx.fillStyle = this.bg; ctx.fillRect(0, 0, api.W, api.H)
    this.eye(ctx, api, {
      glow: 0.1 + 0.08 * Math.sin(w * t),
      lid: 1 - 0.96 * Math.sin(Math.PI * seg(t, 5.0, 5.3)),
      dilate: 0.12 * (1 - Math.cos(w * t)),
    })
  },
})

// Draw rotated by `angle` about the eye's centre (cx, cy), shifted right by dx.
function spin(ctx, cx, cy, dx, angle, draw) {
  ctx.save(); ctx.translate(cx + dx, cy); ctx.rotate(angle); ctx.translate(-cx, -cy); draw(); ctx.restore()
}

function ring(ctx, x, y, r, color, alpha, width, TAU) {
  if (alpha <= 0.005) return
  ctx.save()
  ctx.globalAlpha = alpha; ctx.strokeStyle = `rgb(${color})`; ctx.lineWidth = width
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.stroke()
  ctx.restore()
}

const INK = "150,205,251", BLUE = "137,180,250", SKY = "137,220,235"
