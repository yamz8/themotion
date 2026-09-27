"""Funky shapes: six translucent pastel blobs on flat pink paper, overlapping,
with doodles on top: two sets of concentric rings, brown and white dashes,
light-blue wavy strokes and thin curves.

The blobs are flat colours laid over each other at partial opacity (teal over
pink, teal and pink over lavender), so each is saved as one flat colour at a
fitted opacity and they rebuild their overlaps when drawn in order, even while
they move. The doodles are whatever the blobs leave unexplained, cut from the
still, and a faint `polish` layer holds the last level or two (antialiasing,
overlap rounding), so the layers drawn in place rebuild the wallpaper to
within one level.

Layers: blob_* (in drawing order), curves, ring_tl*, ring_br*, wave*, dash*, polish.
Meta: paper (the flat background), alpha (per blob colour), blobs (name,
centre, extent, in drawing order), curves (x extent), rings (per set: centre,
and each ring's layer and mean radius), waves (layer, x extent), dashes (per
dash: layer, kind, centre, direction, length).
"""
import numpy as np
from scipy import ndimage as nd

from split import components, nearest_label, thin_parts

# The flat colours: paper, the blobs over paper, and their overlaps.
PAPER = (255, 231, 235)
PURE = {"pink": (230, 178, 188), "teal": (164, 198, 198), "lav": (209, 196, 219), "white": (252, 255, 254)}
# Overlap colour: (top blob, the blob under it).
OVER = {(151, 171, 173): ("teal", "pink"), (143, 180, 192): ("teal", "lav"), (209, 160, 181): ("pink", "lav")}
LAV_ALPHA = 0.5  # lavender sits on paper only, so any opacity rebuilds it exactly


