"""Lumon: the Omarchy mark, wordmark and tagline glowing on a terminal screen,
with two status labels, rows of binary data either side of the mark and a
dashed rule below, over a dim field of faint data and a vignette.

Everything that glows is light added to the field, so the layers are stored as
lift: the colour each adds on top of the backdrop, drawn with "lighter".

Layers: backdrop (the field without the glowing parts), logo, word0..6
(OMARCHY), tag0.. (the tagline's letters), term0.. and branch0.. (the labels'
characters), data (the binary rows) and rule.
Meta: the screen's flat edge colour, the logo's box, the data band's rows,
the glyph counts, the tagline's word breaks and the ink colour.
"""
import numpy as np
from scipy import ndimage as nd

from split import components


def fill(image, hole):
    """A smooth fill of `hole` from the pixels around it (normalized convolution
    at quarter size, widening until every pixel has neighbours)."""
    H, W = hole.shape
    small, known = image[::4, ::4], (~hole[::4, ::4]).astype(float)
    out = np.full(small.shape, np.nan)
    for sigma in (3, 8, 24, 64):
        den = nd.gaussian_filter(known, sigma)
        num = np.stack([nd.gaussian_filter(small[..., k] * known, sigma) for k in range(3)], -1)
        todo = np.isnan(out[..., 0]) & (den > 0.08)
        out[todo] = num[todo] / den[todo, None]
    return np.stack([nd.zoom(out[..., k], 4, order=1)[:H, :W] for k in range(3)], -1)


def split(image, layers):
    H, W = image.shape[:2]
    lum = image.mean(-1)
    flat = np.median(image[:40, :40].reshape(-1, 3), 0)

    core = nd.binary_closing(lum > 110, iterations=3)
    labels, n, sizes, cents = components(core)
    boxes = nd.find_objects(labels)
    logo = int(np.argmax(sizes)) + 1
    ly, lx = boxes[logo - 1]

    # The other glowing shapes sit in horizontal bands: the labels above the
    # logo, data rows beside its foot, the wordmark, the tagline and the rule.
    small = [i for i in range(1, n + 1) if i != logo and sizes[i - 1] >= 40]
    rows = np.zeros(H, bool)
    for i in small:
        rows[boxes[i - 1][0]] = True
    runs, count = nd.label(nd.binary_dilation(rows, iterations=25))
    bands = [np.nonzero(runs == k)[0] for k in range(1, count + 1)]
    bands = [(int(b.min()), int(b.max()) + 1) for b in bands]
    word_band = max(bands, key=lambda b: b[1] - b[0])
    k = bands.index(word_band)
    label_band, data_bands, tag_band, rule_band = bands[0], bands[1:k], bands[k + 1], bands[k + 2]
    data_band = (data_bands[0][0], data_bands[-1][1])
    in_band = lambda i, b: b[0] <= cents[i - 1][0] < b[1]

    # A band's glyphs are its shapes plus any smaller ones (a colon's dots)
    # within their span, grouped by overlapping columns so a dot joins its stem.
    def glyphs(b, keep=lambda i: True):
        big = [i for i in small if in_band(i, b) and keep(i)]
        x0, x1 = min(boxes[i - 1][1].start for i in big), max(boxes[i - 1][1].stop for i in big)
        ids = [i for i in range(1, n + 1) if i != logo and in_band(i, b) and keep(i) and x0 <= cents[i - 1][1] < x1]
        groups = []
        for i in sorted(ids, key=lambda i: boxes[i - 1][1].start):
            if groups and boxes[i - 1][1].start < max(boxes[j - 1][1].stop for j in groups[-1]) - 2:
                groups[-1].append(i)
            else:
                groups.append([i])
        return groups

    words = glyphs(word_band)
    tags = glyphs(tag_band)
    term = glyphs(label_band, lambda i: cents[i - 1][1] < W / 2)
    branch = glyphs(label_band, lambda i: cents[i - 1][1] >= W / 2)

    # Each glyph and the logo take their soft edges and glow with them, out to
    # about as far as each one's glow spreads.
    owner, reach, names = np.zeros(n + 1, int), np.zeros(n + 1), [None]
    for name, gs, r in (("logo", [[logo]], 70), ("word", words, 45), ("tag", tags, 20), ("term", term, 10),
                        ("branch", branch, 10)):
        for j, g in enumerate(gs):
            names.append(name if name == "logo" else f"{name}{j}")
            owner[g], reach[g] = len(names) - 1, r
    dist, (iy, ix) = nd.distance_transform_edt(owner[labels] == 0, return_indices=True)
    near = labels[iy, ix]
    part = np.where(dist < reach[near], owner[near], 0)
    # The glow in the logo's hollow middle comes with it too.
    part[ly, lx] = np.where(part[ly, lx] == 0, 1, part[ly, lx])
    parts = {name: part == k for k, name in enumerate(names) if name}

    # Faint lift over the field marks the data rows and the rule, whose
    # dashes are too dim to be core.
    rough = fill(image, nd.binary_dilation(core, iterations=24))
    faint = nd.binary_dilation((image - rough).max(-1) > 8, iterations=3)
    band_rows = lambda b: ((np.arange(H) >= b[0] - 12) & (np.arange(H) < b[1] + 12))[:, None]
    parts["data"] = faint & band_rows(data_band) & (part == 0)
    parts["rule"] = faint & band_rows(rule_band) & (part == 0)

    hole = part > 0
    for m in parts.values():
        hole |= m
    # Never brighter than the wallpaper, so every layer only adds light.
    backdrop = np.where(hole[..., None], np.minimum(fill(image, hole), image), image)
    backdrop = np.round(np.clip(backdrop, 0, 255))
    layers.save("backdrop", np.ones((H, W)), backdrop, pad=0)

    lift = image - backdrop
    for name, m in parts.items():
        layers.save(name, m & (lift.max(-1) > 0), lift)

    ink = np.percentile(image[core & (labels == logo)], 90, axis=0)
    gaps = [boxes[b[0] - 1][1].start - boxes[a[-1] - 1][1].stop for a, b in zip(tags, tags[1:])]
    breaks = sorted(np.argsort(gaps)[-3:] + 1)
    layers.meta.update(
        flat=[float(v) for v in flat], logo=[lx.start, ly.start, lx.stop, ly.stop],
        data=list(data_band), words=len(words), tags=len(tags), term=len(term), branch=len(branch),
        breaks=[int(b) for b in breaks], ink=[float(v) for v in ink],
    )
