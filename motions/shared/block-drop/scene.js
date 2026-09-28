// The wordmark is built from its own pixel blocks. One block of the O blinks
// like a cursor; then each letter's blocks fall in from above the screen and
// stack up, bottom row first and left letter first. Each letter squashes as
// its last block lands, a hop runs along the word, and the last slivers fade
// in from the still, so the frame is the wallpaper from 4.4 s.
const FALL = 0.42      // seconds a block takes to fall
const CALM = [4.0, 4.4] // every wobble is gone, and the still fully in, by the end of this

themotion.scene({
  beats: { cursor: 0.35, drop: 0.95, hop: 3.15, exact: CALM[1] },

  setup(api) {
    const { cells, letters, box, bg } = api.meta
    const r = api.rng(7)
    this.bg = `rgb(${bg.map(Math.round).join(",")})`
    this.base = box[3]
    this.letters = letters.map(([x0, x1]) => ({ cx: (x0 + x1) / 2, blocks: [] }))
    cells.forEach(([x, y, w, h, k]) => this.letters[k].blocks.push({ x, y, w, h }))

    // The cursor: the O's lowest block on its left side, already in place.
    const o = this.letters[0].blocks
    const bottom = Math.max(...o.map(b => b.y))
    this.cursor = o.filter(b => b.y >= bottom - api.meta.pitch).sort((a, b) => a.x - b.x)[0]
    this.cursor.t0 = -1

    this.letters.forEach((l, k) => {
      // Bottom rows first, and each row from the letter's middle outward.
      const falling = l.blocks.filter(b => b !== this.cursor)
      falling.sort((a, b) => (b.y - a.y) || (Math.abs(a.x + a.w / 2 - l.cx) - Math.abs(b.x + b.w / 2 - l.cx)))
      falling.forEach((b, j) => {
        b.t0 = 0.95 + k * 0.2 + (j / falling.length) * 0.8 + r() * 0.05
        b.drop = b.y + b.h + 120 + r() * 380  // starts above the top of the screen
      })
      l.done = Math.max(...falling.map(b => b.t0)) + FALL
      l.hop = 3.15 + k * 0.1
    })
  },

  enter(ctx, t, api) {
    const { ease, seg } = api
    const calm = 1 - ease.inOutCubic(seg(t, CALM[0], CALM[1]))
    ctx.fillStyle = this.bg
    ctx.fillRect(0, 0, api.W, api.H)

    for (const l of this.letters) {
      // The letter's squash when its last block lands, and its hop later.
      const h = seg(t, l.hop, l.hop + 0.45)
      const lift = 4 * h * (1 - h) * 70 * calm
      const squash = (ease.wobble(t - l.done, 0.12, 7, 20) + ease.wobble(t - l.hop - 0.45, 0.1, 8, 22)) * calm
      const sy = 1 - squash, sx = 1 + squash * 0.6

      for (const b of l.blocks) {
        if (b === this.cursor && t < 0.95) {
          if (t < 0.35 || (t > 0.55 && t < 0.7)) continue  // blinks on, off, on
        } else if (t < b.t0) continue
        const p = seg(t, b.t0, b.t0 + FALL)
        // Falls from rest under gravity, then bounces a little on landing.
        const dy = -b.drop * (1 - p * p) - Math.abs(ease.wobble(t - b.t0 - FALL, 16, 9, 24)) * calm
        const x = l.cx + (b.x - l.cx) * sx
        const y = this.base + (b.y + dy - this.base) * sy - lift
        ctx.drawImage(api.still, b.x, b.y, b.w, b.h, x, y, b.w * sx, b.h * sy)
      }
    }

    // Slivers the grid can't hold and any soft edges, from the still itself.
    const rest = 1 - calm
    if (rest > 0) { ctx.globalAlpha = rest; ctx.drawImage(api.still, 0, 0, api.W, api.H); ctx.globalAlpha = 1 }
  },
})
