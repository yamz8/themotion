# themotion

Motion for [Omarchy](https://omarchy.org) themes, made from their wallpapers. Theme + motion.

A theme's wallpaper is split into layers once, and any number of motions move those layers in code: a moon springs open, a character rises into it, stars fall in. Every frame is a function of time, so the live preview, the final render and any later re-render always agree. A pattern decides what kind of video comes out and checks it: today that is Omarchy's boot intro, which fades in from black and lands on the exact wallpaper.

```
themotion make motions/catppuccin/1-totoro/moonrise --omarchy ~/omarchy
```

```
split 15 layers into build/catppuccin/1-totoro/layers
rendered 180 frames
video: build/catppuccin/1-totoro/moonrise/intros/1-totoro.mp4
pass  length       6.00 s (allowed 5.0-7.0 s)
pass  codec        h264 yuv420p
pass  color        colour matrix bt709 (Omarchy reads HD as BT.709)
pass  start        first frame luma 0.0 (max 12)
pass  fade         largest step 3.0 per frame (max 12)
pass  end          last frame vs wallpaper: mean 0.04, max 11 (max 0.3 / 24)
```

## Requirements

- Linux with `ffmpeg`, `node` 20+, [`uv`](https://docs.astral.sh/uv/), and Chromium or Chrome (Omarchy ships all but uv)
- Omarchy, for the wallpapers: `$OMARCHY_PATH` (Omarchy sets it), then `/usr/share/omarchy`; pass `--omarchy PATH` to use a checkout instead

Python and Node dependencies install themselves on first run.

## Commands

| Command | What it does |
|---|---|
| `themotion catalog [--json]` | Lists every Omarchy wallpaper with its kind and how far it has got |
| `themotion split <wallpaper or motion>` | Splits the wallpaper into layers under `build/` |
| `themotion preview <motion> [--open]` | Builds a self-contained preview page with play, scrub, and a wallpaper comparison |
| `themotion render <motion>` | Draws every frame at the wallpaper's full size (or `render_scale` of it) in headless Chromium |
| `themotion finish <motion> [--install]` | Encodes the video; `--install` copies it into the theme with its wallpaper hash |
| `themotion check <video> <wallpaper>` | Checks a video against its pattern, whoever made it |
| `themotion fit <video> <wallpaper>` | Re-finishes a footage intro's ending onto the exact wallpaper, leaving the rest untouched |
| `themotion make <motion> [--install]` | All of the above in order |

`--set key=value` overrides a pattern default for one run, for example `--set length=6.5` or `--set fade_in=1.0`.

## How it fits together

- **Patterns** (`patterns/*.toml`) are output contracts. `[requires]` lists what the target needs, which nothing may override; `[defaults]` are taste, which motions override. `themotion check` enforces the requirements. See [docs/patterns.md](docs/patterns.md).
- **Wallpapers** (`wallpapers/<theme>/<wallpaper>/`) are the catalog: every Omarchy wallpaper has a folder, named after its file. `wallpaper.toml` says what kind of picture it is (`logo`, `graphic`, `pattern`, `scene` or `dense`) and what it shows; once someone works on it, `split.py` cuts it into parts and `credit.md` credits its creator. A wallpaper is split once and shared by all its motions.
- **Motions** (`motions/<theme>/<wallpaper>/<motion>/`) move those parts: `scene.toml` picks the pattern, `scene.js` draws an `enter` (how the picture builds up) and optionally an `idle` (gentle motion on the settled picture, for future looping patterns), and `notes.md` holds the storyboard. See [docs/making-a-motion.md](docs/making-a-motion.md).
- **The engine** (`engine/`) is the CLI, the split helpers, the browser runtime, the preview page, the renderer and the checker.
- **Blocks** (`engine/blocks/`) are reusable motion: a starfield, glows and halos, a shockwave, and a pop-in with overshoot and bob.
- **Layers are never committed.** They are derived from the wallpaper at build time, so this repository contains code, not artwork.

Paintings and photos don't split into clean layers; for those, see [docs/real-footage.md](docs/real-footage.md).

## Motions

| Theme | Wallpaper | Motion | Pattern |
|---|---|---|---|
| Catppuccin | `1-totoro` | `moonrise`: Totoro moonrise | omarchy-intro@1 |
| Catppuccin | `2-waves` | `swell`: Waves swell from a line | omarchy-intro@1 |
| Catppuccin | `3-blue-eye` | `eye-opens`: Blue eye opens | omarchy-intro@1 |
| Flexoki Light | `1-orb` | `swinging-light`: Orb lit by a swinging light | omarchy-intro@1 |
| Hackerman | `1-synth-scape` | `sunrise`: The terrain unfolds and the sun rises | omarchy-intro@1 |
| Hackerman | `2-geometric` | `shard-burst`: The network bursts out of its core and locks into place | omarchy-intro@1 |
| Lumon | `01-united-in-severance` | `globe-trace`: United in severance | omarchy-intro@1 |
| Lumon | `02-opinions-equally` | `terminal-boot`: Enjoy each opinion equally | omarchy-intro@1 |
| Ristretto | `0-launch` | `liftoff`: The stripes lift off and spring into their curves | omarchy-intro@1 |
| Ristretto | `1-color-curves` | `fan-in`: The colour bands fan in and the dome rises | omarchy-intro@1 |
| Rose Pine | `1-funky-shapes` | `jelly-pop`: The blobs pop in and the doodles draw on | omarchy-intro@1 |
| Rose Pine | `2-dot-map` | `spin-in`: The dot map spins in from its centre | omarchy-intro@1 |
| Rose Pine | `3-omarchy-plants` | `spring-up`: Plants spring up, the letters drop in | omarchy-intro@1 |
| Vantablack | `2-layers-deep` | `depth-opens`: The depth opens up front to back | omarchy-intro@1 |
| Vantablack | `3-layers-stacked` | `sheet-by-sheet`: The papercut stack is laid down sheet by sheet | omarchy-intro@1 |
| White | `3-white` | `unfold`: The papers slide in and unfold | omarchy-intro@1 |

## License

MIT for the code in this repository. Wallpapers belong to their creators and are not included; see each wallpaper's `credit.md`.
