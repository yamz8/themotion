# Rose Pine dot map

A seed dot pops at the heart of the diagonal band with a ring, then a front spreads out from it, faster along the band than across it, and every dot it passes spins into place on a spring. A ripple runs out through the grid like a drop in water, swelling and pushing the dots it passes, and the darkest few percent twinkle with a swell and a twist before the map settles.

The wallpaper is a 142 × 80 grid of small rounded squares at a 36.05 px pitch. Every dot is its own shape, so they share one layer and the scene draws each dot from its own 30 px box of it, about 11,000 per frame.

The cream paper is bright, so the fade from black runs 0.8 s to keep each frame's step under 12 levels. The settled frames are encoded at the pattern's `settled_q`, so the ending lands a mean 0.10 off the wallpaper, and the motion runs at CRF 20, which keeps the file under 4 MB. Before `settled_q`, the whole video needed CRF 11 (about 7 MB) to pass the end check.

## Credits

- Wallpaper: ships with Omarchy's Rose Pine theme; its artist is not credited there.
