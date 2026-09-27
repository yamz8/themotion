# White stationery

Each piece of paper slides in along the picture's diagonals, folded over on itself, and unfolds as it lands: the flap drops flat and bounces twice like paper. The bottom sheet comes first, then the left sheet, the folder and the two card stacks. The last stack lands with a tap that nudges its neighbour, and the folder's corner flicks up once before everything lies still.

| Time | Beat |
|---|---|
| 0.3 | The bottom sheet slides up from the lower left, its top corner folded back; it unfolds from 1.0 s |
| 0.6 | The left sheet slides in from the left, its tip folded; it unfolds from 1.3 s |
| 0.95 | The folder glides down along its spine with its lower strip folded over; it opens from 1.8 s |
| 1.85 | The card stack drops in from the upper right, folded on its diagonal; it opens from 2.3 s |
| 2.2 | The second stack slides in from the right and opens |
| 3.05 | It lands with a tap that shoves the first stack, which springs back |
| 3.55 | The folder's bottom corner flicks up and falls flat with a bounce |
| 4.3 | Everything is still: the frame is the wallpaper |

The wallpaper is a photo, so nothing is recoloured. `split.py` records each piece's outline and a mask that owns every pixel nearest that piece, out to a margin that carries its shadow; the scene cuts each piece from the still through its mask. The masks tile the picture with hard seams, so the landed pieces rebuild the still exactly. Under a piece that has not landed, a smooth cubic fit of the bare table fills in. While a piece is in the air it is drawn from its outline alone, with a soft drop shadow; as it lands, its margin and baked shadow fade in and the drop shadow fades out. Pieces that run off the picture are padded with their edge pixels stretched, so an overshoot never shows where the photo ends.

The fold is an orthographic hinge: the flap is squashed towards its fold line by the cosine of its angle and mirrored past upright, with a light grey shade on its back.

The paper is near white, so the fade from black runs 1.0 s to keep each frame's step under 12 levels.

## Credits

- Wallpaper: ships with Omarchy's White theme; its photographer is not credited there.
