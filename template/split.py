"""Split the wallpaper into movable layers.

This starter finds dark shapes on a smooth light backdrop and saves each one
as its own layer. Adapt the thresholds and grouping to your wallpaper.
"""
import numpy as np

from split import components, coverage, erode, fit_plane, nearest_label


def split(image, layers):
    lum = image.mean(-1)
    backdrop_mask = lum > np.percentile(lum, 60)
    coef, backdrop = fit_plane(image, erode(backdrop_mask, 4))
    ink = image[lum < np.percentile(lum, 2)].mean(0)

    alpha = coverage(image, backdrop, ink)
    labels, n, sizes, cents = components(alpha > 0.5)
    near = nearest_label(labels, 8)
    for k, i in enumerate(np.argsort(-sizes)[:12] + 1):
        layers.save(f"shape{k}", alpha * ((near == i) & (alpha > 0.01)), ink)

    layers.meta.update(coef=coef, ink=[float(v) for v in ink])
