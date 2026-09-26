# themotion

Motion for Omarchy themes, made from their wallpapers. Read `README.md` first, then `docs/patterns.md` and `docs/making-a-scene.md`.

## Layout

- `patterns/*.toml`: output contracts. `[requires]` comes from how the target plays the video and is never overridden; `[defaults]` is taste; `[check]` holds thresholds.
- `scenes/<theme>/<wallpaper-name>/`: `scene.toml`, `split.py`, `scene.js`, `notes.md`. The folder name matches the wallpaper file's stem.
- `lib/`: the CLI (`cli.py`), split helpers (`split.py`), checker (`check.py`), browser runtime (`runtime.js`, `ease.js`, `blocks/`), preview page (`player.html`) and renderer (`render.mjs`).
- `build/`: generated layers, previews, frames and videos. Never committed.

## Rules for scenes

- `enter(ctx, t, api)` draws the whole frame and depends on nothing but `t`. Use `api.rng(seed)` for randomness.
- Everything is back in its original place by the pattern's `settle` time; the pattern does the fade from black and the blend into the exact wallpaper.
- Draw in wallpaper pixels. Rendering happens at the wallpaper's full size, and the video keeps the wallpaper's proportions: never force 16:9, since OWE and the shell both crop to fill the screen.
- Reach for an existing block in `lib/blocks/` before writing new motion; move motion into a block when a second scene needs it.
- Never commit wallpapers or layers. Credit the wallpaper's creator in `notes.md` as far as it is known.

## Verifying

- `themotion make <scene> --omarchy <checkout>` must pass every check.
- Look at the motion, not only the checks: build the preview and scrub it, or render a contact sheet of key frames.
- Checks prove the file; the handoff is a moment on a real screen. Before an intro ships, watch it play at login on an Omarchy machine.
- The wallpaper is decoded with libwebp (Chromium, Pillow, Omarchy's shell). ffmpeg's own WebP decoder is 1-2 levels off, so never use it for a reference still.

## Style

- Two-space indentation. JavaScript without semicolons; Python per PEP 8 with 120-column lines.
- Markdown lines are not hard-wrapped.
- Keep patterns as data: a new rule is a key in a pattern plus a check in `lib/check.py`, not a special case in a scene.
