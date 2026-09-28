"""Launch: five flat stripes on a flat dark brown, running straight down the
middle of the picture and bending outward into curves near the bottom.

Every stripe is one flat colour, and each row of the picture crosses each
stripe once, so a stripe is fully described by where it starts and ends on
every row. The scene draws the stripes row by row and moves those ends.

Layers: stripe0 .. stripe4, left to right.
Meta: background, stripes (per stripe: colour, straight [left, right] from the
vertical part, and per row the left and right edges plus the first and last
column the stripe touches, including its soft edge).
"""
import numpy as np

from split import components, nearest_label


def split(image, layers):
    h, w = image.shape[:2]
    background = np.median(image[::8, ::8].reshape(-1, 3), 0)
    far = np.linalg.norm(image - background, axis=-1)

    # The stripe colours: the most common colours away from the background.
    q = np.round(image[::4, ::4][far[::4, ::4] > 30]).astype(int)
    colors, counts = np.unique(q, axis=0, return_counts=True)
    inks = colors[np.argsort(-counts)[:5]].astype(float)

    # Label the solid cores, then hand the soft edges to the nearest core.
    solid = np.zeros((h, w), int)
    for k, ink in enumerate(inks):
        solid[np.linalg.norm(image - ink, axis=-1) < 6] = k + 1
    labels, n, sizes, cents = components(solid > 0)
    big = np.argsort(-sizes)[:5] + 1
    # Order the stripes left to right by their position along the top rows.
    order = sorted(big, key=lambda i: np.nonzero((labels[10] == i))[0].mean())
    core = np.zeros((h, w), int)
    for k, i in enumerate(order):
        core[labels == i] = k + 1
    near = nearest_label(core, 6)

    stripes = []
    for k in range(5):
        mask = near == k + 1
        ink = np.median(image[core == k + 1], 0)
        step = ink - background
        alpha = np.clip(((image - background) * step).sum(-1) / (step * step).sum(), 0, 1) * mask
        alpha[alpha < 0.004] = 0
        layers.save(f"stripe{k}", alpha, ink)

        # Per row: the stripe's edges as an interval of the same area and centre,
        # and the columns it touches at all.
        xs = np.arange(w)
        area = alpha.sum(1)
        centre = (alpha * xs).sum(1) / np.maximum(area, 1e-9)
        touched = alpha > 0
        first = np.argmax(touched, 1)
        last = w - 1 - np.argmax(touched[:, ::-1], 1)
        rows = [[round(float(c - a / 2), 2), round(float(c + a / 2), 2), int(f), int(l) + 1]
                for c, a, f, l in zip(centre, area, first, last)]
        if any(a <= 0 for a in area):
            raise ValueError(f"stripe {k} misses a row")

        # The straight stripe: its vertical part, well above where it bends.
        top = slice(0, h // 3)
        left = float(np.median(centre[top] - area[top] / 2))
        right = float(np.median(centre[top] + area[top] / 2))
        stripes.append({"color": [float(v) for v in ink], "straight": [left, right], "rows": rows})

    # Where the stripes start to bend: the first row the outermost one leaves its column.
    s0 = stripes[0]
    bend = next(y for y, r in enumerate(s0["rows"]) if r[0] < s0["straight"][0] - 1)
    layers.meta.update(background=[float(v) for v in background], stripes=stripes, bend=bend)
