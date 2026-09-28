"""Layers deep: a papercut in near-black greys. A flat grey front sheet fills
the left; behind its curved edge paper strips run from the top down to the
bottom, deeper and deeper to the right, down to a dark back sheet at the
right. Each strip is lit along its rim and casts a soft shadow on the next.

The picture is split like 3-layers-stacked, on the jumps in log brightness,
but it is much darker and softer: brightness runs 0 to 76, and the strips at
the lower right stand only 1-2 levels above their neighbours, inside WebP's
block noise. No threshold finds those edges without also cutting along the
shadows, so the split keeps only the sharp edges and some pieces are groups
of strips: the faint strips at the right stay with the back sheet, and a few
neighbours in the middle move as one. About 30 pieces in all.

Each piece is saved as a mask only; the scene cuts its pixels from the still
at runtime, so every piece is the wallpaper's own pixels and the pieces tile
the picture exactly. The stack order comes from which side of each edge is
shadowed.

The pieces hold only what shows, so a sheet sliding in leaves a gap where
nothing lies beneath it. The floor fills those gaps: the back sheet's colour
carried under the whole picture and blurred, saved small since it is smooth.

Layers: sheet0, sheet1, ... (quarter-size masks, deepest first; the last is the front sheet);
floor (eighth size).
Meta: per sheet its name, centroid and area in wallpaper pixels; mask_scale and floor_scale,
the layers' scales.
"""
import numpy as np
from scipy import ndimage as nd

from split import papercut, stack_order

S = 4           # the edges are found at quarter size, where the WebP's blocks are gone
EDGE = 0.5      # log-brightness gradient of a paper edge (Sobel, quarter size); shadows stay under it
SMALL = 800     # pieces smaller than this (quarter size) are slivers of an edge
F = 8           # the floor's scale
BLUR = 24       # the floor's blur, at its scale


def split(image, layers):
    labels, known, lum = papercut(image, S, EDGE, SMALL)
    order, _ = stack_order(labels, known, lum)

    # The pieces are only known at quarter size, so the masks are saved at
    # quarter size (the scene scales them up without smoothing): a full-size
    # mask per piece would not fit in the renderer's memory at 7680x4320.
    sheets = []
    for rank, k in enumerate(order):
        mask = labels == k
        cy, cx = nd.center_of_mass(mask)
        name = f"sheet{rank}"
        layers.save(name, mask.astype(float), (255, 255, 255), pad=0)
        sheets.append(dict(name=name, centroid=[round(float(cx) * S, 1), round(float(cy) * S, 1)],
                           area=int(mask.sum()) * S * S))
    # The back sheet is the biggest after the front one, which is on top.
    back = max(order[:-1], key=lambda k: (labels == k).sum())
    small = nd.zoom(image, (1 / F, 1 / F, 1), order=1)
    mine = nd.zoom((labels == back).astype(float), S / F, order=1) > 0.99
    _, (iy, ix) = nd.distance_transform_edt(~mine, return_indices=True)
    floor = nd.gaussian_filter(small[iy, ix], (BLUR, BLUR, 0))
    layers.save("floor", np.ones(floor.shape[:2]), floor, pad=0)
    layers.meta.update(sheets=sheets, mask_scale=S, floor_scale=F)
