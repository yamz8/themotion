"""Waves: a ribbon of thin lines on a flat background, coloured by a
left-to-right gradient from pink to blue.

The lines cross each other everywhere, so the ribbon stays one layer and the
scene moves it in vertical strips.

Layers: ribbon.
Meta: background, axis (the ribbon's mean height), stops (the line colour
across the width), and centre (the ribbon's height per column, every 16 px).
"""
import numpy as np
from scipy import ndimage as nd


def split(image, layers):
    h, w = image.shape[:2]
    background = image[20, 20]

    # The line colour depends on x only: per column, take the pixel furthest
    # from the background, which sits in the core of some line.
    far = np.linalg.norm(image - background, axis=-1)
    core = image[np.argmax(far, axis=0), np.arange(w)]
    line = nd.median_filter(core, size=(65, 1), mode="nearest")
    line = nd.uniform_filter1d(line, 33, axis=0, mode="nearest")

    # Coverage: how far each pixel has moved from the background toward its column's colour.
    ink = line - background
    alpha = np.clip(((image - background) * ink).sum(-1) / (ink * ink).sum(-1), 0, 1)
    alpha[alpha < 0.004] = 0
    layers.save("ribbon", alpha, line)

    ys = np.arange(h)[:, None]
    weight = alpha.sum(0) + 1e-9
    centre = (alpha * ys).sum(0) / weight
    layers.meta.update(
        background=[float(v) for v in background],
        axis=float((alpha * ys).sum() / alpha.sum()),
        stops=[[x / (w - 1), [float(v) for v in line[x]]] for x in np.linspace(0, w - 1, 17).astype(int)],
        centre=[float(c) for c in nd.uniform_filter1d(centre, 129, mode="nearest")[::16]],
    )
