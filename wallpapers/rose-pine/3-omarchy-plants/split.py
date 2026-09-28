"""Omarchy plants: a cream sky with a soft diagonal gradient over a flat
ground whose top edge bows up gently, a sun, the pixel-art OMARCHY word in
seven colours, and two clusters of overlapping flat plants with small sprouts
on the ground around them.

The plants overlap and are partly blurred, so each cluster stays one layer and
the scene grows it column by column. Everything moving is separated from a
fitted sky and ground, which also fill in the backdrop behind them.

Layers: backdrop (the wallpaper without anything that moves), sun, letter0..6
(left to right), plantsL and plantsR (the clusters), sprout0..n.
Meta: sun (cx, cy, r), edge (the ground's first row, sampled every edge_step
px and at the last column), base (the ground line each cluster grows from), letters (each letter's bottom).
"""
import numpy as np
from scipy import ndimage as nd

from split import components, nearest_label

GROUND_X = 11    # a thin strip of sky runs down the left edge, beside the ground
SOFT = 24         # a change from the backdrop this large is full coverage
SKY_ANGLE = np.radians(47)  # the sky's gradient runs in steps across this direction
GROUND_ROWS = slice(3100, None)  # plain ground in every column
EDGE_SOFT = 4     # rows above the ground's edge that its soft blend reaches
EDGE_STEP = 32    # the ground edge goes to the scene sampled this often


def edge_of(image, clean, sky, ground):
    """The first ground row of every column.

    It is read wherever the plants leave it in view; under them, a quartic
    through those readings lands within a pixel or two."""
    rows = slice(2400, 2900)
    lum = image[rows].mean(-1)
    mid = (sky.mean() + ground.mean()) / 2
    xs, ys = [], []
    for x in range(int(GROUND_X) + 8, image.shape[1]):
        k = np.argmax(lum[:, x] < mid)
        if k > 3 and clean[rows.start + k - 3:rows.start + k + 3, x].all():
            xs.append(x)
            ys.append(rows.start + k)
    xs, ys = np.array(xs), np.array(ys)
    top = np.round(np.polyval(np.polyfit(xs / 1000, ys, 4), np.arange(image.shape[1]) / 1000)).astype(int)
    top[xs] = ys
    return top


