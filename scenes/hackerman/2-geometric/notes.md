# Hackerman geometric

One triangle of the network draws itself in its dense lower right: three dots pop in, lines join them, and it fills. The picture, cut into shards along its own vertices, then bursts out of it as it opens and fades: each shard flies out small and spinning, overshoots a little into place and flashes as it locks on, while the dots around it spark. The burst spreads outward from the core, so the loose strands in the upper left lock on last.

| Time | Beat |
|---|---|
| 0.2 | The seed triangle's dots pop in and its lines draw between them |
| 0.7 | It fills |
| 0.9 | It opens and the first shards burst out of it |
| 0.9-4.4 | Shards lock on outward from the core, each with a flash and a spark on its dots |
| 5.0 | Everything still; the pattern blends into the exact wallpaper |

The network's translucent triangles overlap and add up like light, so they can't be lifted out one by one. Instead `split.py` finds the dots where lines meet (an opening that keeps 14 px dots but drops 7 px lines, minus one that drops the dots too), thins them to one every 150 px, and triangulates them with points around the frame. The scene cuts each shard from the still and draws it with additive blending: on the pure black background, overlapping shards glow in flight and cut edges sum back to the exact picture. There are no layer images, so the preview page is only the wallpaper plus a few kilobytes of triangles.

## Credits

- Wallpaper: ships with Omarchy's Hackerman theme; its artist is not credited there.
