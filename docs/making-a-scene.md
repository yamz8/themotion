# Making a scene

A scene turns one wallpaper into motion. It is a folder under `scenes/<theme>/<wallpaper-name>/` with three files, named after the wallpaper file so the installed video lands in the right place.

Start by copying `template/`.

## 1. Storyboard

Write down, in seconds, what happens. Keep it to one idea per beat and let everything be still by the pattern's `settle` time (5.0 s for intros). Totoro's:

| Time | Beat |
|---|---|
| 0.2 | Stars twinkle in |
| 0.9 | They spiral into the centre |
| 1.55 | A seed of light; the moon springs open with a shockwave and halo |
| 2.35 | Totoro rises into the moon and lands with a squash |
| 2.95 | Soot sprites pop in one by one |
| 3.55 | Totoro glances left, then right |
| 4.3 | One blink |
| 5.0 | Everything still; the pattern blends into the exact wallpaper |

Graphic wallpapers with flat shapes on a flat or smooth background work best: each shape can move on its own.

## 2. `scene.toml`

```toml
title = "Totoro moonrise"
theme = "catppuccin"        # the Omarchy theme folder
wallpaper = "1-totoro.webp" # in the theme's backgrounds/
pattern = "omarchy-intro@1"

[defaults]                  # optional overrides of the pattern's defaults
fade_in = 0.6
```

## 3. `split.py`: layers

`split(image, layers)` receives the wallpaper as a float RGB array and saves each movable shape with `layers.save(name, alpha, color)`. Anything the scene needs to know (centres, radii, colours) goes in `layers.meta`. Helpers in `lib/split.py`:

| Helper | Use |
|---|---|
| `fit_plane(image, mask)` | Fits a smooth gradient backdrop, so a shape's soft edges can be separated from it |
| `coverage(image, backdrop, ink)` | How much of a flat-colour shape covers each pixel, 0 to 1, keeping antialiasing |
| `components(mask)` | Labels connected shapes with sizes and centres |
| `nearest_label(labels, reach)` | Hands soft-edge pixels to the shape they belong to |
| `thin_parts(mask, width)` | Separates thin strokes, like whiskers, from a body |
| `circle_of(mask)` | Centre and radius of a round shape |
| `unmix(image, backdrop, ink)` | Coverage and per-pixel colour of a shape whose colour varies (grain, gradients) over a known backdrop |

Run `themotion split <scene>` and look at the PNGs in `build/.../layers/`. The layers drawn back in place should rebuild the wallpaper closely; the pattern's final blend covers the last few levels of difference.

## 4. `scene.js`: motion

```js
themotion.scene({
  beats: { moon: 1.55, Totoro: 2.35 },   // labels on the preview's timeline
  setup(api) { /* precompute once */ },
  enter(ctx, t, api) { /* draw the whole frame at time t, in wallpaper pixels */ },
  idle(ctx, t, api) { /* optional: gentle motion on the settled picture */ },
  idleLength: 8,                          // seconds before idle repeats
})
```

`enter` draws the full frame, background included, at time `t`, and must depend on nothing but `t`. The pattern handles the fade from black and the blend into the exact wallpaper, so the scene only needs to end with every layer in its original place.

The `api` gives you:

| | |
|---|---|
| `api.put(name, dx, dy)` | Draws a layer at its original position, optionally offset |
| `api.layer(name)` | A layer's `img`, `x`, `y`, `w`, `h` for custom transforms |
| `api.meta`, `api.W`, `api.H` | What `split.py` recorded; the wallpaper's size |
| `api.seg(t, a, b)` | Progress 0 to 1 between times `a` and `b` |
| `api.ease.*` | `outCubic`, `inOutCubic`, `outExpo`, `outBack`, `spring`, `wobble` and more |
| `api.blocks.*` | `starfield`, `glow`, `halo`, `shockwave`, `popIn` |
| `api.rng(seed)` | A seeded random generator, so particles land the same on every render |

## 5. Preview, render, check

```
themotion preview scenes/catppuccin/1-totoro --open
themotion make scenes/catppuccin/1-totoro
```

The preview page is self-contained, so it can be shared for review. `make` renders, encodes and checks; add `--install` to copy the video into the Omarchy checkout.

Checks pass on the file, but the handoff is a moment on a real screen: before shipping an intro, watch it play at login on an Omarchy machine.

## 6. `notes.md`

Credit the wallpaper's creator as far as it is known, and describe the storyboard in a sentence.
