"""The automatic split for `logo` wallpapers: the Omarchy wordmark in one ink
on one flat colour.

The wordmark is pixel art, so besides the ink and each letter as layers, the
split records its grid: every ink block as [x, y, w, h, letter], cut at the
wordmark's own pixel edges. Drawn from the still at those rectangles, the
blocks tile the wordmark exactly, so a motion can move them one by one and
still land on the wallpaper pixel for pixel.
"""
from collections import Counter

import numpy as np
from scipy import ndimage as nd


def two_colours(image):
    counts = Counter(map(tuple, image.reshape(-1, 3)[::5].round().astype(int).tolist()))
    (bg, _), (ink, _) = counts.most_common(2)
    return np.array(bg, float), np.array(ink, float)


def grid_lines(edges, pitch):
    """Pixel edges along one axis, clustered, with gaps filled in at the pitch."""
    lines = []
    for e in sorted(edges):
        if not lines or e - lines[-1][-1] > pitch / 3:
            lines.append([e])
        else:
            lines[-1].append(e)
    lines = [round(np.mean(g)) for g in lines]
    out = [lines[0]]
    for a, b in zip(lines, lines[1:]):
        n = max(1, round((b - a) / pitch))
        out += [round(a + (b - a) * k / n) for k in range(1, n + 1)]
    return out


def block_pitch(lengths):
    """The size of one pixel block: the shortest run of ink that is common,
    refined over every run as a whole number of blocks."""
    lengths = lengths[lengths >= 4]
    for p in np.unique(lengths):
        if (np.abs(lengths - p) <= 2).mean() > 0.01:
            break
    k = np.maximum(1, np.round(lengths / p))
    return float(np.median(lengths / k))


def runs(mask):
    d = np.diff(np.pad(mask.astype(np.int8), ((0, 0), (1, 1))), axis=1)
    return np.nonzero(d == 1), np.nonzero(d == -1)


def split(image, layers):
    bg, ink = two_colours(image)
    # How far each pixel is from the backdrop towards the ink: 1 on the ink,
    # between for antialiased edges.
    d = ink - bg
    alpha = np.clip(((image - bg) @ d) / (d @ d), 0, 1)
    mask = alpha > 0.5

    (sy, sx), (ey, ex) = runs(mask)
    (tsy, tsx), (tey, tex) = runs(mask.T)
    lengths = np.r_[ex - sx, tex - tsx]
    pitch = block_pitch(lengths)
    xs = grid_lines(np.r_[sx, ex], pitch)
    ys = grid_lines(np.r_[tsx, tex], pitch)

    # Letters: connected strokes, merged when they share most of their columns.
    labels, n = nd.label(mask, np.ones((3, 3)))
    boxes = nd.find_objects(labels)
    spans = sorted((b[1].start, b[1].stop, i + 1) for i, b in enumerate(boxes))
    letters, owner = [], {}
    for x0, x1, lab in spans:
        if letters and min(x1, letters[-1][1]) - max(x0, letters[-1][0]) > 0.5 * min(x1 - x0, letters[-1][1] - letters[-1][0]):
            letters[-1][1] = max(letters[-1][1], x1)
        else:
            letters.append([x0, x1])
        owner[lab] = len(letters) - 1
    letter_of = np.zeros(n + 1, int)
    for lab, k in owner.items():
        letter_of[lab] = k

    cells = []
    for y0, y1 in zip(ys, ys[1:]):
        for x0, x1 in zip(xs, xs[1:]):
            if mask[y0:y1, x0:x1].mean() > 0.5:
                lab = np.bincount(labels[y0:y1, x0:x1].ravel(), minlength=n + 1)[1:].argmax() + 1
                cells.append([x0, y0, x1 - x0, y1 - y0, int(letter_of[lab])])

    ys_, xs_ = np.nonzero(alpha > 0.01)
    layers.save("ink", alpha, ink)
    for k in range(len(letters)):
        own = np.isin(labels, [lab for lab, j in owner.items() if j == k])
        near = nd.binary_dilation(own, iterations=3) & (alpha > 0.01)
        layers.save(f"letter{k}", alpha * near, ink)
    layers.meta.update(
        bg=bg.tolist(), ink=ink.tolist(), pitch=pitch,
        box=[int(xs_.min()), int(ys_.min()), int(xs_.max() + 1), int(ys_.max() + 1)],
        letters=[[x0, x1] for x0, x1 in letters], cells=cells)
