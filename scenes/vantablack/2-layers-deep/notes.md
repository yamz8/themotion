# Vantablack layers deep

The depth opens up front to back. The grey front sheet slides in from the left, then each layer behind it slides out from under the one above, out of the dark and a little further right each time. Halfway through, the back sheet at the right fades up where it lies, with a floor in its colour under everything, and the last layers slide in over it.

| Time | Beat |
|---|---|
| 0.15 | The grey front sheet slides in from the left |
| 0.75-3.2 | The layers behind it slide out from under each other, top of the stack first, 0.085 s apart |
| 2.2 | The back sheet and the floor fade up at the right |
| 4.5 | Every frame is the wallpaper, pixel for pixel |
| 5.0 | The pattern blends into the exact wallpaper |

The wallpaper is a rendered papercut like `3-layers-stacked`, and `split.py` cuts it the same way (the shared `papercut` and `stack_order` helpers in `lib/split.py`): pieces between the sharp paper edges, stacked by which side of each edge is shadowed. This one is much darker and softer, though. Brightness runs 0 to 76, and the strips at the lower right stand 1-2 levels above each other, inside WebP's block noise, so no threshold finds them without also cutting along the shadows. The split keeps only the sharp edges, about 30 pieces, and some pieces are groups of strips: the faint strips at the right stay with the back sheet, and a few neighbours in the middle move as one.

Every sheet slides straight in from the left with no overshoot. Its left edge is the edge of the sheet above it, so moving past its place would open a black gap there. The pieces hold only what shows, so a sliding sheet leaves a gap on its right where nothing lies beneath; before the floor comes up those gaps are the dark between layers, and after it they show the back sheet's paper. The back sheet reaches the screen's right edge, so it fades up where it lies instead of sliding.

At 7680x4320 the renderer runs out of memory drawing full-size frames, so the scene sets `render_scale = 0.5`: frames are 3840x2160, still twice the video's size. The masks are saved at quarter size, the size they are cut at, and each sheet is cut from the still at draw time through one scratch canvas. The last frame matches the wallpaper to a mean of 0.01 levels before encoding; after encoding the end check reads 0.26 (limit 0.3), the two-step resize, where other scenes read about 0.04.

## Credits

- Wallpaper: ships with Omarchy's Vantablack theme; its creator is not credited there.
