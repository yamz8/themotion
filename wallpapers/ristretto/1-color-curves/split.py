"""Colour curves: overlapping paper bands in coffee colours, arcing from the
bottom left over a dark dome at the bottom middle, on a dark ground.

The bands are soft gradients with hard, antialiased edges between them, so the
picture splits cleanly into flat-edged regions: every place where the colour
jumps is an edge, and every piece between edges is a region. A region is not
yet a band, though. The bands lie on one another like paper strips: one edge
of each pair has a light rim and casts a thin shadow on the strip beneath, and
two strips cross twice, so where they overlap they make a lighter lens and
where they part they show what lies under them. Cut as they are seen, the
regions have corners wherever a band dips under another, and a band moved on
its own shows those corners, the shadow of its neighbour, and the straight cut
where it leaves the screen.

So each band is saved as the whole strip it would be on its own:

- Bands are stacked bottom to top (STACK). An edge belongs to the band on top
  of it; the band beneath reaches under it.
- Every band is described around the pivot's ellipse, where the scene turns
  it, as an inner and an outer edge for each angle. An edge the band owns is
  kept as it is seen. Where a band above covers it, the edge goes on under
  that band: between two stretches it owns, along the smooth curve joining
  them; beyond its last one, turning from its own course onto a curve MARGIN
  in under the band above, so a neighbour that drifts a little apart while
  both move never opens a seam. Past the screen's edges it carries straight
  on, so a band turned back or overshooting never shows where the screen cut
  it.
- Its colour is the wallpaper's own inside it, carried on smoothly where it
  is hidden or off screen; the thin strip next to a band above (that band's
  shadow) is replaced the same way.
- A band carries its rim and the shadow it casts: the wallpaper pixels just
  outside its own edges are saved as a dark or light fringe over the band
  beneath, so the bands drawn back in place are the wallpaper again.

Layers: ground (the whole screen, which stays still) and band0, band1, ...
in drawing order, bottom first.
Meta: pivot and aspect (the ellipse the bands turn about), the ground's
colour, and per band its name, slot (its place outermost first, which sets
when it enters), median colour, centroid, nesting radius, span (the angles it
covers around the pivot) and, for the dome, the middle of its base.
"""
import numpy as np
from scipy import ndimage as nd


EDGE = 25       # gradient strength of an edge, after a 2 px blur; the soft gradients inside bands stay under 10
SMALL = 2000    # pieces smaller than this are slivers of an edge, not regions
REACH = 8       # how far (px) an edge pixel or sliver looks for a region to join
# The inner domes are ellipses around a centre just below the bottom edge,
# about 1.5 times wider than tall (fitted to the edges between them).
PIVOT = (1420.0, 1720.0)
ASPECT = 1.5
# The outer bands open out toward the top right, so they nest around a
# flatter ellipse further out; its median radius orders the regions outermost first.
NEST = (2000.0, 2200.0)
NEST_ASPECT = 1.2

# The regions outermost first are: 0 brown, 1 sage-to-tan, 2 bright orange
# (between 1 and 4 at the right), 3 teal, 4 orange, 5 the light lens where 1
# and the orange band overlap, 6 dark brown (between 1 and 7 at the bottom),
# 7 orange, 8 red, 9 maroon, 10 dark maroon, 11 the dome. 4 and 7 are one
# orange band that the lens and the red band cut in two (MERGE). Bands bottom
# to top, from the rims: the outer of each pair of rings lies on the inner,
# the sage and orange bands cross over the teal, dark brown and bright orange
# showing between them, and the lens is their overlap, on top. The dome comes
# last and rises over the ring around it, so it goes on top.
MERGE = [(4, 7)]
STACK = [10, 9, 8, 6, 3, 2, 4, 0, 1, 5, 11]
DOME = 11

