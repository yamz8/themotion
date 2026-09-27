"""Colour curves: overlapping bands in coffee colours, arcing from the bottom
left over a dark dome at the bottom middle, on a dark ground.

The bands are soft gradients with hard, antialiased edges between them, so
the picture splits cleanly into flat-edged regions: every place where the
colour jumps is an edge, and every piece between edges is a region. Each
region is saved as a mask only; the scene cuts its pixels from the still at
runtime, so the preview stays small and every region is the wallpaper's own
pixels. The regions tile the picture exactly, so drawn back in place they are
the wallpaper.

Layers: ground (the dark top left, which stays still) and band0, band1, ...
(masks, outermost first).
Meta: pivot and aspect (the ellipse the inner domes curve around), the
ground's colour, and per band its name, median colour, centroid, nesting radius and span (the
angles it covers around the pivot).
"""
import numpy as np
from scipy import ndimage as nd

EDGE = 25       # gradient strength of an edge, after a 2 px blur; the soft gradients inside bands stay under 10
SMALL = 2000    # pieces smaller than this are slivers of an edge, not regions
# The inner domes are ellipses around a centre just below the bottom edge,
# about 1.5 times wider than tall (fitted to the edges between them).
PIVOT = (1420.0, 1720.0)
ASPECT = 1.5
# The outer bands open out toward the top right, so they nest around a
# flatter ellipse further out; its median radius orders the bands outermost first.
NEST = (2000.0, 2200.0)
NEST_ASPECT = 1.2


def split(image, layers):
    h, w = image.shape[:2]
    blur = nd.gaussian_filter(image, (2, 2, 0))
    grad = sum(np.hypot(nd.sobel(blur[..., k], 0), nd.sobel(blur[..., k], 1)) for k in range(3))

    labels, n = nd.label(grad < EDGE)
    sizes = nd.sum(np.ones_like(labels), labels, range(1, n + 1))
    keep = [i + 1 for i in range(n) if sizes[i] >= SMALL]
    # Edge pixels and slivers go to the nearest region.
    known = np.isin(labels, keep)
    _, (iy, ix) = nd.distance_transform_edt(~known, return_indices=True)
    labels = labels[iy, ix]

    yy, xx = np.mgrid[0:h, 0:w]
    radius = np.hypot(xx - NEST[0], (yy - NEST[1]) * NEST_ASPECT)
    # Angle around the pivot's ellipse, clockwise from its left end: 0 at the
    # left, pi/2 straight up, pi at the right.
    angle = np.arctan2(-(yy - PIVOT[1]) * ASPECT, -(xx - PIVOT[0]))

    ground = labels[0, 0]
    layers.save("ground", (labels == ground).astype(float), (255, 255, 255))

    bands = []
    for k in keep:
        if k == ground:
            continue
        m = labels == k
        cy, cx = nd.center_of_mass(m)
        bands.append(dict(mask=m, color=[int(v) for v in np.median(image[m], 0)],
                          centroid=[round(float(cx), 1), round(float(cy), 1)],
                          radius=round(float(np.median(radius[m])), 1),
                          span=[round(float(v), 4) for v in np.percentile(angle[m], [0.2, 99.8])]))
    bands.sort(key=lambda b: -b["radius"])

    meta = []
    for i, b in enumerate(bands):
        name = f"band{i}"
        layers.save(name, b.pop("mask").astype(float), (255, 255, 255))
        meta.append(dict(name=name, **b))

    layers.meta.update(pivot=list(PIVOT), aspect=ASPECT, ground_color=[int(v) for v in np.median(image[labels == ground], 0)],
                       bands=meta)
