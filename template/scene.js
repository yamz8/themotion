// Describe the scene's storyboard in a sentence or two here.
themotion.scene({
  beats: { shapes: 0.8 },

  setup(api) {
    this.shapes = Object.values(api.layers)
  },

  enter(ctx, t, api) {
    // The backdrop split.py fitted, without the shapes, over the whole screen.
    ctx.fillStyle = api.blocks.plane(ctx, api.meta.coef, api.W / 2, api.H / 2, Math.hypot(api.W, api.H) / 2)
    ctx.fillRect(0, 0, api.W, api.H)
    this.shapes.forEach((l, i) => {
      api.blocks.popIn(ctx, l, t, { start: 0.8 + i * 0.15, settle: api.spec.settle, seed: i + 1 })
    })
  },
})
