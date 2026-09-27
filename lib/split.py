"""Helpers for splitting a wallpaper into layers a scene can move.

A scene's split.py defines `split(image, layers)`: `image` is the wallpaper as
a float RGB array (H, W, 3) and `layers` is a LayerWriter. It saves each
movable shape as a tight, premultiplied-free RGBA crop and records any numbers
the scene needs (centres, radii, gradient fits) in layers.meta.

Layers stay derived from the wallpaper at build time and are never committed.
"""
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage as nd


class LayerWriter:
    def __init__(self, outdir, width, height):
        self.outdir = outdir
        self.meta = {"width": width, "height": height, "layers": []}
        os.makedirs(outdir, exist_ok=True)

    def save(self, name, alpha, color, pad=2, at=(0, 0)):
        """Save a shape whose coverage is `alpha` (H, W, 0..1) in `color`: one
        RGB value for a flat shape, or an (H, W, 3) array for per-pixel colour.
        `alpha` and `color` may be a crop of the wallpaper whose top-left
        corner is at `at` (x, y); the padding then stays within the crop."""
        ys, xs = np.nonzero(alpha > 0)
        if len(ys) == 0:
            raise ValueError(f"layer {name} is empty")
        h, w = alpha.shape
        y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + 1 + pad)
        x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + 1 + pad)
        rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        color = np.broadcast_to(np.asarray(color, float), (h, w, 3))
        rgba[..., :3] = np.round(np.clip(color[y0:y1, x0:x1], 0, 255)).astype(np.uint8)
        rgba[..., 3] = np.round(np.clip(alpha[y0:y1, x0:x1], 0, 1) * 255)
        Image.fromarray(rgba).save(os.path.join(self.outdir, f"{name}.png"), optimize=True)
        self.meta["layers"].append({"name": name, "x": int(x0 + at[0]), "y": int(y0 + at[1]),
                                    "w": int(x1 - x0), "h": int(y1 - y0)})

    def write(self):
        with open(os.path.join(self.outdir, "layers.json"), "w") as f:
            json.dump(self.meta, f, indent=1)


def grid(image):
    h, w = image.shape[:2]
    return np.mgrid[0:h, 0:w]


def fit_plane(image, mask):
    """Least-squares colour = a + b*x + c*y per channel over `mask`.

    Returns the coefficients [[a, b, c] x 3] and the fitted image.
    """
    yy, xx = grid(image)
    A = np.stack([np.ones(mask.sum()), xx[mask], yy[mask]], 1)
    coef = [np.linalg.lstsq(A, image[..., k][mask], rcond=None)[0] for k in range(3)]
    fitted = np.stack([c[0] + c[1] * xx + c[2] * yy for c in coef], -1)
    return [[float(v) for v in c] for c in coef], fitted


def circle_of(mask):
    """Centre and radius of the bounding circle of a round mask."""
    ys, xs = np.nonzero(mask)
    cx, cy = (xs.min() + xs.max() + 1) / 2, (ys.min() + ys.max() + 1) / 2
    return float(cx), float(cy), float((xs.max() - xs.min() + 1) / 2)


def coverage(image, backdrop, ink, channel=0):
    """How much of `ink` covers each pixel over `backdrop`, 0..1."""
    return np.clip((backdrop[..., channel] - image[..., channel]) / (backdrop[..., channel] - ink[channel] + 1e-9), 0, 1)


def components(mask):
    """Label connected shapes; returns labels, count, sizes and centroids (y, x)."""
    labels, n = nd.label(mask)
    idx = range(1, n + 1)
    sizes = nd.sum(np.ones_like(labels), labels, idx)
    cents = nd.center_of_mass(mask, labels, idx)
    return labels, n, sizes, cents


def nearest_label(labels, reach):
    """Each pixel's nearest labelled shape within `reach` px, else 0.

    Used to hand antialiased fringe pixels to the shape they belong to.
    """
    dist, (iy, ix) = nd.distance_transform_edt(labels == 0, return_indices=True)
    near = labels[iy, ix]
    near[dist >= reach] = 0
    return near


def thin_parts(mask, width, within=None):
    """Pixels (of `within`, default `mask`) away from the parts of `mask`
    thicker than about `width` px: thin strokes plus their soft edges."""
    thick = nd.binary_opening(mask, structure=np.ones((width, width)))
    return (mask if within is None else within) & ~nd.binary_dilation(thick, iterations=3)


def erode(mask, px):
    return nd.binary_erosion(mask, iterations=px)


def unmix(image, backdrop, ink):
    """Separate a shape whose colour varies (grain, gradients) from a known backdrop.

    `ink` is the shape's full-strength reference colour. Returns the coverage,
    0..1, and a per-pixel colour that, drawn at that coverage over `backdrop`,
    gives back the image.
    """
    lift = (image - backdrop) / (np.asarray(ink, float) - backdrop + 1e-9)
    alpha = np.clip(lift.max(-1), 0, 1)
    color = backdrop + (image - backdrop) / np.maximum(alpha, 1e-3)[..., None]
    return alpha, np.clip(color, 0, 255)


def papercut(image, scale, edge, small):
    """Pieces of a papercut picture, cut on its sharp paper edges.

    Paper edges are where the log of the brightness jumps, while soft shadows
    stay under `edge` (a Sobel gradient at 1/`scale` size, where WebP's blocks
    are gone). Pieces smaller than `small` px at that size are slivers of an
    edge and go to their nearest neighbour, so the pieces tile the picture.
    Returns the piece labels at 1/`scale` size, 0 to n-1; the pixels away from
    any edge, where brightness can be trusted; and the log brightness."""
    lum = np.log1p(nd.zoom(image.mean(-1), 1 / scale, order=1))
    grad = np.hypot(nd.sobel(lum, 0), nd.sobel(lum, 1))
    labels, n = nd.label(~nd.binary_dilation(grad > edge, iterations=2))
    sizes = nd.sum(np.ones_like(labels), labels, range(1, n + 1))
    keep = [i + 1 for i in range(n) if sizes[i] >= small]
    known = np.isin(labels, keep)
    _, (iy, ix) = nd.distance_transform_edt(~known, return_indices=True)
    lut = np.zeros(n + 1, np.int32)
    lut[keep] = np.arange(len(keep))
    known &= ~nd.binary_dilation(~known, iterations=1)
    return lut[labels[iy, ix]], known, lum


def stack_order(labels, known, lum, near=3, far=12):
    """Papercut pieces sorted deepest first, from which side of each edge is
    shadowed: in a band `near` to `far` px from the edge between two pieces,
    the piece on top is lit and the one beneath is in its shadow. Returns the
    order and the weighted comparisons, above[a, b] > 0 when a lies on b."""
    m = labels.max() + 1
    side = {}
    for a in range(m):
        mine = labels == a
        band = nd.binary_dilation(mine, iterations=far) & ~nd.binary_dilation(mine, iterations=near) & known
        for b in np.unique(labels[band]):
            if b != a:
                zone = band & (labels == b)
                side[(b, a)] = (lum[zone].mean(), zone.sum())  # b's side of its edge with a
    above = np.zeros((m, m))
    for (b, a), (v, count) in side.items():
        if (a, b) in side:
            above[a, b] = (side[(a, b)][0] - v) * min(count, side[(a, b)][1])
    # Repeatedly take the piece with the least evidence of lying on any piece
    # still left: a topological sort that breaks a cycle at its weakest link.
    left, order = set(range(m)), []
    while left:
        k = min(left, key=lambda a: (sum(max(above[a, b], 0) for b in left), a))
        order.append(k)
        left.remove(k)
    return order, above