MARGIN = 80     # how far (ellipse px) a band reaches under a band above it that enters after it
DEEP = 120      # ... and under one that is already in place when it enters, where the reach is never seen
BLEND = 160     # px of arc over which an edge turns from its own course onto that margin
TIP = 640       # px of arc from a band's pointed end over which its reach grows to full
SLOPE = 40      # px of arc an edge's direction is read over where it carries on
EXTEND = (0.15, 0.2)  # how far (rad) a band goes on past its ends at the screen's edges, before and after
SHADE = 5       # px next to a band above whose colour is that band's shadow
FRINGE = 4      # px outside a band's own edge whose rim and shadow it carries
OFFREACH = 400  # how far (ellipse px) past the screen a band cut only by the screen goes on
JUNCTION = 10   # px around a point where three bands meet that carry no fringe
NOISE = 3       # levels of difference from the band beneath below which a fringe pixel is left clear

SLIVER = 4      # ellipse px: a band narrower than this has ended
DPHI = 0.0005   # angle step (rad) of the edge tables
DRHO = 0.5      # radius step (ellipse px) the edges are found at
OFF = -2        # off the screen
GROUND = -1


def split(image, layers):
    h, w = image.shape[:2]
    labels, regions, ground = find_regions(image)
    n = len(regions)
    assert n == 12, f"expected 12 bands, found {n}"

    # Region index -> piece (its place in STACK); merged regions share one.
    piece_of = {}
    for z, r in enumerate(STACK):
        piece_of[r] = z
    for group in MERGE:
        for r in group:
            piece_of[r] = piece_of[group[0]]
    zmap = np.full(n + 2, -1)
    for r, z in piece_of.items():
        zmap[r] = z
    lab = np.where(ground, GROUND, labels)          # region index, ground = -1
    zimg = np.where(ground, -1, zmap[np.maximum(labels, 0)])

    phis = np.arange(-0.6, np.pi + 0.6, DPHI)
    rhos = np.arange(0, 3400, DRHO)
    zpolar = polar_table(zimg, phis, rhos, w, h)

    # A band reaches far under a band that is in place before it enters
    # (outermost first), and only a little under one that comes after it,
    # since until then the reach shows as part of the band.
    slot_of = np.array([min([r] + [m for g in MERGE if g[0] == r for m in g[1:]]) for r in STACK])
    pieces = []
    for z, r in enumerate(STACK):
        ids = [r] + [m for g in MERGE if g[0] == r for m in g[1:]]
        vis = np.isin(lab, ids)
        lo, hi = edges(zpolar, z, phis, rhos, vis, slot_of)
        pieces.append(dict(z=z, slot=min(ids), ids=ids, vis=vis, lo=lo, hi=hi))

    # Each band: its shape, then its colour; fringes need the colour of the band beneath.
    for p in pieces:
        shape(p, phis, zimg, w, h)
        colour(p, image, zimg)
    for p in pieces:
        fringe(p, pieces, image, zimg)

    ground_trust = ground & (nd.distance_transform_edt(ground) >= SHADE)
    layers.save("ground", np.ones((h, w)), fill(image, ground_trust))

    yy, xx = np.mgrid[0:h, 0:w]
    radius = np.hypot(xx - NEST[0], (yy - NEST[1]) * NEST_ASPECT)
    # Angle around the pivot's ellipse, clockwise from its left end: 0 at the
    # left, pi/2 straight up, pi at the right.
    angle = np.arctan2(-(yy - PIVOT[1]) * ASPECT, -(xx - PIVOT[0]))
    meta = []
    for i, p in enumerate(pieces):
        name = f"band{i}"
        layers.save(name, p["alpha"], p["color"], at=(p["x0"], p["y0"]))
        m = p["vis"]
        cy, cx = nd.center_of_mass(m)
        b = dict(name=name, slot=p["slot"], color=[int(v) for v in np.median(image[m], 0)],
                 centroid=[round(float(cx), 1), round(float(cy), 1)],
                 radius=round(float(np.median(radius[m])), 1),
                 span=[round(float(v), 4) for v in np.percentile(angle[m], [0.2, 99.8])])
        if p["slot"] == DOME:
            xs = np.nonzero(m.any(0))[0]
            b.update(dome=True, base=[round(float(xs.min() + xs.max() + 1) / 2, 1), float(h)])
        meta.append(b)

    layers.meta.update(pivot=list(PIVOT), aspect=ASPECT,
                       ground_color=[int(v) for v in np.median(image[ground], 0)], bands=meta)


