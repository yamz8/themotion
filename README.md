# themotion

Motion for [Omarchy](https://omarchy.org) themes, made from their wallpapers. Theme + motion.

A theme's wallpaper is split into layers, and a small scene script moves those layers in code: a moon springs open, a character rises into it, stars fall in. Every frame is a function of time, so the live preview, the final render and any later re-render always agree. A pattern decides what kind of video comes out and checks it: today that is Omarchy's boot intro, which fades in from black and lands on the exact wallpaper.

```
themotion make scenes/catppuccin/1-totoro --omarchy ~/omarchy
```

```
split 15 layers into build/catppuccin/1-totoro/layers
rendered 180 frames
video: build/catppuccin/1-totoro/intros/1-totoro.mp4
pass  length       6.00 s (allowed 5.0-7.0 s)
pass  codec        h264 yuv420p
pass  color        colour matrix bt709 (Omarchy reads HD as BT.709)
pass  start        first frame luma 0.0 (max 12)
pass  fade         largest step 3.0 per frame (max 12)
pass  end          last frame vs wallpaper: mean 0.04, max 11 (max 0.3 / 24)
```

## Requirements

- Linux with `ffmpeg`, `node` 20+, [`uv`](https://docs.astral.sh/uv/), and Chromium or Chrome (Omarchy ships all but uv)
- An Omarchy checkout, for the wallpapers; pass `--omarchy PATH` or set `$OMARCHY_PATH`

Python and Node dependencies install themselves on first run.

## Commands

| Command | What it does |
|---|---|
| `themotion split <scene>` | Splits the scene's wallpaper into layers under `build/` |
| `themotion preview <scene> [--open]` | Builds a self-contained preview page with play, scrub, and a wallpaper comparison |
| `themotion render <scene>` | Draws every frame at the wallpaper's full size in headless Chromium |
| `themotion finish <scene> [--install]` | Encodes the video; `--install` copies it into the theme with its wallpaper hash |
| `themotion check <video> <wallpaper>` | Checks a video against its pattern, whoever made it |
| `themotion make <scene> [--install]` | All of the above in order |

`--set key=value` overrides a pattern default for one run, for example `--set length=6.5` or `--set fade_in=1.0`.

## How it fits together

- **Patterns** (`patterns/*.toml`) are output contracts. `[requires]` lists what the target needs, which nothing may override; `[defaults]` are taste, which scenes override. `themotion check` enforces the requirements. See [docs/patterns.md](docs/patterns.md).
- **Scenes** (`scenes/<theme>/<wallpaper>/`) hold `scene.toml`, `split.py` and `scene.js`. A scene draws an `enter` (how the picture builds up) and optionally an `idle` (gentle motion on the settled picture, for future looping patterns). See [docs/making-a-scene.md](docs/making-a-scene.md).
- **Blocks** (`lib/blocks/`) are reusable motion: a starfield, glows and halos, a shockwave, and a pop-in with overshoot and bob.
- **Layers are never committed.** They are derived from the wallpaper at build time, so this repository contains code, not artwork.

Paintings and photos don't split into clean layers; for those, see [docs/real-footage.md](docs/real-footage.md).

## Scenes

| Theme | Scene | Pattern |
|---|---|---|
| Catppuccin | `1-totoro`: Totoro moonrise | omarchy-intro@1 |

## License

MIT for the code in this repository. Wallpapers belong to their creators and are not included; see each scene's `notes.md`.
