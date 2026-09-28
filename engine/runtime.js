// themotion runtime: loads a scene's layers, draws frames for a pattern, and
// exposes a render hook for the offline renderer. Every frame is a pure
// function of time, so previews, renders and re-renders always agree.
(() => {
  const TAU = Math.PI * 2
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x))
  const seg = (t, a, b) => clamp((t - a) / (b - a))
  const lerp = (a, b, t) => a + (b - a) * t

  // Small seeded PRNG (mulberry32), so particles land the same on every render.
  function rng(seed) {
    return () => {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed)
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t
      return ((t ^ t >>> 14) >>> 0) / 4294967296
    }
  }

  const blocks = {}
  let sceneDef = null

  const themotion = window.themotion = {
    TAU, clamp, seg, lerp, rng, blocks,
    ease: null, // filled in by ease.js
    scene(def) { sceneDef = def },
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve(img)
      img.onerror = () => reject(new Error("could not load an image layer"))
      img.src = src
    })
  }

  // Boot: called by the page once the scene script has registered itself.
  themotion.boot = async function (canvas, config) {
    const { spec, meta, images } = config
    const names = Object.keys(images)
    const loaded = await Promise.all(names.map(n => loadImage(images[n])))
    const img = Object.fromEntries(names.map((n, i) => [n, loaded[i]]))
    const layers = Object.fromEntries((meta.layers || []).map(l => [l.name, { ...l, img: img[l.name] }]))

    const W = meta.width, H = meta.height
    const scale = config.scale || spec.width / W
    canvas.width = Math.round(W * scale)
    canvas.height = Math.round(H * scale)
    const ctx = canvas.getContext("2d")

    const api = {
      ...themotion, W, H, meta, spec, layers, still: img.still,
      layer: name => layers[name],
      put(name, dx = 0, dy = 0) { const l = layers[name]; ctx.drawImage(l.img, l.x + dx, l.y + dy) },
    }
    const scene = sceneDef
    if (scene.setup) scene.setup(api)

    function base() {
      ctx.setTransform(scale, 0, 0, scale, 0, 0)
      ctx.globalAlpha = 1
      ctx.globalCompositeOperation = "source-over"
    }

    // omarchy-intro: the scene's entrance, a blend into the exact still from
    // `settle`, and a fade in from black over the first `fade_in` seconds.
    function intro(t) {
      base()
      scene.enter(ctx, Math.min(t, spec.settle + spec.handoff), api)
      base()
      const h = themotion.ease.inOutCubic(seg(t, spec.settle, spec.settle + spec.handoff))
      if (h > 0) { ctx.globalAlpha = h; ctx.drawImage(img.still, 0, 0, W, H); ctx.globalAlpha = 1 }
      // Linear, so no frame jumps more than brightness / (fade_in * fps).
      const f = 1 - seg(t, 0, spec.fade_in)
      if (f > 0) { ctx.fillStyle = `rgba(0,0,0,${f})`; ctx.fillRect(0, 0, W, H) }
    }

    // Idle motion on the settled picture; the base of a future looping pattern.
    function idle(t) {
      base()
      if (scene.idle) scene.idle(ctx, t, api)
      else ctx.drawImage(img.still, 0, 0, W, H)
    }

    function still() { base(); ctx.drawImage(img.still, 0, 0, W, H) }

    return {
      scene, length: spec.length, fps: spec.fps, idleLength: scene.idleLength || 8,
      intro, idle, still,
    }
  }
})()