def find_regions(image):
    """The flat regions between edges, tiling the picture: labels (-1 for the
    ground), the band regions outermost first, and the ground's mask."""
    h, w = image.shape[:2]
    blur = nd.gaussian_filter(image, (2, 2, 0))
    grad = sum(np.hypot(nd.sobel(blur[..., k], 0), nd.sobel(blur[..., k], 1)) for k in range(3))
    labels, n = nd.label(grad < EDGE)
    sizes = nd.sum(np.ones_like(labels), labels, range(1, n + 1))
    keep = [i + 1 for i in range(n) if sizes[i] >= SMALL]
    # Edge pixels and slivers go to the neighbouring region whose colour they
    # match, not merely the nearest one, so each region's edge sits where the
    # wallpaper's colour turns from one band to the next.
    known = np.isin(labels, keep)
    best = np.full((h, w), np.inf)
    out = labels.copy()
    for k in keep:
        m = labels == k
        dist = nd.distance_transform_edt(~m)
        near = ~known & (dist <= REACH)
        if not near.any():
            continue
        core = nd.binary_erosion(m, iterations=3)
        local = nd.gaussian_filter(image * core[..., None], (12, 12, 0)) / (nd.gaussian_filter(core.astype(float), 12)[..., None] + 1e-6)
        cost = np.abs(image - local).sum(-1) + 2 * dist     # the colour decides; distance only breaks ties
        take = near & (cost < best)
        best[take] = cost[take]
        out[take] = k
    _, (iy, ix) = nd.distance_transform_edt(~known, return_indices=True)
    rest = ~known & np.isinf(best)
    out[rest] = labels[iy, ix][rest]
    labels = out

    ground_id = labels[0, 0]
    yy, xx = np.mgrid[0:h, 0:w]
    radius = np.hypot(xx - NEST[0], (yy - NEST[1]) * NEST_ASPECT)
    bands = [k for k in keep if k != ground_id]
    bands.sort(key=lambda k: -np.median(radius[labels == k]))
    index = np.full(labels.max() + 1, -1)
    for i, k in enumerate(bands):
        index[k] = i
    labels = index[labels]
    labels[labels < 0] = len(bands)
    # A few edge pixels end up as specks apart from their region; each goes to the region around it.
    stray = np.zeros((h, w), bool)
    for i in range(len(bands) + 1):
        parts, count = nd.label(labels == i)
        if count > 1:
            sizes = nd.sum(np.ones_like(parts), parts, range(1, count + 1))
            stray |= (parts > 0) & (parts != np.argmax(sizes) + 1)
    _, (iy, ix) = nd.distance_transform_edt(stray, return_indices=True)
    labels = labels[iy, ix]
    ground = labels == len(bands)
    labels[ground] = -1
    return labels, bands, ground


def to_xy(phi, rho):
    return PIVOT[0] - rho * np.cos(phi), PIVOT[1] - rho * np.sin(phi) / ASPECT


def to_polar(x, y):
    u, v = x - PIVOT[0], (y - PIVOT[1]) * ASPECT
    return np.arctan2(-v, -u), np.hypot(u, v)


def polar_table(zimg, phis, rhos, w, h):
    """Which band (by its place in the stack) each point of the pivot's
    ellipses shows, for every angle and radius; OFF off the screen."""
    out = np.full((len(phis), len(rhos)), OFF, np.int8)
    for a in range(0, len(phis), 500):
        x, y = to_xy(phis[a:a + 500, None], rhos[None, :])
        xi, yi = np.rint(x).astype(int), np.rint(y).astype(int)
        ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        out[a:a + 500][ok] = zimg[yi[ok], xi[ok]]
    return out


