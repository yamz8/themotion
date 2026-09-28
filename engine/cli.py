"""themotion: make motion for Omarchy themes from their wallpapers.

A wallpaper (wallpapers/<theme>/<wallpaper>/) is cut into parts once; a
motion (motions/<theme>/<wallpaper>/<motion>/) moves those parts. A shared
motion (motions/shared/<motion>/) serves every wallpaper of one kind: pick
one with --wallpaper THEME/NAME, or all of them with --all.

usage:
  themotion split   <wallpaper|motion>   split the wallpaper into layers
  themotion preview <motion> [--open]    build the live preview page
  themotion render  <motion>             draw every frame
  themotion finish  <motion> [--install] encode the video (and copy it into the theme)
  themotion check   <video> <wallpaper> [--pattern NAME]
  themotion fit     <video> <wallpaper> [--out FILE] [--fade-in SECONDS]  re-finish a footage intro's ending (and optionally its start)
  themotion make    <motion> [--install] split, render, finish and check
  themotion look    <motion>             key frames on one sheet, and when the frame becomes the wallpaper
  themotion catalog [--json]             every Omarchy wallpaper, its kind and how far it has got

options:
  --omarchy PATH    an Omarchy checkout (default: $OMARCHY_PATH, then /usr/share/omarchy)
  --set KEY=VALUE   override a pattern default for this run, e.g. --set length=6.5
"""
import argparse
import base64
import glob
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")
IMAGE_TYPES = (".webp", ".jpg", ".jpeg", ".png")

# What kind of picture a wallpaper is decides how it can be brought to life.
KINDS = {
    "logo": "the Omarchy wordmark on a flat colour; one motion can serve every theme",
    "graphic": "flat shapes and line art; splits into shapes that move on their own",
    "pattern": "repeated cells, dots or lines; moves cell by cell",
    "scene": "an illustrated scene with depth; splits into depth bands and small objects",
    "dense": "a painting or photo; real footage fitted with `themotion fit`, or light effects",
}


def die(msg):
    print(f"themotion: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


# ---------- patterns, wallpapers and motions ----------

def load_pattern(name):
    path = os.path.join(ROOT, "patterns", f"{name}.toml")
    if not os.path.exists(path):
        die(f"unknown pattern {name} (see patterns/)")
    with open(path, "rb") as f:
        return tomllib.load(f)


def parse_sets(sets):
    out = {}
    for s in sets or []:
        k, _, v = s.partition("=")
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def omarchy_path(omarchy=None):
    for path in (omarchy, os.environ.get("OMARCHY_PATH"), "/usr/share/omarchy",
                 os.path.expanduser("~/.local/share/omarchy")):
        if path and os.path.isdir(os.path.join(path, "themes")):
            return path
    die("no Omarchy found; pass --omarchy PATH or set $OMARCHY_PATH")


def read_toml(path, what):
    if not os.path.exists(path):
        die(f"{os.path.relpath(os.path.dirname(path))} has no {os.path.basename(path)}; is it a {what}?")
    with open(path, "rb") as f:
        return tomllib.load(f)


class Wallpaper:
    """wallpapers/<theme>/<wallpaper>/: how one Omarchy wallpaper is cut into parts."""

    def __init__(self, path, omarchy=None):
        self.dir = os.path.abspath(path.rstrip("/"))
        self.cfg = read_toml(os.path.join(self.dir, "wallpaper.toml"), "wallpaper")
        self.name = os.path.basename(self.dir)
        self.theme = os.path.basename(os.path.dirname(self.dir))
        if self.cfg.get("kind") not in KINDS:
            die(f"{os.path.relpath(self.dir)}/wallpaper.toml: kind must be one of {', '.join(KINDS)}")
        self.omarchy = omarchy
        self.build = os.path.join(ROOT, "build", self.theme, self.name)
        self.layers = os.path.join(self.build, "layers")

    @property
    def path(self):
        # Found by name: Omarchy has shipped the same wallpaper as .jpg, .png and .webp.
        backgrounds = os.path.join(omarchy_path(self.omarchy), "themes", self.theme, "backgrounds")
        for ext in IMAGE_TYPES:
            path = os.path.join(backgrounds, self.name + ext)
            if os.path.exists(path):
                return path
        die(f"wallpaper not found: {os.path.join(backgrounds, self.name)}.*")

    @property
    def split_script(self):
        """The wallpaper's own split.py, or else the automatic split for its kind."""
        for path in (os.path.join(self.dir, "split.py"), os.path.join(ENGINE, "kinds", self.cfg["kind"] + ".py")):
            if os.path.exists(path):
                return path

    @property
    def motions(self):
        own = [os.path.basename(os.path.dirname(p)) for p in
               glob.glob(os.path.join(ROOT, "motions", self.theme, self.name, "*", "scene.toml"))]
        return sorted(own) + [name for name, kind in shared_motions() if kind == self.cfg["kind"]]

    @property
    def state(self):
        if self.motions:
            return "motion"
        if os.path.exists(os.path.join(self.dir, "split.py")):
            return "split"
        return "auto split" if self.split_script else "new"


def shared_motions():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "motions", "shared", "*", "scene.toml"))):
        with open(path, "rb") as f:
            out.append((os.path.basename(os.path.dirname(path)), tomllib.load(f).get("kind")))
    return out


