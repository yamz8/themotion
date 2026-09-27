# Vantablack layers stacked

The papercut stack is laid down out of the dark, one sheet at a time and deepest first. Each paper strip drops onto the pile from above, a little large and held up and to the left, fades in and lands with a small spring, so the stack builds from the black sheet at the top right, down through the strips in the middle and out to the long strips at the top left and bottom. Last, the grey front sheet slides in from the left, overshoots once and eases back onto the stack.

| Time | Beat |
|---|---|
| 0.25 | The deepest strips at the top right drop in out of the black |
| 0.25-3.0 | The other strips follow deepest first, 0.065 s apart, each landing with a small spring |
| 2.95 | The grey front sheet slides in from the left edge, overshoots and eases back from the right |
| 4.2 | Every frame is the wallpaper, pixel for pixel |
| 5.0 | The pattern blends into the exact wallpaper |

The wallpaper is a rendered papercut: every strip ends in a sharp, lit edge and casts a soft shadow on the strip below. `split.py` finds the edges at half size (where the log of the brightness jumps), takes the pieces between them as strips, about 40 in all, and sorts them into a stack by which side of each edge is lit and which is in shadow. Each strip is saved as a mask only; the scene cuts its pixels from the still, so the preview carries little but the wallpaper, and the strips tile the picture exactly.

The front sheet's left edge is the screen's edge, so while it overshoots its own flat grey left column is stretched to cover the gap behind it. It overshoots once and settles from the right, so its curved edge never uncovers black.

## Credits

- Wallpaper: ships with Omarchy's Vantablack theme; its creator is not credited there.