def edges(zpolar, z, phis, rhos, vis, slot_of):
    """A band's inner and outer edge, as a radius for every angle, carried on
    where it is hidden or off the screen (see the module's notes)."""
    m = zpolar == z
    present = m.any(1)
    nr = len(rhos)
    first = np.argmax(m, 1)
    last = nr - 1 - np.argmax(m[:, ::-1], 1)
    # A ray that crosses the band twice (it curls round at the screen's foot)
    # keeps the longer crossing.
    holes = (last - first + 1) - m.sum(1)
    for j in np.nonzero(present & (holes > 8))[0]:
        rr = runs(m[j])
        a, b = max(rr, key=lambda r: r[1] - r[0])
        first[j], last[j] = a, b
    # Where the band thins to a sliver a few px wide it has ended: the sliver
    # is the antialiased seam along a neighbour, and the band above covers it.
    present &= (last - first) * DRHO >= SLIVER
    for a, b in runs(present):
        if b - a < 60:
            present[a:b + 1] = False
    cols = np.arange(len(phis))
    below = np.where(first > 0, zpolar[cols, np.maximum(first - 1, 0)], OFF)
    above = np.where(last < nr - 1, zpolar[cols, np.minimum(last + 1, nr - 1)], OFF)
    # Where along each ray the band's mask crosses one half, to a fraction of a pixel.
    soft = nd.gaussian_filter(vis.astype(float), 0.7)
    lo = refine(soft, phis, rhos[first] - DRHO / 2)
    hi = refine(soft, phis, rhos[last] + DRHO / 2)
    lo[~present] = hi[~present] = np.nan
    # Where the band ends on the screen in a point (both its edges seen up to
    # there), its reach under the bands above shrinks to nothing at the point,
    # so the band keeps its own pointed end instead of a blunt one.
    seen = np.nonzero(present)[0]
    px = 1 / (np.nanmedian((lo + hi)[present] / 2) * DPHI)
    taper = np.ones(len(phis))
    points = []
    for end in (seen.min(), seen.max()):
        if below[end] != OFF and above[end] != OFF and (hi[end] - lo[end]) < 3 * SLIVER:
            points.append(end)
            x = np.clip(np.abs(cols - end) / (TIP * px), 0, 1)
            taper *= x * x * (3 - 2 * x)
    # How far each edge may reach: no further than across the band above it,
    # or it would show out on that band's far side.
    reach_lo = np.full(len(phis), np.inf)
    reach_hi = np.full(len(phis), np.inf)
    for j in np.nonzero(present)[0]:
        if first[j] > 0 and zpolar[j, first[j] - 1] > z:
            col = zpolar[j, :first[j]]
            r = np.nonzero(col != col[-1])[0]
            if len(r) and col[r[-1]] != OFF:
                reach_lo[j] = rhos[first[j]] - rhos[r[-1]] - 4
        if last[j] < nr - 1 and zpolar[j, last[j] + 1] > z:
            col = zpolar[j, last[j] + 1:]
            r = np.nonzero(col != col[0])[0]
            if len(r) and col[r[0]] != OFF:
                reach_hi[j] = rhos[last[j] + 1 + r[0]] - rhos[last[j]] - 4
    out = []
    for f, nb, sign, room in ((lo, below, -1, reach_lo), (hi, above, 1, reach_hi)):
        cls = np.where(nb == OFF, 0, np.where(nb < z, 1, 2))      # 0 off screen, 1 own, 2 under a band above
        cls[~present] = 0
        reach = np.where((nb >= 0) & (slot_of[np.clip(nb, 0, None)] < slot_of[z]), DEEP, MARGIN)
        reach = np.maximum(np.minimum(reach, room), 0)
        out.append(complete(f, cls, nb, present, sign, phis, reach, taper, points))
    close_points(out[0], out[1], points, px)
    return out


