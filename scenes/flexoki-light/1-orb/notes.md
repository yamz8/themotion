# Flexoki orb

A single ink block blinks on the paper like a cursor, then the ball grows out of it dot by dot. Light swings in like a pendulum, clearing the dots it falls on, and comes to rest on the wallpaper's own shading by 4.4 s.

The wallpaper is one ink on paper, shaded by a 4×4 Bayer dither on 4 px cells. Every dot the scene draws is one of the wallpaper's ink cells, cut from the still at its exact place; the motion only chooses which of them show. So nothing ever needs to resolve at the end: once the light rests, every cell is showing and the frame is the wallpaper, with the WebP's faint ink fringe on the paper faded in over 4.4-4.6 s, well ahead of the pattern's handoff.

`split.py` records the grid and its ink cells and fits a lit sphere to the dither (a circle for the hard dark edge, tone = clamp(a + b · normal) ^ gamma). The cursor is the wallpaper's 2×2 ink block nearest the sphere's centre. During the swing a cell hides while the moving light makes it clearly lighter than it is at rest, with a random margin per cell so the light clears dots rather than areas; the light can only hide the wallpaper's dots, never add dots of its own. An earlier version re-dithered the sphere under the moving light and locked each cell onto the wallpaper's bit late in the motion, which made the dot pattern visibly change near the handoff.

## Credits

- Wallpaper: ships with Omarchy's Flexoki Light theme; its artist is not credited there. Flexoki is Steph Ango's colour scheme.
