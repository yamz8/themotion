"""Synth scape: a blurred cyan sun in a sky that darkens to black at the top,
over wireframe mountains and a grid floor that meet the sky at a flat horizon
down the middle.

The sky is the same on both edges, row by row, so its gradient comes from the
edge columns; everything the sun adds on top of that (disc and glow) is the
sun layer, so it can rise. The terrain is every pixel from its wireframe's
top edge down.

Layers: sky (the edge gradient, rows constant, down to the horizon), sun (the
disc and glow over that gradient, filled in smoothly behind the mountains),
terrain (the outline of the mountains and floor; the scene fills it from the
still), wire (the terrain's lines alone, in one colour).
Meta: horizon (the floor's far edge in the valley), valley (the valley's
centre, where the left and right ranges part), sun (disc centre and radius),
line (the lines' colour).
"""
import numpy as np
from scipy import ndimage as nd

from split import circle_of, components, unmix


def split(image, layers):
    h, w = image.shape[:2]

    # The wireframe's lines are sharp; the sky, sun and glow are all soft.
    lum = image.mean(-1)
    sharp = np.abs(lum - nd.gaussian_filter(lum, 4)) > 6
    top = np.where(sharp.any(0), sharp.argmax(0), h)
    top = nd.minimum_filter1d(top, 9) - 3  # take the lines' soft upper edge along

    # The floor's far edge: the lowest the terrain starts, near the middle.
    mid = slice(w // 2 - w // 10, w // 2 + w // 10)
    horizon = int(top[mid].max())
    valley = mid.start + int(np.argmax(top[mid] == horizon) + np.sum(top[mid] == horizon) // 2)

    yy, xx = np.mgrid[0:h, 0:w]
    terrain = yy >= np.minimum(top, horizon)[None, :]
    # Only the terrain's outline: the scene cuts its pixels from the still,
    # which keeps the preview page small enough to share.
    layers.save("terrain", terrain.astype(float), (0, 0, 0))

    # The sky's gradient, from the edge columns, which the sun doesn't reach.
    sky = np.median(np.concatenate([image[:, :16], image[:, -16:]], 1), 1)
    above = yy < horizon
    layers.save("sky", above.astype(float), np.broadcast_to(sky[:, None], image.shape))

    # What the sun adds, measured wherever the sky shows and filled in behind
    # the mountains by normalised blurring, which keeps the glow smooth.
    add = np.clip(image - sky[:, None], 0, 255)
    seen = (yy < top[None, :] - 4) & above
    small = (slice(None, None, 8), slice(None, None, 8))
    s_seen = seen[small].astype(float)
    s_add = add[small] * s_seen[..., None]
    fill = s_add.copy()
    for sigma in (2, 4, 8, 16, 32):
        wgt = nd.gaussian_filter(s_seen, sigma)
        est = np.stack([nd.gaussian_filter(s_add[..., k], sigma) for k in range(3)], -1) / np.maximum(wgt, 1e-6)[..., None]
        hole = (s_seen == 0) & (fill.sum(-1) == 0) & (wgt > 1e-3)
        fill[hole] = est[hole]
    fill = np.stack([nd.zoom(fill[..., k], 8, order=1)[:h, :w] for k in range(3)], -1)
    add = np.where(seen[..., None], add, fill)

    # As a layer over the gradient, so the sun keeps its own colour wherever
    # it is and however dark the sky is behind it.
    ink = image[seen].max(0)
    alpha, color = unmix(sky[:, None] + add, np.broadcast_to(sky[:, None], image.shape), ink)
    layers.save("sun", alpha * above, color)

    # The wireframe's lines on their own, for the scan pulse: the fill is what
    # is left when the thin bright lines are opened away.
    fill = np.stack([nd.grey_opening(image[..., k], size=(7, 7)) for k in range(3)], -1)
    line = np.percentile(image[sharp & (yy > horizon)], 90, axis=0)
    wire, _ = unmix(image, fill, line)
    layers.save("wire", wire * terrain, line)

    # The disc: its red jumps from about 50 to 80 at the edge, and nothing
    # else in the sky gets that red.
    labels, n, sizes, cents = components(seen & (image[..., 0] > 70))
    layers.meta.update(
        horizon=horizon,
        valley=valley,
        sun=circle_of(labels == np.argmax(sizes) + 1),
        line=[float(v) for v in line],
    )