def refine(soft, phis, rho0):
    """The radius near rho0, along each ray, where `soft` crosses 0.5."""
    steps = np.arange(-3, 3.01, 0.25)
    rho = rho0[:, None] + steps[None, :]
    x, y = to_xy(phis[:, None], rho)
    v = nd.map_coordinates(soft, [y.ravel(), x.ravel()], order=1, mode="nearest").reshape(rho.shape)
    s = v - 0.5
    cross = np.sign(s[:, :-1]) != np.sign(s[:, 1:])
    out = rho0.copy()
    for i in np.nonzero(cross.any(1))[0]:
        ks = np.nonzero(cross[i])[0]
        k = ks[np.argmin(np.abs(steps[ks]))]
        out[i] = rho[i, k] + (rho[i, k + 1] - rho[i, k]) * s[i, k] / (s[i, k] - s[i, k + 1])
    return out


def runs(mask):
    """(start, end) of each run of True, end inclusive."""
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0] - 1))


def smooth_runs(f, mask, key, sigma):
    out = np.full_like(f, np.nan)
    for a, b in runs(mask):
        # split further where the neighbour changes
        cuts = [a] + [i for i in range(a + 1, b + 1) if key[i] != key[i - 1]] + [b + 1]
        for s, e in zip(cuts[:-1], cuts[1:]):
            out[s:e] = nd.gaussian_filter1d(f[s:e], sigma, mode="nearest") if e - s > 2 else f[s:e]
    return out


def line_at(f, end, step, k):
    """Value and slope of f at index `end`, read over the k samples from end
    going in direction -step (the run it ends)."""
    idx = np.arange(end, end - step * k, -step)
    idx = idx[(idx >= 0) & (idx < len(f))]
    idx = idx[np.isfinite(f[idx])]
    if len(idx) < 2:
        return f[end], 0.0
    slope, icept = np.polyfit(idx, f[idx], 1)
    return slope * end + icept, slope


