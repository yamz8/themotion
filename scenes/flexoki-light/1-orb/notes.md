# Flexoki orb

A single ink pixel blinks on the paper like a cursor, then springs open into a dark dithered ball. Light tips in and swings like a pendulum, sweeping the shadow across the ball while its lit side dissolves into the paper, and the dither settles cell by cell onto the wallpaper's.

The wallpaper is one ink on paper, shaded by a 4×4 Bayer dither on 4 px cells, so nothing is moved as a picture. `split.py` records the grid and fits a lit sphere to the dither (a circle for the hard dark edge, tone = clamp(a + b · normal) ^ gamma); `scene.js` re-dithers that sphere on the same grid for any size and light. The fit gets most cells right. Over the last 1.5 s of motion, as the swing dies down, each cell locks onto the wallpaper's own bit at a random moment, so the dither resolves dot by dot and is exact by 4.8 s. (Nudging the fitted tone just past each threshold doesn't work here: every nudged cell flips only when the nudge weight reaches 1, so the whole correction lands on one frame.) The WebP's slight ink fringe then arrives in a short fade onto the still, ahead of the pattern's handoff.

## Credits

- Wallpaper: ships with Omarchy's Flexoki Light theme; its artist is not credited there. Flexoki is Steph Ango's colour scheme.
