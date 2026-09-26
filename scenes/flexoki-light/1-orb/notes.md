# Flexoki orb

A single ink pixel blinks on the paper like a cursor, then springs open into a dark dithered ball. Light tips in and swings like a pendulum, sweeping the shadow across the ball while its lit side dissolves into the paper, and the dither settles cell by cell onto the wallpaper's.

The wallpaper is one ink on paper, shaded by a 4×4 Bayer dither on 4 px cells, so nothing is moved as a picture. `split.py` records the grid and fits a lit sphere to the dither (a circle for the hard dark edge, tone = clamp(a + b · normal) ^ gamma); `scene.js` re-dithers that sphere on the same grid for any size and light. The fit gets most cells right; per-cell nudges, faded in as the light comes to rest, make the final light dither to exactly the wallpaper's cells. The WebP's slight ink fringe then arrives in a half-second fade onto the still, ahead of the pattern's handoff.

## Credits

- Wallpaper: ships with Omarchy's Flexoki Light theme; its artist is not credited there. Flexoki is Steph Ango's colour scheme.