def disk(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def split(image, layers):
    h, w = image.shape[:2]
    small = lambda m, k=4: m[::k, ::k]
    paper = np.array(PAPER, float)

    # Classify every pixel against the flat colours.
    flats = {"paper": PAPER, **PURE, **{f"{a}/{b}": c for c, (a, b) in OVER.items()}}
    names = list(flats)
    dist = np.stack([np.abs(image - np.array(flats[n], float)).max(-1) for n in names], -1)
    cls = np.where(dist.min(-1) <= 4, dist.argmin(-1), -1)

    # Measured colours of each flat, and the opacity of each blob colour: an
    # overlap is top-over-under, so (overlap - top) = (1 - a) (under - paper).
    measured = {n: np.median(image[::2, ::2][cls[::2, ::2] == i], 0) for i, n in enumerate(names)}
    ratios = {"pink": [], "teal": []}
    for c, (top, under) in OVER.items():
        ratios[top].append((measured[f"{top}/{under}"] - measured[top], measured[under] - paper))
    alpha = {"lav": LAV_ALPHA, "white": 1.0}
    for top, pairs in ratios.items():
        x = np.concatenate([p[1] for p in pairs])
        y = np.concatenate([p[0] for p in pairs])
        alpha[top] = 1 - float((x * y).sum() / (x * x).sum())
    ink = {k: np.clip((measured[k] - (1 - alpha[k]) * paper) / alpha[k], 0, 255) for k in PURE}

    # Which blob is which, roughly, at quarter size. The doodles are drawn in
    # the blobs' own translucent colours (the rings are teal and lavender), so
    # only broad areas of each flat count, and the rest takes a local,
    # distance-weighted vote of the flats around it.
    order = ["pink_left", "lav", "teal_left", "teal_top", "pink_right", "white"]
    c4 = small(cls)
    known = np.zeros(c4.shape, bool)
    for i, n in enumerate(names):
        # White dashes are as thick as the other strokes are thin; only the white blob is broader still.
        known |= nd.binary_opening(c4 == i, disk(12 if n == "white" else 5))
    weight = nd.gaussian_filter(known.astype(float), 6)
    up = lambda m, k: np.repeat(np.repeat(m, k, 0), k, 1)[:h, :w]
    blobs = []
    for colour in PURE:
        ids = [i for i, n in enumerate(names) if colour in n.split("/")]
        member = np.isin(c4, ids) & known
        vote = nd.gaussian_filter(member.astype(float), 6) / np.maximum(weight, 1e-6)
        m = nd.binary_opening(np.where(known, member, vote > 0.5), disk(2))
        m = nd.binary_fill_holes(nd.binary_closing(np.pad(m, 16, mode="edge"), disk(4))[16:-16, 16:-16])
        labels, n, sizes, _ = components(m)
        keep = 1 if colour in ("lav", "white") else 2
        for i in np.argsort(-sizes)[:keep] + 1:
            m = labels == i
            left = np.nonzero(m)[1].mean() * 4 < w / 2
            name = colour if keep == 1 else f"{colour}_{'left' if left else 'top' if colour == 'teal' else 'right'}"
            blobs.append((name, colour, up(m, 4)))
    blobs.sort(key=lambda b: order.index(b[0]))

    # Each blob's outline at full size. Strokes are drawn in the teal,
    # lavender and white flats (and those over pink); a pixel of those is a
    # stroke where its flat is thin, at half size. Every other flat pixel says
    # for itself whether the blob covers it (paper and plain pink are never
    # strokes, so they are seen right up to a blob's edge); pixels under a
    # stroke take a local vote of those around them, so the edge carries on
    # under it. Near doodles, where the edge is hidden at rest, it is smoothed.
    c2 = cls[::2, ::2]
    thin = np.zeros(c2.shape, bool)
    for i, n in enumerate(names):
        if n not in ("paper", "pink"):
            m = c2 == i
            thin |= m & ~nd.binary_opening(m, disk(16 if n == "white" else 7))
    seen = (cls >= 0) & ~nd.binary_dilation(up(thin, 2), iterations=4)
    # Near a doodle: a thin flat, or a thick patch of no flat at all (unlike
    # the one-pixel antialiasing along a blob's edge).
    crowded = up(nd.binary_dilation(thin | nd.binary_opening(c2 < 0, disk(2)), iterations=12), 2)
    for k, (name, colour, rough) in enumerate(blobs):
        ys, xs = np.nonzero(rough)
        s = np.s_[max(ys.min() - 64, 0):ys.max() + 65, max(xs.min() - 64, 0):xs.max() + 65]
        ids = [i for i, n in enumerate(names) if colour in n.split("/")]
        member = np.isin(cls[s], ids) & seen[s]
        support = nd.gaussian_filter(seen[s].astype(np.float32), 20)
        vote = nd.gaussian_filter(member.astype(np.float32), 20) / np.maximum(support, 1e-9)
        m = np.where(seen[s], member, np.where(support > 0.02, vote > 0.5, rough[s]))
        m = nd.binary_opening(nd.binary_closing(m, disk(3)), disk(3)) & nd.binary_dilation(rough[s], iterations=48)
        m = np.where(crowded[s], nd.gaussian_filter(m.astype(np.float32), 25) > 0.5, m)
        labels, n, sizes, _ = components(m)
        full = np.zeros((h, w), bool)
        full[s] = labels == np.argmax(sizes) + 1
        blobs[k] = (name, colour, nd.binary_fill_holes(full))

    # Each outline, smoothed, is the blob's coverage; in a band along its
    # edge, away from doodles, coverage is read from the picture itself, seen
    # through any blob drawn later (whose own colour is taken back out first).
    comp = np.broadcast_to(paper, image.shape).copy()
    info = []
    for k, (name, colour, hard) in enumerate(blobs):
        ys, xs = np.nonzero(hard)
        s = np.s_[max(ys.min() - 16, 0):ys.max() + 17, max(xs.min() - 16, 0):xs.max() + 17]
        m = hard[s]
        target, ok = image[s].copy(), np.ones(m.shape, bool)
        for _, later, h2 in blobs[k + 1:]:
            h2 = h2[s]
            if alpha[later] >= 1 or not h2.any():
                continue
            inside = nd.binary_erosion(h2, iterations=4)
            target[inside] = (target[inside] - alpha[later] * ink[later]) / (1 - alpha[later])
            ok &= ~(nd.binary_dilation(h2, iterations=4) & ~inside)
        a, c = alpha[colour], ink[colour]
        under = comp[s]
        step = a * (c - under)
        proj = ((target - under) * step).sum(-1) / np.maximum((step * step).sum(-1), 1e-6)
        off = np.abs(target - (under + np.clip(proj, 0, 1)[..., None] * step)).max(-1)
        band = nd.binary_dilation(m, iterations=8) & ~nd.binary_erosion(m, iterations=8)
        use = band & ok & ~crowded[s] & (off < 6) & ((step * step).sum(-1) > 30)
        cover = nd.gaussian_filter(m.astype(float), 1.0)
        cover[use] = np.clip(proj[use], 0, 1)
        cover[~nd.binary_dilation(m, iterations=9)] = 0
        layers.save(f"blob_{name}", cover * a, c, at=(s[1].start, s[0].start))
        # Rebuild exactly what the canvas will draw: 8-bit opacity and colour.
        a8 = (np.round(cover * a * 255) / 255)[..., None]
        comp[s] = np.round(c) * a8 + under * (1 - a8)
        info.append({"name": f"blob_{name}", "colour": colour, "cx": float(xs.mean()), "cy": float(ys.mean()),
                     "x0": int(xs.min()), "y0": int(ys.min()), "x1": int(xs.max()), "y1": int(ys.max())})

    # The doodles: what the blobs leave unexplained.
    rest = image - comp
    diff = np.abs(rest).max(-1)
    strong = diff > 12
    labels, n, sizes, _ = components(strong)
    strong &= np.isin(labels, np.nonzero(sizes >= 60)[0] + 1)
    doodle = nd.binary_dilation(strong, iterations=3)
    # The least opacity that rebuilds each pixel over the settled blobs.
    need = np.max(np.where(rest > 0, rest / np.maximum(255 - comp, 1e-3), -rest / np.maximum(comp, 1e-3)), -1)

    def save(name, mask, soft=20):
        # Opaque where the doodle is solid, partial along its soft edge, with
        # the colour that rebuilds the picture over the settled blobs.
        ys, xs = np.nonzero(mask)
        s = np.s_[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        a = np.clip(diff[s] / soft, 0, 1) if soft else np.clip(need[s], 0, 1)
        a = np.ceil(np.maximum(a, need[s]) * 255) / 255 * mask[s]
        col = comp[s] + rest[s] / np.maximum(a, 1 / 255)[..., None]
        layers.save(name, a, np.clip(col, 0, 255), at=(s[1].start, s[0].start))
        return s

    # Thin curves versus thick strokes.
    thin = thin_parts(strong, 9) & strong
    labels, n, sizes, _ = components(thin)
    thin = np.isin(labels, np.nonzero(sizes >= 3000)[0] + 1)
    thin_near = nd.binary_dilation(thin, iterations=3) & doodle
    thick = doodle & ~thin_near
    s = save("curves", thin_near)
    curves = {"x0": int(s[1].start), "x1": int(s[1].stop)}

    # Thick strokes, told apart by colour first: brown and white dashes (which
    # sit on top of the rings where they cross), then everything else.
    body = strong & ~thin_near
    brown = body & (image.mean(-1) < 150)
    white = body & (image.min(-1) > 238)
    labels = np.zeros((h, w), np.int32)
    kinds = []
    for kind, m in (("brown", brown), ("white", white), ("other", nd.binary_opening(body & ~brown & ~white, disk(1)))):
        lab, n = nd.label(m)
        labels[lab > 0] = lab[lab > 0] + len(kinds)
        kinds += [kind] * n
    near = np.where(thick, nearest_label(labels, 12), 0)
    covered = thin_near.copy()
    dashes, waves, rings = [], [], {"tl": [], "br": []}
    for i, box in enumerate(nd.find_objects(near), 1):
        if box is None:
            continue
        m = np.zeros((h, w), bool)
        m[box] = near[box] == i
        size = int((labels[box] == i).sum())
        ys, xs = np.nonzero(m[box])
        ys, xs = ys + box[0].start, xs + box[1].start
        bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        kind = kinds[i - 1]
        if kind != "other" and size >= 150 and max(bw, bh) < 300:
            # A dash: its direction from the second moments.
            cov = np.cov(np.stack([xs - xs.mean(), ys - ys.mean()]))
            vec = np.linalg.eigh(cov)[1][:, -1]
            if vec[0] < 0:
                vec = -vec
            proj = (xs - xs.mean()) * vec[0] + (ys - ys.mean()) * vec[1]
            dashes.append(({"kind": kind, "cx": float(xs.mean()), "cy": float(ys.mean()), "dx": float(vec[0]),
                            "dy": float(vec[1]), "len": float(proj.max() - proj.min() + 8)}, m))
        elif kind == "other" and bw > 1200 and bh < 250:
            waves.append((ys.mean(), m))
        elif kind == "other" and size >= 3000:
            rings["tl" if xs.mean() < w / 2 else "br"].append((bw * bh, m))
        else:
            continue  # a sliver along a blob's edge: left to the polish
        covered |= m

    dash_meta = []
    for k, (d, m) in enumerate(dashes):
        save(f"dash{k}", m)
        dash_meta.append({"name": f"dash{k}", **d})

    waves.sort(key=lambda p: p[0])
    wave_meta = []
    for k, (_, m) in enumerate(waves):
        s = save(f"wave{k}", m)
        wave_meta.append({"name": f"wave{k}", "x0": int(s[1].start), "x1": int(s[1].stop)})

    ring_meta = {}
    for side, parts in rings.items():
        parts.sort(key=lambda p: p[0])
        # The centre: the middle of the innermost ring.
        ys, xs = np.nonzero(parts[0][1])
        cx, cy = float(xs.mean()), float(ys.mean())
        out = []
        for k, (_, m) in enumerate(parts):
            save(f"ring_{side}{k}", m)
            ys, xs = np.nonzero(m)
            out.append({"name": f"ring_{side}{k}", "r": float(np.hypot(xs - cx, ys - cy).mean())})
        ring_meta[side] = {"cx": cx, "cy": cy, "rings": out}

    # What is left: antialiasing and rounding, a level or two, and slivers
    # along blob edges, drawn last.
    rest[covered] = 0
    diff = np.abs(rest).max(-1)
    need[covered] = 0
    save("polish", diff >= 1.5, soft=0)

    layers.meta.update(
        paper=[float(v) for v in PAPER],
        alpha={k: float(v) for k, v in alpha.items()},
        blobs=info,
        curves=curves,
        dashes=dash_meta,
        waves=wave_meta,
        rings=ring_meta,
    )