def complete(f, cls, nb, present, sign, phis, reach, taper, points):
    """An edge carried over every angle the band could be seen at."""
    n = len(f)
    j = np.arange(n)
    rho = np.nanmedian(f[present])
    px = 1 / (rho * DPHI)                       # columns per px of arc
    own, under = cls == 1, cls == 2
    # a stretch of own edge a few px long is a corner where bands meet, not an
    # edge; and the last few px of any stretch, where bands meet, are ragged
    trim = int(2.5 * JUNCTION * px)
    for a, b in runs(own):
        if (b - a) < 30 * px:
            own[a:b + 1] = False
            under[a:b + 1] = present[a:b + 1]
            continue
        for lo_, hi_ in ((a, a + trim), (b - trim, b)):
            side = lo_ - 1 if lo_ == a else hi_ + 1
            if 0 <= side < n and present[side]:
                own[lo_:hi_ + 1] = False
                under[lo_:hi_ + 1] = cls[side] == 2
    fo = smooth_runs(f, own, nb, 1.5 * px)
    # The visible edge under another band is ragged where three bands meet;
    # the reach follows a smoothed envelope of it, never inside it.
    env = np.where(under, sign * f, -np.inf)
    env = sign * nd.maximum_filter1d(env, max(3, int(24 * px)) | 1)
    env = np.where(under & np.isfinite(env), env, f)
    env = smooth_runs(env, under, np.zeros(n), 8 * px)
    env = np.where(under, sign * np.maximum(sign * env, sign * f), np.nan)
    target = smooth_runs(env + sign * reach, under, nb, MARGIN * px)
    # never closer to the visible edge than half the margin
    target = np.where(under, sign * np.maximum(sign * target, sign * (env + sign * np.maximum(reach / 2, 1.5))), np.nan)
    # ... and shrinks onto the visible edge toward a pointed end
    target = f + sign * 1.0 + taper * (target - f - sign * 1.0)

    seen = np.nonzero(present)[0]
    # past an end at the screen's edge the band goes on; a pointed end is where it stops
    lo_j = seen.min() if seen.min() in points else max(0, int(seen.min() - EXTEND[0] / DPHI))
    hi_j = seen.max() if seen.max() in points else min(n - 1, int(seen.max() + EXTEND[1] / DPHI))
    out = np.full(n, np.nan)
    out[own] = fo[own]
    k = max(3, int(SLOPE * px))
    blend = BLEND * px
    for a, b in runs(~own):
        a, b = max(a, lo_j), min(b, hi_j)
        if a > b:
            continue
        left = a - 1 if a - 1 >= lo_j and own[a - 1] else None
        right = b + 1 if b + 1 <= hi_j and own[b + 1] else None
        seg = j[a:b + 1]
        # the margin curve, carried straight on where the band is not under another
        u = target[a:b + 1].copy()
        have = np.isfinite(u)
        if have.any():
            fs, ls = np.nonzero(have)[0][[0, -1]]
            y0, m0 = line_at(target, a + fs, -1, k)
            y1, m1 = line_at(target, a + ls, 1, k)
            inner = np.interp(seg, seg[have], u[have])
            u = np.where(seg < a + fs, y0 + m0 * (seg - a - fs), np.where(seg > a + ls, y1 + m1 * (seg - a - ls), inner))
        if left is not None and right is not None:
            y0, m0 = line_at(fo, left, 1, k)
            y1, m1 = line_at(fo, right, -1, k)
            L = right - left
            t = (seg - left) / L
            v = ((2 * t**3 - 3 * t**2 + 1) * y0 + (t**3 - 2 * t**2 + t) * L * m0
                 + (-2 * t**3 + 3 * t**2) * y1 + (t**3 - t**2) * L * m1)
        elif left is not None or right is not None:
            end = left if left is not None else right
            y0, m0 = line_at(fo, end, 1 if left is not None else -1, k)
            e = y0 + m0 * (seg - end)
            if have.any():
                x = np.clip(np.abs(seg - end) / blend, 0, 1)
                wgt = x * x * (3 - 2 * x)
                v = (1 - wgt) * e + wgt * u
            else:
                v = e
        elif have.any():
            v = u
        else:
            # cut only by the screen: carried well out past it
            v = f[a:b + 1] + sign * OFFREACH
            fin = np.isfinite(v)
            if fin.any() and not fin.all():
                v = np.interp(seg, seg[fin], v[fin])
        # always cover what is seen of the band
        cover = under[a:b + 1]
        v = np.where(cover, sign * np.maximum(sign * v, sign * (f[a:b + 1] + sign * 1.0)), v)
        out[a:b + 1] = v
    out[:lo_j] = np.nan
    out[hi_j + 1:] = np.nan
    # Smooth what was carried on, the own edge held fixed, so no wobble is left
    # where the edge turns from its own course onto the reach.
    fin = np.isfinite(out)
    free = fin & ~own
    cover = under & fin
    for _ in range(4):
        for a, b in runs(fin):
            seg = out[a:b + 1]
            sm = nd.gaussian_filter1d(seg, 10 * px, mode="nearest")
            out[a:b + 1] = np.where(free[a:b + 1], sm, seg)
        out[cover] = sign * np.maximum(sign * out[cover], sign * (f[cover] + sign * 1.0))
    return out


def close_points(lo, hi, points, px):
    """Past a pointed end, the band's two edges carry straight on until they
    meet, within three times the band's width there."""
    n = len(lo)
    k = max(3, int(SLOPE * px))
    for end in points:
        step = 1 if np.isfinite(lo[max(0, end - 1)]) and not np.isfinite(lo[min(n - 1, end + 1)]) else -1
        l0, lm = line_at(lo, end, -step, k)
        h0, hm = line_at(hi, end, -step, k)
        w0 = max(hi[end] - lo[end], 1.0)
        length = max(int(3 * w0 * px), 2)
        beyond = np.arange(end + step, end + step * length, step)
        beyond = beyond[(beyond >= 0) & (beyond < n)]
        dj = beyond - end
        ll, hh = l0 + lm * dj, h0 + hm * dj
        # each edge carries straight on; if they would not meet soon, they are drawn together
        w = np.minimum(hh - ll, w0 * (1 - np.abs(dj) / length))
        c = (ll + hh) / 2
        lo[beyond], hi[beyond] = c - w / 2, c + w / 2


