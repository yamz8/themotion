# themotion

Motion for Omarchy themes, made from their wallpapers. Read `README.md` first, then `docs/patterns.md` and `docs/making-a-motion.md`.

## Layout

- `patterns/*.toml`: output contracts. `[requires]` comes from how the target plays the video and is never overridden; `[defaults]` is taste; `[check]` holds thresholds.
- `wallpapers/<theme>/<wallpaper-name>/`: the catalog, one folder for every Omarchy wallpaper, named after the file's stem. `wallpaper.toml` holds its `kind` and a one-line `about`; `split.py` (cuts it into layers) and `credit.md` are added when it is worked on. Shared by all its motions. `themotion catalog` lists them all.
- `motions/<theme>/<wallpaper-name>/<motion>/`: `scene.toml` (title, pattern, overrides), `scene.js` and `notes.md` (storyboard). A wallpaper can have many motions; the one installed becomes the theme's intro for that wallpaper.
- `motions/shared/<motion>/`: a motion for every wallpaper of one kind (`kind` in its `scene.toml`), built with `--wallpaper THEME/NAME` or `--all`. It draws only from what the kind's automatic split (`engine/kinds/<kind>.py`) records.
- `engine/`: the CLI (`cli.py`), split helpers (`split.py`), checker (`check.py`), browser runtime (`runtime.js`, `ease.js`, `blocks/`), preview page (`player.html`) and renderer (`render.mjs`).
- `build/`: generated layers, previews, frames and videos. Never committed.

## Rules for motions

- `enter(ctx, t, api)` draws the whole frame and depends on nothing but `t`. Use `api.rng(seed)` for randomness.
- Everything is back in its original place by the pattern's `settle` time; the pattern does the fade from black and the blend into the exact wallpaper.
- Draw in wallpaper pixels. Rendering happens at the wallpaper's full size (a motion may lower `render_scale` for a very large wallpaper, keeping frames larger than the video), and the video keeps the wallpaper's proportions: never force 16:9, since OWE and the shell both crop to fill the screen.
- Reach for an existing block in `engine/blocks/` before writing new motion; move motion into a block when a second motion needs it.
- Never commit wallpapers or layers. Credit the wallpaper's creator in its `credit.md` as far as it is known.

## Verifying

- `themotion make <motion> --omarchy <checkout>` must pass every check.
- Look at the motion, not only the checks: `themotion look <motion>` puts key frames on one sheet and says when the frame becomes the wallpaper; build the preview and scrub it for timing.
- Checks prove the file; the handoff is a moment on a real screen. Before an intro ships, watch it play at login on an Omarchy machine.
- The wallpaper is decoded with libwebp (Chromium, Pillow, Omarchy's shell). ffmpeg's own WebP decoder is 1-2 levels off, so never use it for a reference still.

## Style

- Two-space indentation. JavaScript without semicolons; Python per PEP 8 with 120-column lines.
- Markdown lines are not hard-wrapped.
- Keep patterns as data: a new rule is a key in a pattern plus a check in `engine/check.py`, not a special case in a motion.
