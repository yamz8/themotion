"""Orb: a sphere in one ink on paper, shaded by a 4x4 Bayer dither on 4 px
cells. Its dark side is a clean circular edge; the lit side dissolves into the
paper.

Nothing moves as a picture here: the scene re-dithers the orb on the same grid
under a moving light. So the split records the grid and its cells, and fits a
lit sphere to the dither so the scene can shade it with any light.

Layers: none.
Meta: paper and ink colours; the grid (cell size, origin, the cells' bounding
box and their ink bits, row by row); the Bayer phase; the sphere (centre and
radius, in cells) and its shading, tone = clamp(a + b . normal) ** gamma.
"""
import numpy as np
from scipy import ndimage as nd
from scipy.optimize import least_squares

CELL = 4
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def split(image, layers):
    h, w = image.shape[:2]
    lum = image.mean(-1)
    border = np.concatenate([image[:8].reshape(-1, 3), image[-8:].reshape(-1, 3)])
    paper = np.median(border, 0)
    ink = image[lum < 60].mean(0)
    dark = lum < (lum[lum < 60].mean() + paper.mean()) / 2

    # The grid's origin is where cells are most uniform.
    def spread(ox, oy):
        d = dark[oy:, ox:]
        d = d[:d.shape[0] // CELL * CELL, :d.shape[1] // CELL * CELL].reshape(d.shape[0] // CELL, CELL, -1, CELL)
        m = d.mean((1, 3))
        return (m * (1 - m)).sum()
    ox, oy = min(((x, y) for x in range(CELL) for y in range(CELL)), key=lambda o: spread(*o))
    rows, cols = (h - oy) // CELL, (w - ox) // CELL
    bits = dark[oy + CELL // 2::CELL, ox + CELL // 2::CELL][:rows, :cols]

    Y, X = np.mgrid[0:rows, 0:cols]

    # The dark side's edge is a circle; the lit side dissolves inside it. Fit
    # the circle to the sharp part of the edge only, where the tone climbs
    # from paper to dark within a few cells.
    tone = nd.uniform_filter(bits.astype(float), 4)
    edge = (tone > 0.25) & ~nd.binary_erosion(tone > 0.25) & (nd.maximum_filter(tone, 7) > 0.6)
    ey, ex = np.nonzero(edge)
    s = np.linalg.lstsq(np.c_[ex, ey, np.ones(len(ex))], ex ** 2.0 + ey ** 2.0, rcond=None)[0]
    cx, cy = s[0] / 2, s[1] / 2
    r = np.sqrt(s[2] + cx * cx + cy * cy)

    # Shading: tone = clamp(a + b . n) ** gamma over the sphere's normals.
    nx, ny = (X - cx) / r, (Y - cy) / r
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    inside = nx * nx + ny * ny < 1

    def shade(p):
        return np.clip(p[0] + p[1] * nx + p[2] * ny + p[3] * nz, 0, 1) ** p[4]
    fit = least_squares(lambda p: (shade(p) - tone)[inside], [0.5, -0.5, -0.5, 0, 1]).x

    # The Bayer phase that best reproduces the cells from the fitted shading.
    model = np.where(inside, shade(fit), 0)
    phase = min(((px, py) for px in range(4) for py in range(4)),
                key=lambda p: ((model > (BAYER[(Y + p[1]) % 4, (X + p[0]) % 4] + 0.5) / 16) != bits).sum())

    # The recorded cells cover every ink cell and the whole sphere, so the
    # scene can correct each cell the shading reaches.
    ys, xs = np.nonzero(bits | inside)
    y0, y1, x0, x1 = ys.min() - 1, ys.max() + 2, xs.min() - 1, xs.max() + 2

    layers.meta.update(
        paper=[float(v) for v in paper],
        ink=[float(v) for v in ink],
        cell=CELL, origin=[ox, oy], box=[int(x0), int(y0), int(x1), int(y1)],
        bits=["".join("1" if b else "0" for b in row) for row in bits[y0:y1, x0:x1]],
        bayer=BAYER.tolist(), phase=[int(v) for v in phase],
        sphere=[float(cx), float(cy), float(r)],
        shade=[float(v) for v in fit],
    )
