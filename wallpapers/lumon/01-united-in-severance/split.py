"""Lumon: a wireframe globe with the wordmark, five rules and a tagline, in
light ink on a vertical gradient.

Layers: backdrop (the wallpaper without ink), ring, parallels, meridians,
letter0..4 (LUMON), rule0..4 (top to bottom), tag0..16 (UNITED IN SEVERANCE).
Meta: the globe's centre and semi-axes, the meridians' half-widths, curves
and the rows they break for, the wordmark band, the rules' rows and the ink colour.
"""
import numpy as np
from scipy import ndimage as nd

from split import components, grid, nearest_label, unmix


def split(image, layers):
    yy, xx = grid(image)
    H, W = image.shape[:2]
    core = image[..., 0] > 60

    # The backdrop only changes down the screen: take each row's median away
    # from the ink, and fill the rows the rules cover from their neighbours.
    rows = np.full((H, 3), np.nan)
    for y in range(H):
        free = ~nd.binary_dilation(core[y], iterations=6)
        if free.sum() > 100:
            rows[y] = np.median(image[y][free], 0)
    known = ~np.isnan(rows[:, 0])
    rows = np.stack([np.interp(np.arange(H), np.nonzero(known)[0], rows[known, k]) for k in range(3)], -1)
    touched = nd.binary_dilation(core, iterations=6)
    backdrop = np.where(touched[..., None], rows[:, None, :], image)
    layers.save("backdrop", np.ones((H, W)), backdrop, pad=0)

    ink = np.percentile(image[core], 90, axis=0)
    alpha, color = unmix(image, backdrop, ink)
    alpha *= touched

    labels, n, sizes, cents = components(core)
    near = nearest_label(labels, 6)
    boxes = nd.find_objects(labels)
    part = lambda ids: alpha * np.isin(near, list(ids))

    globe = int(np.argmax(sizes)) + 1
    gy, gx = boxes[globe - 1]
    cx, cy = (gx.start + gx.stop) / 2, (gy.start + gy.stop) / 2
    a, b = (gx.stop - gx.start) / 2, (gy.stop - gy.start) / 2

    # Split the globe's strokes: the outer ring, the two parallels (long runs
    # of ink across a row) and the meridians.
    own = near == globe
    r = np.hypot((xx + 0.5 - cx) / a, (yy + 0.5 - cy) / b)
    ring = own & (r > 1 - 16 / b)
    long_rows = nd.binary_opening(core & own, structure=np.ones((1, 200)))
    # Grow the bars only by their soft edges, so no stub of a crossing
    # meridian comes along with them.
    parallels = own & ~ring & nd.binary_dilation(long_rows, structure=np.ones((5, 7)))
    meridians = own & ~ring & ~parallels
    # A bar's soft edge rows still carry the feet of the meridians crossing
    # it; cap each row at the bar's own coverage and give the rest back.
    bar = alpha * parallels
    middle = np.abs(xx[0] + 0.5 - cx) < 60
    cap = np.array([np.median(row[middle]) for row in bar])
    bar = np.minimum(bar, cap[:, None])
    layers.save("ring", alpha * ring, color)
    layers.save("parallels", bar, color)
    layers.save("meridians", alpha * meridians + (alpha * parallels - bar), color)

    # Each meridian is a great circle seen side-on, close to an ellipse sharing
    # the globe's height. Measure their half-widths on the equator, and each
    # one's actual curve: its stroke's centre, row by row, on either side.
    mb = b - 5
    lean = np.abs(xx + 0.5 - cx) / np.sqrt(np.clip(1 - ((yy + 0.5 - cy) / mb) ** 2, 1e-6, 1))
    m = meridians & core & (np.abs(yy - cy) < mb * 0.9)
    split_at = (lean[m].min() + lean[m].max()) / 2
    halfwidths = [float(np.median(lean[m & (lean < split_at)])), float(np.median(lean[m & (lean >= split_at)]))]
    curves = []
    for inner in (True, False):
        stroke = meridians * alpha * ((lean < split_at) == inner)
        curve = {"y": [], "left": [], "right": []}
        for y in range(gy.start, gy.stop):
            sides = [stroke[y] * (xx[y] + 0.5 < cx), stroke[y] * (xx[y] + 0.5 > cx)]
            if min(w.sum() for w in sides) > 3:
                centres = [(w * (xx[y] + 0.5)).sum() / w.sum() for w in sides]
                curve["y"].append(y + 0.5)
                curve["left"].append(float(cx - centres[0]))
                curve["right"].append(float(centres[1] - cx))
        curves.append(curve)
    # The meridians break for the wordmark between these rows.
    bare, _ = nd.label(~meridians.any(1))
    rows_bare = np.nonzero(bare == bare[int(cy)])[0]
    gap = [int(rows_bare.min()), int(rows_bare.max()) + 1]
    par_rows = [float(yy[parallels & core & (yy < cy)].mean()), float(yy[parallels & core & (yy > cy)].mean())]

    # Everything else, left to right and top to bottom.
    others = sorted((i for i in range(1, n + 1) if i != globe), key=lambda i: (cents[i - 1][0] // 40, cents[i - 1][1]))
    letters = [i for i in others if gy.start < cents[i - 1][0] < gy.stop]
    rules = [i for i in others if boxes[i - 1][1].stop - boxes[i - 1][1].start > W * 0.9]
    tags = [i for i in others if i not in letters and i not in rules]
    for k, i in enumerate(letters):
        layers.save(f"letter{k}", part([i]), color)
    for k, i in enumerate(rules):
        layers.save(f"rule{k}", part([i]), color)
    for k, i in enumerate(tags):
        layers.save(f"tag{k}", part([i]), color)

    # The tagline's words are split by its widest gap.
    gaps = [boxes[j - 1][1].start - boxes[i - 1][1].stop for i, j in zip(tags, tags[1:])]
    first_word = int(np.argmax(gaps)) + 1

    band = [min(boxes[i - 1][0].start for i in letters), max(boxes[i - 1][0].stop for i in letters)]
    layers.meta.update(
        cx=cx, cy=cy, a=a, b=b, mb=mb, halfwidths=halfwidths, curves=curves, gap=gap, parallels=par_rows, band=band,
        rules=[float(cents[i - 1][0]) for i in rules], first_word=first_word,
        ink=[float(v) for v in ink],
    )
