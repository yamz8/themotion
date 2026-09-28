"""themotion: make motion for Omarchy themes from their wallpapers.

A wallpaper (wallpapers/<theme>/<wallpaper>/) is cut into parts once; a
motion (motions/<theme>/<wallpaper>/<motion>/) moves those parts.

usage:
  themotion split   <wallpaper|motion>   split the wallpaper into layers
  themotion preview <motion> [--open]    build the live preview page
  themotion render  <motion>             draw every frame
  themotion finish  <motion> [--install] encode the video (and copy it into the theme)
  themotion check   <video> <wallpaper> [--pattern NAME]
  themotion fit     <video> <wallpaper> [--out FILE] [--fade-in SECONDS]  re-finish a footage intro's ending (and optionally its start)
  themotion make    <motion> [--install] split, render, finish and check

options:
  --omarchy PATH    an Omarchy checkout (default: $OMARCHY_PATH)
  --set KEY=VALUE   override a pattern default for this run, e.g. --set length=6.5
"""
import argparse
import base64
import glob
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "engine")


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
        if os.path.splitext(self.cfg["file"])[0] != self.name:
            die(f"{os.path.relpath(self.dir)} must be named after its file, {self.cfg['file']}")
        self.omarchy = omarchy or os.environ.get("OMARCHY_PATH")
        self.build = os.path.join(ROOT, "build", self.theme, self.name)
        self.layers = os.path.join(self.build, "layers")

    @property
    def path(self):
        if not self.omarchy:
            die("set --omarchy or $OMARCHY_PATH to an Omarchy checkout")
        path = os.path.join(self.omarchy, "themes", self.theme, "backgrounds", self.cfg["file"])
        if not os.path.exists(path):
            die(f"wallpaper not found: {path}")
        return path


class Motion:
    """motions/<theme>/<wallpaper>/<motion>/: one way of moving a wallpaper's parts."""

    def __init__(self, path, omarchy=None, sets=None):
        self.dir = os.path.abspath(path.rstrip("/"))
        self.cfg = read_toml(os.path.join(self.dir, "scene.toml"), "motion")
        self.name = os.path.basename(self.dir)
        wallpaper = os.path.dirname(self.dir)
        theme = os.path.dirname(wallpaper)
        self.wallpaper = Wallpaper(
            os.path.join(ROOT, "wallpapers", os.path.basename(theme), os.path.basename(wallpaper)), omarchy)
        self.pattern_name = self.cfg.get("pattern", "omarchy-intro@1")
        self.pattern = load_pattern(self.pattern_name)
        # Requirements win over everything; defaults are overridable.
        self.spec = {**self.pattern["defaults"], **self.cfg.get("defaults", {}), **parse_sets(sets)}
        lo, hi = self.pattern["requires"]["length_range"]
        if not lo <= self.spec["length"] <= hi:
            die(f"length {self.spec['length']} s is outside the pattern's {lo}-{hi} s")
        if self.spec["settle"] + self.spec["handoff"] > self.spec["length"]:
            die("settle + handoff must end before the video does")
        self.build = os.path.join(self.wallpaper.build, self.name)

    @property
    def output(self):
        # Named after the wallpaper: that is how the theme finds its intro.
        return os.path.join(self.build, self.pattern["output"].format(name=self.wallpaper.name))


def load_target(path, omarchy=None, sets=None):
    if os.path.exists(os.path.join(path, "wallpaper.toml")):
        return Wallpaper(path, omarchy)
    return Motion(path, omarchy, sets)


# ---------- commands ----------

def cmd_split(wallpaper):
    sys.path.insert(0, ENGINE)
    import numpy as np
    from PIL import Image
    from split import LayerWriter

    spec = importlib.util.spec_from_file_location("wallpaper_split", os.path.join(wallpaper.dir, "split.py"))
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
    page = (page.replace("{{TITLE}}", motion.cfg["title"]).replace("{{SCRIPTS}}", inline)
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
    dest = os.path.join(wp.omarchy, "themes", wp.theme, motion.pattern["output"].format(name=wp.name))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(out, dest)
    # Omarchy pairs each intro with the hash of its wallpaper, so a changed
    # wallpaper never plays an intro that ends on the old picture.
    with open(wp.path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.splitext(dest)[0] + ".sha256", "w") as f:
        f.write(digest + "\n")
    print(f"installed: {dest}")


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
    ap.add_argument("command", choices=["split", "preview", "render", "finish", "check", "fit", "make"])
    ap.add_argument("target")
    ap.add_argument("wallpaper", nargs="?")
    ap.add_argument("--omarchy")
    ap.add_argument("--set", action="append", dest="sets")
    ap.add_argument("--pattern", default="omarchy-intro@1")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--fade-in", type=float, default=0.0, help="fit: also fade up from black over this many seconds")
    a = ap.parse_args()

    if a.command == "check":
        if not a.wallpaper:
            die("usage: themotion check <video> <wallpaper>")
        return cmd_check(a.target, a.wallpaper, a.pattern)

    if a.command == "fit":
        if not a.wallpaper:
            die("usage: themotion fit <video> <wallpaper> [--out FILE]")
        out = a.out or os.path.splitext(a.target)[0] + ".fit.mp4"
        return cmd_fit(a.target, a.wallpaper, a.pattern, out, a.sets, a.fade_in)

    target = load_target(a.target, a.omarchy, a.sets)
    if a.command == "split":
        return cmd_split(target if isinstance(target, Wallpaper) else target.wallpaper)
    if isinstance(target, Wallpaper):
        die(f"{a.command} takes a motion (motions/<theme>/<wallpaper>/<motion>/), not a wallpaper")
    motion = target
    if a.command == "preview":
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
