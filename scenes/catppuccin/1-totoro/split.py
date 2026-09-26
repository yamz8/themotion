"""Totoro: a lit disc with a plane gradient, and ink shapes on it.

Layers: body, whisker, pupil, belly, sprite0..sprite10.
Meta: cx, cy, R of the disc, its gradient coef, the ink and background colours.
"""
import numpy as np

from split import circle_of, components, coverage, erode, fit_plane, grid, nearest_label, thin_parts


def split(image, layers):
    yy, xx = grid(image)
    background = image[40, 40]
    ink = background  # the shapes are the backdrop colour showing through

    light = image[..., 0] > 150
    cx, cy, R = circle_of(light)
    r = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
    coef, disc = fit_plane(image, erode(light, 6) & (r < R - 8))

    alpha = coverage(image, disc, ink) * (r < R - 1)
    labels, n, sizes, cents = components(alpha > 0.5)
    near = nearest_label(labels, 14)
    fringe = alpha > 0.01

    # Coordinates below are in 1080p units; the wallpaper is 4K.
    s = image.shape[1] / 1920
    body = int(np.argmax(sizes)) + 1

    def kind(i):
        y, x = cents[i - 1][0] / s, cents[i - 1][1] / s
        if i == body:
            return "body"
        if 636 < y < 656 and (880 < x < 910 or 1018 < x < 1048):
            return "pupil"
        if y > 755 and 820 < x < 1100:
            return "belly"
        return "sprite"

    kinds = {i: kind(i) for i in range(1, n + 1)}
    pick = lambda ids: fringe & np.isin(near, list(ids))

    # Whiskers are joined to the body at 4K: take its thin strokes beside the face.
    body_px = pick([body])
    beside_face = (yy >= 630 * s) & (yy <= 705 * s) & ((xx < 840 * s) | (xx > 1078 * s))
    whisker = body_px & beside_face & thin_parts(labels == body, 13, fringe)

    layers.save("body", alpha * (body_px & ~whisker), ink)
    layers.save("whisker", alpha * whisker, ink)
    for name in ("pupil", "belly"):
        layers.save(name, alpha * pick(i for i in kinds if kinds[i] == name), ink)

    # Each soot sprite is one big blob plus its fuzz; small bits join the nearest blob.
    sprites = [i for i in kinds if kinds[i] == "sprite"]
    blobs = [i for i in sprites if sizes[i - 1] >= 140 * s * s]
    owner = {}
    for i in sprites:
        y, x = cents[i - 1]
        owner[i] = i if i in blobs else min(blobs, key=lambda b: (cents[b - 1][0] - y) ** 2 + (cents[b - 1][1] - x) ** 2)
    order = sorted(blobs, key=lambda b: (cents[b - 1][1] < cx, cents[b - 1][0]))
    for k, b in enumerate(order):
        layers.save(f"sprite{k}", alpha * pick(i for i in sprites if owner[i] == b), ink)

    layers.meta.update(cx=cx, cy=cy, R=R, coef=coef, ink=[float(v) for v in ink], background=[float(v) for v in background])