def shape(p, phis, zimg, w, h):
    """Rasterise a band's edges into its coverage, on a canvas reaching past the screen."""
    lo, hi = p["lo"], p["hi"]
    ok = np.isfinite(lo) & np.isfinite(hi) & (hi > lo + 1)
    # where the two edges run together the band has ended: no hair-thin spokes beyond
    for a, b in runs(ok):
        if b - a < 40:
            ok[a:b + 1] = False
    xs, ys = [], []
    for e in (lo, hi):
        x, y = to_xy(phis[ok], e[ok])
        xs.append(x); ys.append(y)
    xs, ys = np.concatenate(xs), np.concatenate(ys)
    x0, x1 = int(np.floor(xs.min())) - 4, int(np.ceil(xs.max())) + 5
    y0, y1 = int(np.floor(ys.min())) - 4, int(np.ceil(ys.max())) + 5
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(float)
    phi, rho = to_polar(xx, yy)
    jf = (phi - phis[0]) / DPHI
    cols = np.arange(len(phis))
    # Past either end of the band the edge tables are empty; fill them from the
    # nearest end so the distance field stays smooth, and cut the band there.
    idx = np.nonzero(ok)[0]
    near = idx[np.clip(np.searchsorted(idx, cols), 0, len(idx) - 1)]
    lo_i = np.interp(jf, cols, np.where(ok, lo, lo[near]))
    hi_i = np.interp(jf, cols, np.where(ok, hi, hi[near]))
    inside = np.interp(jf, cols, ok.astype(float), left=0, right=0) > 0.999
    d = np.minimum(rho - lo_i, hi_i - rho)
    gy, gx = np.gradient(d)
    sd = d / np.maximum(np.hypot(gx, gy), 1e-6)
    sd = np.where(inside, sd, -10.0)
    alpha = np.clip(sd + 0.5, 0, 1)
    # On the screen, never over a band beneath (it would hide it at rest);
    # off the screen anything goes.
    sy0, sy1, sx0, sx1 = max(y0, 0), min(y1, h), max(x0, 0), min(x1, w)
    win = (slice(sy0 - y0, sy1 - y0), slice(sx0 - x0, sx1 - x0))
    zs = zimg[sy0:sy1, sx0:sx1]
    mine = p["vis"][sy0:sy1, sx0:sx1]
    below = (zs < p["z"]) & ~nd.binary_dilation(mine, iterations=6)
    alpha[win] *= 1 - np.clip(nd.gaussian_filter(below.astype(float), 0.7) * 2, 0, 1) * below
    p.update(x0=x0, y0=y0, alpha=alpha, sd=sd, win=win, screen=(sy0, sy1, sx0, sx1))


