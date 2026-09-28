"""Geometric: a plexus of glowing cyan lines, dots and translucent triangles
on pure black, dense in the lower right and thinning out to a few loose
strands towards the upper left.

The triangles overlap and add up like light, so they can't be lifted out one
by one. Instead the picture is cut into shards along its own vertices: the
dots where lines meet are found, thinned out, and triangulated together with
points around the frame. The scene cuts each shard from the still, and since
the background is black the shards add up to the picture exactly.

No layers. Meta: points (the triangulation's vertices, x, y), shards (index
triples), nodes (the indices of points that are real dots, not frame points),
core (the densest part of the network, where the motion starts).
"""
import numpy as np
from scipy import ndimage as nd
from scipy.spatial import Delaunay


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def split(image, layers):
    h, w = image.shape[:2]
    lum = image.mean(-1)

    # The dots are about 14 px across and the lines about 7: an opening with
    # a small disk keeps the dots (and fills), a larger one drops the dots too.
    small = (slice(None, None, 2), slice(None, None, 2))
    dots = nd.grey_opening(lum[small], footprint=disk(3)) - nd.grey_opening(lum[small], footprint=disk(6))
    labels, n = nd.label(dots > 40)
    idx = range(1, n + 1)
    cents = np.array(nd.center_of_mass(dots, labels, idx)) * 2
    strength = np.array(nd.maximum(dots, labels, idx))

    # Strongest dots first, each at least `spacing` from those already kept,
    # so the dense core doesn't shatter into slivers.
    spacing = 150
    kept = []
    for i in np.argsort(-strength):
        y, x = cents[i]
        if all((x - kx) ** 2 + (y - ky) ** 2 >= spacing ** 2 for kx, ky in kept):
            kept.append((float(x), float(y)))

    # Points around the frame, so the shards cover all of it.
    frame = []
    for k in range(9):
        frame += [(w * k / 8, 0.0), (w * k / 8, float(h))]
    for k in range(1, 6):
        frame += [(0.0, h * k / 6), (float(w), h * k / 6)]
    points = np.array(kept + frame)
    tri = Delaunay(points)

    # The core: the peak of the network's brightness, heavily blurred.
    blur = nd.gaussian_filter(lum[::8, ::8], 40)
    cy, cx = np.unravel_index(np.argmax(blur), blur.shape)

    layers.meta.update(
        points=[[round(x, 1), round(y, 1)] for x, y in points],
        shards=tri.simplices.tolist(),
        nodes=list(range(len(kept))),
        core=[float(cx * 8), float(cy * 8)],
    )
