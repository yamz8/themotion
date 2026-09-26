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

    def save(self, name, alpha, color, pad=2):
        """Save a flat-colour shape whose coverage is `alpha` (H, W, 0..1)."""
        ys, xs = np.nonzero(alpha > 0)
        if len(ys) == 0:
            raise ValueError(f"layer {name} is empty")
        h, w = alpha.shape
        y0, y1 = max(0, ys.min() - pad), min(h, ys.max() + 1 + pad)
        x0, x1 = max(0, xs.min() - pad), min(w, xs.max() + 1 + pad)
        rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        rgba[..., :3] = np.round(color).astype(np.uint8)
        rgba[..., 3] = np.round(np.clip(alpha[y0:y1, x0:x1], 0, 1) * 255)
        Image.fromarray(rgba).save(os.path.join(self.outdir, f"{name}.png"), optimize=True)
        self.meta["layers"].append({"name": name, "x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)})

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
