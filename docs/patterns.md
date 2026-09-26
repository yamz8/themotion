# Patterns

A pattern is an output contract: what kind of video a scene becomes, and how to tell whether the result is right. Patterns live in `patterns/<name>@<version>.toml` and are data, not code, so the renderer and the checker read the same rules and cannot drift apart.

## Requirements and defaults

Each pattern separates two kinds of rule.

**`[requires]`** comes from how the target plays the video. Breaking one shows on screen, so no scene or flag can override it, and `themotion check` enforces every one.

**`[defaults]`** is taste: length, fade, frame rate, size. A scene overrides any of them in its `scene.toml`:

```toml
[defaults]
fade_in = 1.0   # a bright wallpaper needs a longer fade from black
```

and a single run overrides them with `--set key=value`.

**`[check]`** holds the thresholds the checker uses for the requirements.

## Versions

The requirements belong to the target, not to themotion. When Omarchy changes how it plays intros, the pattern gets a new version (`omarchy-intro@2`) and existing scenes keep checking against the version they were made for.

## omarchy-intro@1

Omarchy plays a theme's intro once per boot, in place of the wallpaper, then hands the desktop to the still wallpaper. The behaviour is documented in Omarchy's `docs/theming.md`.

| Requirement | Why |
|---|---|
| Starts black | The screen is black until the intro's first frame, so any other opening flashes |
| Ends on the exact wallpaper | The shell swaps to the still right after the last frame, so any difference jumps |
| BT.709, limited range, h264, yuv420p | Omarchy's player reads HD video as BT.709; anything else shifts colour at the handoff |
| 5 to 7 seconds | Long enough to register, short enough not to delay the desktop |

| Default | Value |
|---|---|
| `length` | 6.0 s |
| `fps` | 30 |
| `width` × `height` | 1920 × 1080, like the other intros in Omarchy |
| `fade_in` | 0.6 s |
| `settle` | 5.0 s: the scene's motion should be finished by here |
| `handoff` | 0.3 s blend from `settle` into the exact wallpaper |
| `crf` | 16 |

Installed intros go to `themes/<theme>/intros/<wallpaper>.mp4`, next to a `<wallpaper>.sha256` holding the wallpaper's hash, so Omarchy never plays an intro that ends on a different picture.

## Adding a pattern

Copy an existing pattern, give it a new name, and change its tables. A looping background, for example, would require that the last frame flows into the first, would play a scene's `idle` instead of its `enter`, and would need a matching check in `lib/check.py`.