def wallpapers_of(kind, omarchy=None):
    return [Wallpaper(os.path.dirname(p), omarchy)
            for p in sorted(glob.glob(os.path.join(ROOT, "wallpapers", "*", "*", "wallpaper.toml")))
            if read_toml(p, "wallpaper").get("kind") == kind]


class Motion:
    """motions/<theme>/<wallpaper>/<motion>/: one way of moving a wallpaper's parts."""

    def __init__(self, path, omarchy=None, sets=None, wallpaper=None):
        self.dir = os.path.abspath(path.rstrip("/"))
        self.cfg = read_toml(os.path.join(self.dir, "scene.toml"), "motion")
        self.name = os.path.basename(self.dir)
        self.shared = os.path.dirname(self.dir) == os.path.join(ROOT, "motions", "shared")
        if self.shared:
            if not wallpaper:
                die(f"{self.name} is shared by every {self.cfg.get('kind')} wallpaper; "
                    "pick one with --wallpaper THEME/NAME or use --all")
            self.wallpaper = Wallpaper(os.path.join(ROOT, "wallpapers", wallpaper), omarchy)
            if self.wallpaper.cfg["kind"] != self.cfg.get("kind"):
                die(f"{wallpaper} is a {self.wallpaper.cfg['kind']} wallpaper; {self.name} is for {self.cfg.get('kind')}")
        else:
            parent = os.path.dirname(self.dir)
            self.wallpaper = Wallpaper(os.path.join(ROOT, "wallpapers", os.path.basename(os.path.dirname(parent)),
                                                    os.path.basename(parent)), omarchy)
        self.pattern_name = self.cfg.get("pattern", "omarchy-intro@1")
        self.pattern = load_pattern(self.pattern_name)
        # Requirements win over everything; defaults are overridable.
        chosen = {**self.cfg.get("defaults", {}), **parse_sets(sets)}
        self.spec = {**self.pattern["defaults"], **chosen}
        if "fade_in" not in chosen and "fade_max_step" in self.pattern.get("check", {}):
            self.spec["fade_in"] = max(self.spec["fade_in"], self.fade_for_brightness())
        lo, hi = self.pattern["requires"]["length_range"]
        if not lo <= self.spec["length"] <= hi:
            die(f"length {self.spec['length']} s is outside the pattern's {lo}-{hi} s")
        if self.spec["settle"] + self.spec["handoff"] > self.spec["length"]:
            die("settle + handoff must end before the video does")
        self.build = os.path.join(self.wallpaper.build, self.name)
        # A wallpaper's title stands in for {wallpaper} in a shared motion's title.
        self.title = self.cfg["title"].replace("{wallpaper}", f"{self.wallpaper.theme}/{self.wallpaper.name}")

    def fade_for_brightness(self):
        """The shortest fade from black that keeps a bright wallpaper's
        per-frame step well under the check's limit (40% of margin)."""
        from PIL import Image
        with Image.open(self.wallpaper.path) as im:
            im.draft("L", (im.width // 8, im.height // 8))
            luma = sum(i * n for i, n in enumerate(im.convert("L").histogram())) / (im.width * im.height)
        limit = 0.6 * self.pattern["check"]["fade_max_step"] * self.spec["fps"]
        return math.ceil(luma / limit * 10) / 10

    @property
    def output(self):
        # Named after the wallpaper: that is how the theme finds its intro.
        return os.path.join(self.build, self.pattern["output"].format(name=self.wallpaper.name))


def load_targets(path, omarchy=None, sets=None, wallpaper=None, every=False):
    if os.path.exists(os.path.join(path, "wallpaper.toml")):
        return [Wallpaper(path, omarchy)]
    if every:
        kind = read_toml(os.path.join(path, "scene.toml"), "motion").get("kind")
        if not kind:
            die("--all is for shared motions (motions/shared/<motion>/)")
        return [Motion(path, omarchy, sets, f"{w.theme}/{w.name}") for w in wallpapers_of(kind, omarchy)]
    return [Motion(path, omarchy, sets, wallpaper)]


# ---------- commands ----------

def cmd_split(wallpaper):
    sys.path.insert(0, ENGINE)
    import numpy as np
    from PIL import Image
    from split import LayerWriter

    if not wallpaper.split_script:
        die(f"{os.path.relpath(wallpaper.dir)} has no split.py yet, and {wallpaper.cfg['kind']} wallpapers "
            "have no automatic split")
    spec = importlib.util.spec_from_file_location("wallpaper_split", wallpaper.split_script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    image = np.asarray(Image.open(wallpaper.path).convert("RGB")).astype(np.float64)
    shutil.rmtree(wallpaper.layers, ignore_errors=True)
    writer = LayerWriter(wallpaper.layers, image.shape[1], image.shape[0])
    mod.split(image, writer)
    writer.write()
    print(f"split {len(writer.meta['layers'])} layers into {os.path.relpath(wallpaper.layers)}")


def data_uri(path):
    mime = {"png": "image/png", "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}[path.rsplit(".", 1)[1].lower()]
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def cmd_preview(motion, open_page=False):
    layers = motion.wallpaper.layers
    meta_path = os.path.join(layers, "layers.json")
    if not os.path.exists(meta_path):
        cmd_split(motion.wallpaper)
    with open(meta_path) as f:
        meta = json.load(f)
    images = {l["name"]: data_uri(os.path.join(layers, l["name"] + ".png")) for l in meta["layers"]}
    images["still"] = data_uri(motion.wallpaper.path)
    scripts = [os.path.join(ENGINE, "runtime.js"), os.path.join(ENGINE, "ease.js"),
               *sorted(glob.glob(os.path.join(ENGINE, "blocks", "*.js"))), os.path.join(motion.dir, "scene.js")]
    inline = "\n".join(f"<script>\n{open(p).read()}\n</script>" for p in scripts)
    config = {"pattern": motion.pattern_name, "spec": motion.spec, "meta": meta, "images": images}
    with open(os.path.join(ENGINE, "player.html")) as f:
        page = f.read()
    page = (page.replace("{{TITLE}}", motion.title).replace("{{SCRIPTS}}", inline)
            .replace("{{CONFIG}}", json.dumps(config)))
    os.makedirs(motion.build, exist_ok=True)
    out = os.path.join(motion.build, "preview.html")
    with open(out, "w") as f:
        f.write(page)
    print(f"preview: {os.path.relpath(out)}")
    if open_page:
        subprocess.Popen(["xdg-open", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def ensure_node():
    if not os.path.exists(os.path.join(ROOT, "node_modules", "playwright-core")):
        run(["npm", "install", "--silent", "--no-fund", "--no-audit"], cwd=ROOT)


def cmd_render(motion):
    page = cmd_preview(motion)
    ensure_node()
    run(["node", os.path.join(ENGINE, "render.mjs"), page, os.path.join(motion.build, "frames"),
         str(motion.spec["render_scale"])])


def cmd_look(motion, every=0.5):
    """Render small frames, put key frames on one sheet, and measure how far
    every frame is from the wallpaper, so a motion can be judged at a glance."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    page = cmd_preview(motion)
    ensure_node()
    look = os.path.join(motion.build, "look")
    frames, still_png = os.path.join(look, "frames"), os.path.join(look, "still.png")
    W = json.load(open(os.path.join(motion.wallpaper.layers, "layers.json")))["width"]
    run(["node", os.path.join(ENGINE, "render.mjs"), page, frames, str(min(1.0, 640 / W)), still_png],
        stdout=subprocess.DEVNULL)
    still = np.asarray(Image.open(still_png).convert("RGB")).astype(float)
    paths = sorted(glob.glob(os.path.join(frames, "*.png")))
    fps = motion.spec["fps"]
    diff, worst = [], []
    for p in paths:
        d = np.abs(np.asarray(Image.open(p).convert("RGB")).astype(float) - still)
        diff.append(float(d.mean()))
        worst.append(float(d.max()))
    # At the wallpaper once no pixel is more than 2 levels off: blending the
    # still over an identical frame alone can round by a level.
    exact = next((i for i in range(len(worst)) if max(worst[i:]) <= 2), None)

    keys = [i for i in range(0, len(paths), round(every * fps))]
    tw, th = Image.open(paths[0]).size
    cols = 4
    font = ImageFont.load_default(size=max(12, th // 16))
    sheet = Image.new("RGB", (cols * tw, -(-len(keys) // cols) * (th + th // 8)), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    for n, i in enumerate(keys):
        x, y = (n % cols) * tw, (n // cols) * (th + th // 8)
        sheet.paste(Image.open(paths[i]), (x, y))
        draw.text((x + 6, y + th + 2), f"{i / fps:.1f} s   off by {diff[i]:.2f}", fill=(235, 235, 235), font=font)
    out = os.path.join(motion.build, "look.png")
    sheet.save(out)
    print(f"look: {os.path.relpath(out)}")
    when = f"{exact / fps:.2f} s" if exact is not None else "never"
    print(f"the frame is the wallpaper from {when} (settle {motion.spec['settle']} s)")
    return out


def output_size(motion):
    """The wallpaper's proportions at the smallest size covering the pattern's
    width x height, rounded to even numbers for yuv420p."""
    with open(os.path.join(motion.wallpaper.layers, "layers.json")) as f:
        meta = json.load(f)
    W, H = meta["width"], meta["height"]
    k = max(motion.spec["width"] / W, motion.spec["height"] / H)
    return 2 * round(W * k / 2), 2 * round(H * k / 2)


def cmd_finish(motion, install=False):
    s, req = motion.spec, motion.pattern["requires"]
    frames = os.path.join(motion.build, "frames")
    if not glob.glob(os.path.join(frames, "*.png")):
        die("no frames yet; run `themotion render` first")
    out = motion.output
    os.makedirs(os.path.dirname(out), exist_ok=True)
    frames_total = len(glob.glob(os.path.join(frames, "*.png")))
    w, h = output_size(motion)
    settled = min(frames_total - 1, int(s["settle"] * s["fps"]))
    # Encoded untagged, BT.709 limited range: what Omarchy's player assumes for HD.
    assert req["color"] == "bt709-tv" and req["codec"] == "h264"
    run(["ffmpeg", "-v", "error", "-y", "-framerate", str(s["fps"]), "-i", os.path.join(frames, "%04d.png"),
         "-vf", f"scale={w}:{h}:flags=bicubic:out_color_matrix=bt709:out_range=tv,format={req['pixel_format']}",
         "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(s["crf"]),
         "-x264-params", f"zones={settled}," + str(frames_total - 1) + f",q={s['settled_q']}", "-profile:v", "high",
         "-pix_fmt", req["pixel_format"], "-movflags", "+faststart", out])
    print(f"video: {os.path.relpath(out)}")
    if install:
        cmd_install(motion, out)
    return out


def cmd_install(motion, out):
    wp = motion.wallpaper
    dest = os.path.join(omarchy_path(wp.omarchy), "themes", wp.theme, motion.pattern["output"].format(name=wp.name))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(out, dest)
    # Omarchy pairs each intro with the hash of its wallpaper, so a changed
    # wallpaper never plays an intro that ends on the old picture.
    with open(wp.path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.splitext(dest)[0] + ".sha256", "w") as f:
        f.write(digest + "\n")
    print(f"installed: {dest}")


def cmd_catalog(omarchy=None, as_json=False):
    from PIL import Image
    root = omarchy_path(omarchy)
    rows, unlisted = [], []
    for f in sorted(glob.glob(os.path.join(root, "themes", "*", "backgrounds", "*"))):
        if os.path.splitext(f)[1].lower() not in IMAGE_TYPES:
            continue
        theme, name = f.split(os.sep)[-3], os.path.splitext(os.path.basename(f))[0]
        d = os.path.join(ROOT, "wallpapers", theme, name)
        if not os.path.exists(os.path.join(d, "wallpaper.toml")):
            unlisted.append(f"{theme}/{name}")
            continue
        wp = Wallpaper(d, root)
        with Image.open(f) as im:
            w, h = im.size
        rows.append({"wallpaper": f"{theme}/{name}", "kind": wp.cfg["kind"], "state": wp.state,
                     "motions": wp.motions, "size": [w, h], "about": wp.cfg["about"]})
    if as_json:
        print(json.dumps({"omarchy": root, "wallpapers": rows, "unlisted": unlisted}, indent=2))
        return
    width = max(len(r["wallpaper"]) for r in rows)
    for r in rows:
        state = ", ".join(r["motions"]) if r["motions"] else r["state"]
        print(f"{r['wallpaper']:<{width}}  {r['kind']:<8} {state:<16} {r['size'][0]}x{r['size'][1]}")
    print()
    for kind, meaning in KINDS.items():
        of = [r for r in rows if r["kind"] == kind]
        done = sum(1 for r in of if r["state"] == "motion")
        print(f"{kind:<8} {len(of):>3} wallpapers, {done:>2} with a motion: {meaning}")
    print(f"\n{sum(1 for r in rows if r['state'] == 'motion')} of {len(rows)} wallpapers have a motion ({root})")
    for u in unlisted:
        print(f"not in the catalog yet: {u} (add wallpapers/{u}/wallpaper.toml)")


def cmd_check(video, wallpaper, pattern_name, spec=None):
    sys.path.insert(0, ENGINE)
    from check import check
    pattern = load_pattern(pattern_name)
    ok = check(video, wallpaper, pattern, spec or pattern["defaults"])
    if not ok:
        sys.exit(1)


def cmd_fit(video, wallpaper, pattern_name, out, sets, fade_in=0.0):
    sys.path.insert(0, ENGINE)
    from fit import fit
    pattern = load_pattern(pattern_name)
    spec = {**pattern["defaults"], **parse_sets(sets)}
    n = fit(video, wallpaper, out, spec, fade_in=fade_in)
    print(f"fitted {n} frames: {os.path.relpath(out)}")
    cmd_check(out, wallpaper, pattern_name, spec)


def main():
    ap = argparse.ArgumentParser(prog="themotion", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["split", "preview", "render", "finish", "check", "fit", "make", "look",
                                        "catalog"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("wallpaper", nargs="?")
    ap.add_argument("--omarchy")
    ap.add_argument("--set", action="append", dest="sets")
    ap.add_argument("--pattern", default="omarchy-intro@1")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--fade-in", type=float, default=0.0, help="fit: also fade up from black over this many seconds")
    ap.add_argument("--json", action="store_true", help="catalog: print JSON")
    ap.add_argument("--wallpaper", dest="for_wallpaper", help="the wallpaper (THEME/NAME) a shared motion is for")
    ap.add_argument("--all", action="store_true", help="run a shared motion for every wallpaper of its kind")
    a = ap.parse_args()

    if a.command == "catalog":
        return cmd_catalog(a.omarchy, a.json)
    if not a.target:
        die(f"{a.command} needs a target; see themotion --help")

    if a.command == "check":
        if not a.wallpaper:
            die("usage: themotion check <video> <wallpaper>")
        return cmd_check(a.target, a.wallpaper, a.pattern)

    if a.command == "fit":
        if not a.wallpaper:
            die("usage: themotion fit <video> <wallpaper> [--out FILE]")
        out = a.out or os.path.splitext(a.target)[0] + ".fit.mp4"
        return cmd_fit(a.target, a.wallpaper, a.pattern, out, a.sets, a.fade_in)

    for target in load_targets(a.target, a.omarchy, a.sets, a.for_wallpaper, a.all):
        run_command(a, target)


def run_command(a, target):
    if a.command == "split":
        return cmd_split(target if isinstance(target, Wallpaper) else target.wallpaper)
    if isinstance(target, Wallpaper):
        die(f"{a.command} takes a motion (motions/<theme>/<wallpaper>/<motion>/), not a wallpaper")
    motion = target
    if a.command == "look":
        cmd_look(motion)
    elif a.command == "preview":
        cmd_preview(motion, a.open)
    elif a.command == "render":
        cmd_render(motion)
    elif a.command == "finish":
        cmd_finish(motion, a.install)
    elif a.command == "make":
        cmd_split(motion.wallpaper)
        cmd_render(motion)
        out = cmd_finish(motion)
        cmd_check(out, motion.wallpaper.path, motion.pattern_name, motion.spec)
        if a.install:
            cmd_install(motion, out)


if __name__ == "__main__":
    main()
