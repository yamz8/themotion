# Rose Pine funky shapes

The pastel blobs pop in one after another on a jelly spring, overshooting, squashing and leaning into place. Blobs cut off by the frame grow out of their edge. Then the doodles draw on: the thin curves run left to right, the rings sweep round from the inside out, the wavy strokes slide in from the right and the brown dashes flick on one by one. The white blob squashes down, springs up and flings its white dashes out to where they belong.

| Time | Beat |
|---|---|
| 0.0-0.9 | Fade in from black onto the pale pink paper |
| 0.3-1.3 | Pink, teal, lavender, pink, teal and white blobs pop in turn, each on a 1.5 s spring |
| 1.9-3.3 | Thin curves draw left to right |
| 2.0-3.6 | Both ring sets sweep round, inner ring first |
| 2.4-3.65 | Wavy strokes slide in from the right, top to bottom |
| 2.5-3.6 | Brown dashes flick on outward from their cluster's middle |
| 2.65-3.85 | White blob squashes, springs up and flings the white dashes, nearest first |
| 3.7-4.1 | The last level or two of antialiasing fades in; from 4.1 the frame is the wallpaper |
| 5.0 | The pattern's blend to the exact still (already identical) |

## How it is split

The blobs are flat colours laid over each other at partial opacity: teal over pink, and teal and pink over lavender. Their opacity is fitted from the overlap colours (about 0.50 for teal and 0.53 for pink), so each blob is one flat colour and they rebuild their overlaps when drawn in order, including while they move. The doodles are drawn in the blobs' own translucent colours, so each blob's outline is read from the paper and pink pixels it can see and carried across the strokes by a local vote. The doodles are whatever the blobs leave unexplained, cut from the still: every ring, dash and wavy stroke is its own layer. A faint `polish` layer holds what is left (antialiasing and rounding, a level or two), so the layers drawn in place rebuild the wallpaper to within one level.

The pale paper is bright, so the fade from black runs 0.9 s to keep each frame's step under 12 levels.

## Credits

- Wallpaper: ships with Omarchy's Rose Pine theme; its artist is not credited there.
