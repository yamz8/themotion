"""Dot map: small rounded squares on a regular grid over flat cream paper, in
Rose Pine Dawn colours at many strengths, densest along a diagonal band.

Every dot is its own shape, so all of them go into one layer and the scene
draws each dot from its own box of it.

Layers: dots (per-pixel colour: each dot's colour across its box).
Meta: coef (the paper's plane fit), box (the side of a dot's box), dots (per
dot: box left, box top, strength 0..1, colour as 0xRRGGBB), origin (the band's strength-weighted centre)
and axis (the band's direction, a unit vector).
"""
import numpy as np
from scipy import ndimage as nd

from split import fit_plane

PITCH = 36.055  # the grid's spacing, fitted over the whole wallpaper
BOX = 30        # a dot is about 12 px; its box also takes the soft edge


def split(image, layers):
    h, w = image.shape[:2]
    paper = np.median(image[::8, ::8].reshape(-1, 3), 0)
    far = np.linalg.norm(image - paper, axis=-1)
    coef, backdrop = fit_plane(image, nd.binary_erosion(far < 6, iterations=3))

    # The grid's phase, from the mean profile across each axis.
    def phase(profile):
        k = np.arange(len(profile))
        return np.angle((profile * np.exp(-2j * np.pi * k / PITCH)).sum()) / (2 * np.pi) * PITCH % PITCH

    x0, y0 = phase(far.mean(0)), phase(far.mean(1))
    cols, rows = int((w - x0) // PITCH) + 1, int((h - y0) // PITCH) + 1

    alpha = np.zeros((h, w))
    color = backdrop.copy()
    dots, half = [], BOX // 2
    for j in range(rows):
        for i in range(cols):
            # Boxes at the edges shift inside the picture; the dot stays within them.
            bx = min(max(int(round(x0 + i * PITCH)) - half, 0), w - BOX)
            by = min(max(int(round(y0 + j * PITCH)) - half, 0), h - BOX)
            box = np.s_[by:by + BOX, bx:bx + BOX]
            d = far[box]
            if d.max() < 5:
                continue
            # The dot's colour: the median of its core, the pixels near its strongest.
            core = image[box][d > 0.75 * d.max()]
            ink = np.median(core, 0)
            back = backdrop[box]
            step = ink - back
            a = np.clip(((image[box] - back) * step).sum(-1) / ((step * step).sum(-1) + 1e-9), 0, 1)
            a[a < 0.03] = 0
            alpha[box] = a
            color[box] = ink
            rgb = int(np.round(ink[0])) << 16 | int(np.round(ink[1])) << 8 | int(np.round(ink[2]))
            dots.append([bx, by, float(np.linalg.norm(ink - paper)), rgb])

    layers.save("dots", alpha, color)

    # The band's centre and the way it runs.
    strength = np.array([d[2] for d in dots])
    top = strength.max()
    for d in dots:
        d[2] = round(d[2] / top, 3)
    xy = np.array([[d[0] + half, d[1] + half] for d in dots], float)
    weight = strength ** 2
    mean = (xy * weight[:, None]).sum(0) / weight.sum()
    cov = np.cov((xy - mean).T, aweights=weight)
    axis = np.linalg.eigh(cov)[1][:, -1]
    if axis[0] < 0:
        axis = -axis

    layers.meta.update(
        coef=coef,
        box=BOX,
        dots=dots,
        origin=[float(v) for v in mean],
        axis=[float(v) for v in axis],
    )
