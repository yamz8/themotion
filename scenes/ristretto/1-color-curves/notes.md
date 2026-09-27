# Ristretto colour curves

The colour bands fan in one after another, outermost first. A front runs along each band's curve from its left end, and the band slides in behind it, overshoots and springs back. Last, the dark dome at the bottom rises into the middle of the fan, stretching tall as it overshoots and settling with a squash.

| Time | Beat |
|---|---|
| 0.3 | The outer brown band starts to sweep in; the rest follow every 0.2 s |
| 2.3 | The last band, the maroon ring around the dome, sweeps in |
| 2.55 | The dome rises from the bottom edge on a spring |
| 4.3 | Every piece is exactly in place; the frame is the wallpaper |
| 5.0 | The pattern blends into the exact still |

The bands are soft gradients with hard edges between them, so the wallpaper splits cleanly at every edge into 13 regions that tile the picture. `split.py` saves only their masks; the scene cuts each region's pixels from the still at runtime, so every moving piece is the wallpaper's own pixels and the preview stays under 300 KB. Pieces swing about the ellipse the inner domes curve around, so each band travels roughly along its own curve.

While bands slide in, thin dark seams can show between neighbours that are still moving; they close as the springs settle.

## Credits

- Wallpaper: ships with Omarchy's Ristretto theme; its artist is not credited there.
