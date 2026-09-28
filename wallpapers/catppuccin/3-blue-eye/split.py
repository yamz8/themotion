"""Blue eye: one colour of line-work on a flat background, round about the centre.

Layers: rays (the swirl between the pupil and the ring), petals (the ring of loops).
Meta: cx, cy, the pupil, seam and outer radii, the ink and background colours.
"""
import numpy as np

from split import circle_of, grid


def split(image, layers):
    yy, xx = grid(image)
    background = image[40, 40]
    ink = np.array([150.0, 205.0, 251.0])  # the lines at full coverage

    # Blue has the most contrast between the lines and the background.
    alpha = np.clip((image[..., 2] - background[2]) / (ink[2] - background[2]), 0, 1)
    cx, cy, outer = circle_of(np.abs(image - background).sum(-1) > 6)
    r = np.hypot(xx + 0.5 - cx, yy + 0.5 - cy)

    # The rays stop at 184 px (4K); the petals' inner envelope starts at 185.
    seam = 185 * image.shape[1] / 3840
    pupil = float(r[alpha > 0.02].min())

    layers.save("rays", alpha * (r < seam), ink)
    layers.save("petals", alpha * (r >= seam), ink)
    layers.meta.update(cx=cx, cy=cy, pupil=pupil, seam=seam, outer=outer,
                       ink=[float(v) for v in ink], background=[float(v) for v in background])
