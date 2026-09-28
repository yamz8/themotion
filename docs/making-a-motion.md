# Making a motion

A motion brings one wallpaper to life. It takes two folders, both named after the wallpaper file so the installed video lands in the right place:

- `wallpapers/<theme>/<wallpaper>/` says how the wallpaper is cut into parts. It is written once, and every motion of that wallpaper shares it.
- `motions/<theme>/<wallpaper>/<motion>/` is one way of moving those parts. A wallpaper can have any number of them.

Every Omarchy wallpaper already has a folder under `wallpapers/` with its `wallpaper.toml`; `themotion catalog` lists them all with their kind and how far each has got. If the wallpaper already has a `split.py`, skip to step 3. For the motion, copy `template/motion/`.

## 1. Storyboard

Write down, in seconds, what happens. Keep it to one idea per beat and let everything be still by the pattern's `settle` time (5.0 s for intros). Totoro's moonrise:

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

## 2. The wallpaper: `wallpaper.toml`, `split.py`, `credit.md`

The folder is named after the file in the Omarchy theme's `backgrounds/`, without its extension, and the theme is the folder above. `wallpaper.toml` says what kind of picture it is and what it shows:

```toml
kind = "graphic"
about = "Totoro silhouette in a lilac moon with soot sprites, on dark navy"
```

The kind decides how the picture can be brought to life:

| Kind | What it is | How it moves |
|---|---|---|
| `logo` | The Omarchy wordmark on a flat colour | One motion can serve every theme |
| `graphic` | Flat shapes and line art | Split into shapes that move on their own |
| `pattern` | Repeated cells, dots or lines | Moves cell by cell |
| `scene` | An illustrated scene with depth | Split into depth bands and small objects |
| `dense` | A painting or photo | Real footage fitted with `themotion fit` (see [real-footage.md](real-footage.md)), or light effects |

`split.py` cuts it into layers. `split(image, layers)` receives the wallpaper as a float RGB array and saves each movable shape with `layers.save(name, alpha, color)`. Anything a motion needs to know (centres, radii, colours) goes in `layers.meta`. Helpers in `engine/split.py`:

| Helper | Use |
|---|---|
| `fit_plane(image, mask)` | Fits a smooth gradient backdrop, so a shape's soft edges can be separated from it |
| `coverage(image, backdrop, ink)` | How much of a flat-colour shape covers each pixel, 0 to 1, keeping antialiasing |
| `components(mask)` | Labels connected shapes with sizes and centres |
| `nearest_label(labels, reach)` | Hands soft-edge pixels to the shape they belong to |
| `thin_parts(mask, width)` | Separates thin strokes, like whiskers, from a body |
| `circle_of(mask)` | Centre and radius of a round shape |
| `unmix(image, backdrop, ink)` | Coverage and per-pixel colour of a shape whose colour varies (grain, gradients) over a known backdrop |

Run `themotion split wallpapers/<theme>/<wallpaper>` and look at the PNGs in `build/<theme>/<wallpaper>/layers/`. The layers drawn back in place should rebuild the wallpaper closely; the pattern's final blend covers the last few levels of difference.

A wallpaper without its own `split.py` uses the automatic split for its kind, when there is one in `engine/kinds/<kind>.py`. So far there is `logo.py`: it records the backdrop and ink colours, each letter, and every pixel block of the wordmark as `[x, y, w, h, letter]` in `layers.meta.cells`, cut so that the blocks drawn from the still tile the wordmark.

`credit.md` credits the wallpaper's creator as far as it is known, and any characters or marks it shows.

## 3. The motion: `scene.toml`

```toml
title = "Totoro moonrise"
pattern = "omarchy-intro@1"

[defaults]                  # optional overrides of the pattern's defaults
fade_in = 0.6
```

The wallpaper comes from the folder the motion sits in.

A motion that suits every wallpaper of one kind lives in `motions/shared/<motion>/` instead, and names the kind in its `scene.toml` (`kind = "logo"`); a `{wallpaper}` in its title becomes the wallpaper's name. Build it for one wallpaper with `--wallpaper THEME/NAME`, or for all of that kind with `--all`. It must draw from what the kind's split records, never from one wallpaper's positions.

A bright wallpaper needs a longer fade from black to keep each frame's step under the check's limit. When a motion doesn't set `fade_in`, themotion lengthens it from the wallpaper's brightness.

## 4. `scene.js`: the motion itself

```js
themotion.scene({
  beats: { moon: 1.55, Totoro: 2.35 },   // labels on the preview's timeline
  setup(api) { /* precompute once */ },
  enter(ctx, t, api) { /* draw the whole frame at time t, in wallpaper pixels */ },
  idle(ctx, t, api) { /* optional: gentle motion on the settled picture */ },
  idleLength: 8,                          // seconds before idle repeats
})
```

`enter` draws the full frame, background included, at time `t`, and must depend on nothing but `t`. The pattern handles the fade from black and the blend into the exact wallpaper, so the motion only needs to end with every layer in its original place.

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
themotion look motions/catppuccin/1-totoro/moonrise
themotion preview motions/catppuccin/1-totoro/moonrise --open
themotion make motions/catppuccin/1-totoro/moonrise
```

`look` renders small frames, puts one every half second on a single sheet (`build/.../look.png`) and says from when the frame is the wallpaper, which should be well before `settle`. It is the quickest way to see a motion, for a person or an agent.

The preview page is self-contained, so it can be shared for review. `make` splits, renders, encodes and checks; add `--install` to copy the video into the Omarchy checkout. The video is named after the wallpaper, so installing a motion makes it the theme's intro for that wallpaper.

Checks pass on the file, but the handoff is a moment on a real screen: before shipping an intro, watch it play at login on an Omarchy machine.

## 6. `notes.md`

Put the storyboard in the motion's `notes.md`, with a sentence on what happens and anything a later reader needs to know about how it is drawn.