def fill(image, known, levels=10):
    """Fill the pixels outside `known` from the known ones around them, at
    growing scales (normalised convolution), coarse scales on a reduced grid."""
    out = np.where(known[..., None], image, 0).astype(float)
    done = known.copy()
    num0 = np.where(known[..., None], image, 0).astype(float)
    den0 = known.astype(float)
    hh, ww = known.shape
    for level in range(levels):
        s = 2 ** level * 2
        if s <= 8:
            num = nd.gaussian_filter(num0, (s, s, 0))
            den = nd.gaussian_filter(den0, s)
        else:
            f = s // 4
            sh, sw = -(-hh // f), -(-ww // f)
            pn = np.zeros((sh * f, sw * f, 3)); pn[:hh, :ww] = num0
            pd = np.zeros((sh * f, sw * f)); pd[:hh, :ww] = den0
            sn = pn.reshape(sh, f, sw, f, 3).mean((1, 3))
            sd = pd.reshape(sh, f, sw, f).mean((1, 3))
            sn = nd.gaussian_filter(sn, (4, 4, 0)); sd = nd.gaussian_filter(sd, 4)
            zy, zx = (np.arange(hh) + 0.5) / f - 0.5, (np.arange(ww) + 0.5) / f - 0.5
            gy, gx = np.meshgrid(zy, zx, indexing="ij")
            num = np.stack([nd.map_coordinates(sn[..., c], [gy, gx], order=1, mode="nearest") for c in range(3)], -1)
            den = nd.map_coordinates(sd, [gy, gx], order=1, mode="nearest")
        take = ~done & (den > 1e-4)
        out[take] = num[take] / den[take][:, None]
        done |= take
        if done.all():
            break
    if not done.all():
        _, (iy, ix) = nd.distance_transform_edt(~done, return_indices=True)
        out[~done] = out[iy[~done], ix[~done]]
    return out


def colour(p, image, zimg):
    """The wallpaper's own colour inside the band, carried on smoothly where it
    is hidden, off the screen, or shaded by the band above."""
    sy0, sy1, sx0, sx1 = p["screen"]
    win = p["win"]
    hh, ww = p["alpha"].shape
    zs = zimg[sy0:sy1, sx0:sx1]
    mine = p["vis"][sy0:sy1, sx0:sx1]
    to_above = nd.distance_transform_edt(~(zs > p["z"]))
    to_other = nd.distance_transform_edt(mine)
    # and not right at a point where three bands meet, whose pixels mix them all
    kinds = sum(nd.maximum_filter((zs == q).astype(np.uint8), size=2 * JUNCTION + 1) for q in np.unique(zs))
    trust = mine & (to_above >= SHADE) & (to_other >= 1.5) & (kinds < 3)
    known = np.zeros((hh, ww), bool)
    img = np.zeros((hh, ww, 3))
    known[win] = trust
    img[win] = image[sy0:sy1, sx0:sx1]
    p["color"] = fill(img, known)


def fringe(p, pieces, image, zimg):
    """The band's rim and shadow on the band beneath, just outside its own
    edges, saved as a dark or light veil, so the bands back in place are the
    wallpaper."""
    sy0, sy1, sx0, sx1 = p["screen"]
    win = p["win"]
    a = p["alpha"][win]
    sd = p["sd"][win]
    zs = zimg[sy0:sy1, sx0:sx1]
    near = nd.distance_transform_edt(~p["vis"][sy0:sy1, sx0:sx1]) <= FRINGE + 1
    # not where three bands meet: the wallpaper's corner pixels there mix all three
    kinds = sum(nd.maximum_filter((zs == q).astype(np.uint8), size=2 * JUNCTION + 1)
                for q in np.unique(zs))
    near &= kinds < 3
    zone = (sd > -FRINGE - 0.5) & (a < 0.9) & (zs < p["z"]) & near
    if not zone.any():
        return
    ys, xs = np.nonzero(zone)
    gy, gx = ys + sy0, xs + sx0
    beneath = np.zeros((len(ys), 3))
    for q in pieces:
        if q["z"] >= p["z"]:
            continue
        sel = zs[ys, xs] == q["z"]
        if sel.any():
            beneath[sel] = q["color"][gy[sel] - q["y0"], gx[sel] - q["x0"]]
    sel = zs[ys, xs] == -1
    if sel.any():
        beneath[sel] = image[gy[sel], gx[sel]]     # the ground (flat; its own colour)
    al = a[ys, xs][:, None]
    cp = p["color"][win][ys, xs]
    pix = image[gy, gx]
    target = (pix - al * cp) / (1 - al)
    diff = target - beneath
    # A dark veil only: the shadow the band casts on the one beneath. Never a
    # tint of another band's colour or a light line, which would show once
    # the band moves over something else.
    ink = np.zeros((len(ys), 3))
    beta = np.clip(((target - beneath) / (ink - beneath - 1e-6)).mean(1), 0, 0.7)
    beta = np.where(np.abs(diff).max(1) < NOISE, 0, beta)
    xcol = ink
    A = al[:, 0] + (1 - al[:, 0]) * beta
    col = (al * cp + ((1 - al[:, 0]) * beta)[:, None] * xcol) / np.maximum(A, 1e-6)[:, None]
    full_a = p["alpha"][win]
    full_c = p["color"][win]
    full_a[ys, xs] = A
    full_c[ys, xs] = col
