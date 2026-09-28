"""Layers stacked: a papercut stack in near-black greys. A flat grey front sheet
fills the left, and behind its curved edge dozens of paper strips sweep from
the top left down and across to the right, each lit along its rim and casting
a soft shadow on the strip beneath, down to a black sheet at the top right.

Every strip ends in a sharp edge, while the shadows are soft, so the picture
splits cleanly: edges are where the log of the brightness jumps, and the
pieces between them are the strips. Each piece is saved as a mask only; the
scene cuts its pixels from the still at runtime, so the preview stays small
and every strip is the wallpaper's own pixels. The pieces tile the picture
exactly, so drawn back in place they are the wallpaper.

Which strip lies on which comes from the shadows: across an edge, the strip
beneath is darker right at the edge than in its middle, and the strip on top
is lit there. Sorting on those comparisons gives the stack, deepest first.

Layers: sheet0, sheet1, ... (masks, deepest first; the last is the front sheet).
Meta: per sheet its name, centroid and area.
"""
import numpy as np
from scipy import ndimage as nd

S = 2           # the edges are found at half size, where the WebP's blocks are gone
EDGE = 0.5      # log-brightness gradient of an edge (Sobel, half size); shadows stay under it
SMALL = 1500    # pieces smaller than this (half size) are slivers of an edge, not strips
NEAR, FAR = 3, 12  # the band either side of an edge (half size) where the rim and the shadow are measured


def split(image, layers):
    h, w = image.shape[:2]
    small = nd.zoom(image.mean(-1), 1 / S, order=1)
    lum = np.log1p(small)
    grad = np.hypot(nd.sobel(lum, 0), nd.sobel(lum, 1))

    labels, n = nd.label(~nd.binary_dilation(grad > EDGE, iterations=2))
    sizes = nd.sum(np.ones_like(labels), labels, range(1, n + 1))
    keep = [i + 1 for i in range(n) if sizes[i] >= SMALL]
    # Edge pixels and slivers go to the nearest strip.
    known = np.isin(labels, keep)
    _, (iy, ix) = nd.distance_transform_edt(~known, return_indices=True)
    labels = labels[iy, ix]
    known &= ~nd.binary_dilation(~known, iterations=1)
    index = {k: i for i, k in enumerate(keep)}
    labels = remap(labels, index)
    m = len(keep)

    order = stack_order(labels, known, small, m)

    # Back to full size: each full-size pixel takes its half-size pixel's strip.
    full = np.repeat(np.repeat(labels, S, 0), S, 1)[:h, :w]
    if full.shape != (h, w):
        full = np.pad(full, ((0, h - full.shape[0]), (0, w - full.shape[1])), mode="edge")

    sheets = []
    for rank, k in enumerate(order):
        mask = full == k
        cy, cx = nd.center_of_mass(mask)
        name = f"sheet{rank}"
        layers.save(name, mask.astype(float), (255, 255, 255), pad=0)
        sheets.append(dict(name=name, centroid=[round(float(cx), 1), round(float(cy), 1)], area=int(mask.sum())))
    layers.meta.update(sheets=sheets)


def remap(labels, index):
    lut = np.zeros(labels.max() + 1, np.int32)
    for k, i in index.items():
        lut[k] = i
    return lut[labels]


def stack_order(labels, known, lum, m):
    """Strips sorted deepest first, from which side of each edge is shadowed.

    For every pair of touching strips, compare their brightness in a band
    NEAR to FAR px from the edge between them (leaving out the edge itself):
    the strip on top is lit there, the one beneath is in its shadow."""
    near = {}
    for a in range(m):
        mine = labels == a
        band = nd.binary_dilation(mine, iterations=FAR) & ~nd.binary_dilation(mine, iterations=NEAR) & known
        for b in np.unique(labels[band]):
            if b != a:
                zone = band & (labels == b)
                near[(b, a)] = (lum[zone].mean(), zone.sum())  # b's side of its edge with a
    above = np.zeros((m, m))  # above[a, b] > 0: a lies on b, weighted by the edge's length
    for (b, a), (v, count) in near.items():
        if (a, b) in near:
            above[a, b] = (near[(a, b)][0] - v) * min(count, near[(a, b)][1])
    # Deepest first: repeatedly take the strip with the least evidence of
    # lying on any strip still left, which is a topological sort that breaks
    # any cycle at its weakest comparison.
    left, order = set(range(m)), []
    while left:
        k = min(left, key=lambda a: (sum(max(above[a, b], 0) for b in left), a))
        order.append(k)
        left.remove(k)
    return order