def profile(image, fit, angle, step=4):
    """The sky's colour along direction `angle`: a median per `step` px band.

    Returns each pixel's band index and the per-band colours; the gradient is
    stepped along the diagonal, which a smooth fit would blur."""
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx * np.cos(angle) + yy * np.sin(angle)
    band = ((u - u.min()) // step).astype(int)
    colors = np.zeros((band.max() + 1, 3))
    have = np.zeros(band.max() + 1, bool)
    b = band[fit]
    order = np.argsort(b, kind="stable")
    b, px = b[order], image[fit][order]
    starts = np.r_[0, np.nonzero(np.diff(b))[0] + 1]
    for s, e in zip(starts, np.r_[starts[1:], len(b)]):
        colors[b[s]] = np.median(px[s:e], 0)
        have[b[s]] = True
    idx = np.arange(len(colors))
    for k in range(3):
        colors[:, k] = np.interp(idx, idx[have], colors[have, k])
    return band, colors


def model(image, clean, top):
    """The sky as a profile across its diagonal bands, and the ground as a
    profile by depth below its edge, which takes in the edge's soft rows."""
    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    fit = clean & (yy < top[None] - 12) & (xx > GROUND_X + 4)
    band, colors = profile(image, fit, SKY_ANGLE)
    back = colors[band]

    depth = np.arange(-EDGE_SOFT, h - top.min())
    cols = np.arange(int(GROUND_X) + 4, w)
    rows = np.clip(top[cols][None] + depth[:, None], 0, h - 1)
    px = np.where(clean[rows, cols][..., None], image[rows, cols], np.nan)
    ground = np.nanmedian(px, 1)
    for k in range(3):
        have = ~np.isnan(ground[:, k])
        ground[:, k] = np.interp(depth, depth[have], ground[have, k])
    d = yy - top[None] + EDGE_SOFT
    below = (d >= 0) & (xx > GROUND_X)
    back[below] = ground[d[below]]
    return back


def split(image, layers):
    h, w = image.shape[:2]
    sky_ink = np.median(image[:2400:8, ::8].reshape(-1, 3), 0)
    ground = np.median(image[GROUND_ROWS][::4, ::4].reshape(-1, 3), 0)

    # Anything far from both backdrop colours moves, with a margin for shadows and blur.
    near = np.minimum(np.linalg.norm(image - sky_ink, axis=-1), np.linalg.norm(image - ground, axis=-1))
    busy = nd.binary_dilation(near > 10, iterations=24)
    top = edge_of(image, ~busy, sky_ink, ground)
    back = model(image, ~busy, top)
    # The model misses by a few levels here and there; carry what it misses
    # in from the surroundings, so the backdrop has no seam around the plants.
    miss = np.where(busy[..., None], 0, image - back)
    weight = nd.gaussian_filter((~busy).astype(float), 48)
    back += np.where(busy[..., None], nd.gaussian_filter(miss, (48, 48, 0)) / np.maximum(weight, 1e-3)[..., None], miss)
    diff = image - back
    far = np.linalg.norm(diff, axis=-1)

    # Coverage and colour that rebuild the image exactly over the backdrop.
    alpha = np.where(busy & (far > 0.75), np.clip(far / SOFT, 1 / 255, 1), 0)
    color = np.clip(back + diff / np.maximum(alpha, 1e-3)[..., None], 0, 255)
    layers.save("backdrop", np.ones((h, w)), np.where(busy[..., None], back, image))

    labels, n, sizes, cents = components(busy)
    groups = {"plantsL": [], "plantsR": [], "sun": [], "word": [], "sprouts": []}
    for i in range(1, n + 1):
        cy, cx = cents[i - 1]
        if cy < top[int(cx)] - 800:
            groups["sun" if cx < w / 4 else "word"].append(i)
        elif sizes[i - 1] > 400_000:
            groups["plantsL" if cx < w / 2 else "plantsR"].append(i)
        else:
            groups["sprouts"].append(i)
    part = lambda ids: alpha * np.isin(labels, ids)

    for name in ("plantsL", "plantsR"):
        layers.save(name, part(groups[name]), color)

    sun = part(groups["sun"])
    ys, xs = np.nonzero(sun > 0.5)
    layers.save("sun", sun, color)

    # The letters touch, so they part by colour. The seven inks are the most
    # common core colours, each far from the ones before; every core pixel
    # takes the nearest ink, and soft edges go to the nearest core.
    word = np.isin(labels, groups["word"])
    core = word & (far > 60)
    px = image[core]
    q = (px // 8).astype(int)
    keys, inverse, counts = np.unique(q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2], return_inverse=True, return_counts=True)
    inks = []
    for k in np.argsort(-counts):
        ink = px[inverse.ravel() == k].mean(0)
        if all(np.linalg.norm(ink - other) > 40 for other in inks):
            inks.append(ink)
        if len(inks) == 7:
            break
    ink_of = np.zeros((h, w), int)
    ink_of[core] = np.argmin(np.linalg.norm(px[:, None] - np.array(inks)[None], axis=-1), 1) + 1
    for k in range(1, 8):
        # Stray pixels that took this ink belong to another letter; each letter is one shape.
        shapes, count = nd.label(ink_of == k)
        biggest = np.argmax(np.bincount(shapes.ravel())[1:]) + 1
        ink_of[(shapes > 0) & (shapes != biggest)] = 0
    owner = nearest_label(ink_of, 1000)
    order = sorted(range(1, 8), key=lambda k: np.nonzero(owner == k)[1].mean())
    bottoms = []
    for j, k in enumerate(order):
        mine = word & (owner == k)
        layers.save(f"letter{j}", alpha * mine, color)
        bottoms.append(int(np.nonzero(mine & (far > 30))[0].max()) + 1)

    for j, i in enumerate(sorted(groups["sprouts"], key=lambda i: cents[i - 1][1])):
        layers.save(f"sprout{j}", part([i]), color)

    base = {}
    for name in ("plantsL", "plantsR"):
        base[name] = int(np.nonzero(np.isin(labels, groups[name]) & (far > 30))[0].max()) + 1

    layers.meta.update(
        sun=[float((xs.min() + xs.max() + 1) / 2), float((ys.min() + ys.max() + 1) / 2), float((xs.max() - xs.min() + 1) / 2)],
        edge=[int(v) for v in top[::EDGE_STEP]] + [int(top[-1])],
        edge_step=EDGE_STEP,
        base=base,
        letters=bottoms,
    )
