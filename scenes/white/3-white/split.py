"""White stationery: a photo of white paper on a white table. A folder at the
top, a sheet at the left, a sheet at the bottom and two stacks of cards, all
laid along the same diagonal.

Photos don't split into flat shapes, so nothing here is recoloured: the scene
cuts each piece from the still at runtime through a mask, and fills the table
under a piece that has not landed yet with a smooth fit of the bare table.

Every pixel near a piece belongs to exactly one piece (the nearest), so the
cuts tile the picture with hard seams between neighbours and the landed
pieces rebuild the still exactly.

Layers: cut-<piece> (alpha only: the piece's cut, its outline plus a margin
that carries its shadow and soft edge), fill (1/8 size, RGBA: the bare table
under every piece; a landed neighbour's cut covers it at their seam).
Meta: pieces (per piece: outline polygon, the image edges it runs off, and
its diagonal as a unit vector), fill_scale.
"""
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
from scipy.spatial import ConvexHull

# Outlines in wallpaper pixels, traced from the photo's edges. Points past the
# picture mean the piece runs off that edge.
PIECES = {
    "folder": [[160, -10], [3620, -10], [4292, 528], [4312, 752], [2080, 2192], [2040, 2160]],
    "left": [[-10, 260], [1780, 2408], [-10, 3712]],
    "bottom": [[3212, 2072], [4680, 3620], [4080, 4170], [460, 4170]],
    "cards": [[3200, 1608], [4400, 712], [5172, 1360], [3980, 2420]],
    "stack": [[4112, 2528], [5328, 1512], [6250, 2220], [6250, 2460], [5000, 3440]],
}
CUT = 240        # a cut reaches this far past its outline, to carry the shadow
CUT_SOFT = 60    # and fades out over the last stretch, where the table is bare
FILL = 120       # the table fill under a missing piece reaches this far
FILL_SOFT = 40
SHADOW = [-110, 100]  # the light comes from the upper right; shadows fall this far down-left
SMALL = 8        # the fill is stored at 1/8 size; it is smooth


def split(image, layers):
    h, w = image.shape[:2]
    names = list(PIECES)
    dist = []
    for name in names:
        # The piece swept along the light, so its shadow goes wherever it goes.
        pts = np.array(PIECES[name], float)
        pts = np.vstack([pts, pts + SHADOW])
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([tuple(p) for p in pts[ConvexHull(pts).vertices]], fill=255)
        dist.append(nd.distance_transform_edt(np.asarray(m) < 128))
    dist = np.array(dist, np.float32)
    nearest = dist.argmin(0)
    near = dist.min(0)
    label = np.where(near < CUT, nearest + 1, 0)

    # The bare table: a smooth cubic fit over everything well clear of the pieces.
    s = SMALL
    small = image[s // 2::s, s // 2::s][:h // s, :w // s]
    yy, xx = np.mgrid[0:small.shape[0], 0:small.shape[1]]
    u, v = (xx * s + s / 2) / w - 0.5, (yy * s + s / 2) / h - 0.5
    terms = np.stack([u ** i * v ** j for i in range(4) for j in range(4 - i)], -1)
    bare = near[s // 2::s, s // 2::s][:h // s, :w // s] > CUT + 80
    table = np.stack([np.linalg.lstsq(terms[bare], small[..., k][bare], rcond=None)[0] for k in range(3)], -1)
    fit = terms @ table

    fill = np.zeros(small.shape[:2])
    for i, name in enumerate(names):
        own = label == i + 1
        # The cut: everything this piece owns, fading out only on the table side.
        layers.save(f"cut-{name}", own * np.clip((CUT - dist[i]) / CUT_SOFT, 0, 1), 0)
        f = np.clip((FILL - dist[i][::s, ::s][:h // s, :w // s]) / FILL_SOFT, 0, 1)
        fill = np.maximum(fill, f * own[::s, ::s][:h // s, :w // s])

    rgba = np.dstack([np.clip(np.round(fit), 0, 255), np.round(fill * 255)]).astype(np.uint8)
    Image.fromarray(rgba).save(os.path.join(layers.outdir, "fill.png"), optimize=True)
    layers.meta["layers"].append({"name": "fill", "x": 0, "y": 0, "w": w, "h": h})

    def runs_off(poly):
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        return {"left": min(xs) < 0, "top": min(ys) < 0, "right": max(xs) > w, "bottom": max(ys) > h}

    layers.meta.update(
        fill_scale=s,
        pieces={name: {"outline": PIECES[name], "off": runs_off(PIECES[name])} for name in names},
    )
    resid = np.abs(small - fit)[bare].mean()
    print(f"table fit: mean residual {resid:.2f} over {bare.mean() * 100:.0f}% of the picture")
