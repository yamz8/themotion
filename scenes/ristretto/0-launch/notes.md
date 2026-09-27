# Ristretto launch

The five stripes lift off from the bottom edge like a rocket's trail. From 0.3 s the pad rumbles and each stripe climbs, the centre one first and each outer pair 0.12 s behind, accelerating as it goes, with a pointed flame tip, a small spark and a wiggle in its trail. By 2.1 s all five run straight from top to bottom and the wiggle has calmed. From 2.25 s they pinch in, then spring outward into their curves, the outer stripes a beat ahead and the tails near the bottom whipping out last, overshooting past the screen's edges and ringing back. From 4.4 s the frame is the wallpaper exactly; the pattern holds it from there.

| Time | Beat |
|---|---|
| 0.3 | Liftoff: the pad rumbles, the centre stripe starts to climb |
| 0.3-2.1 | The stripes shoot up, centre first, sparks at their tips, trails wiggling |
| 2.1 | Five straight trails, top to bottom |
| 2.25 | They pinch in, then spring out into their curves and overshoot |
| 4.4 | The frame is the exact wallpaper |

Every stripe is one flat colour and each row of the picture crosses each stripe once, so `split.py` records every stripe's left and right edge per row. The scene draws each stripe from its own layer in 2-row strips, stretching each strip from the stripe's straight column (its vertical part at the top) to its real edges on that row; at the end of the bend every strip is drawn exactly where it came from, and from 4.4 s the whole layers are.

The wallpaper's bottom row is partly transparent in the WebP; the checks read it as plain RGB, as Omarchy's shell shows it.

## Credits

- Wallpaper: ships with Omarchy's Ristretto theme; its artist is not credited there.
