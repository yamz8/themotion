"""themotion: make motion for Omarchy themes from their wallpapers.

usage:
  themotion split   <scene>             split the wallpaper into layers
  themotion preview <scene> [--open]    build the live preview page
  themotion render  <scene>             draw every frame
  themotion finish  <scene> [--install] encode the video (and copy it into the theme)
  themotion check   <video> <wallpaper> [--pattern NAME]
  themotion make    <scene> [--install] split, render, finish and check

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
LIB = os.path.join(ROOT, "lib")


def die(msg):
    print(f"themotion: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)


# ---------- patterns and scenes ----------

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


class Scene:
    def __init__(self, path, omarchy=None, sets=None):
        self.dir = os.path.abspath(path.rstrip("/"))
        cfg_path = os.path.join(self.dir, "scene.toml")
        if not os.path.exists(cfg_path):
            die(f"{path} has no scene.toml")
        with open(cfg_path, "rb") as f:
            self.cfg = tomllib.load(f)
        self.name = os.path.basename(self.dir)
        self.theme = self.cfg["theme"]
        self.pattern_name = self.cfg.get("pattern", "omarchy-intro@1")
        self.pattern = load_pattern(self.pattern_name)
        # Requirements win over everything; defaults are overridable.
        self.spec = {**self.pattern["defaults"], **self.cfg.get("defaults", {}), **parse_sets(sets)}
        lo, hi = self.pattern["requires"]["length_range"]
        if not lo <= self.spec["length"] <= hi:
            die(f"length {self.spec['length']} s is outside the pattern's {lo}-{hi} s")
        if self.spec["settle"] + self.spec["handoff"] > self.spec["length"]:
            die("settle + handoff must end before the video does")
        self.omarchy = omarchy or os.environ.get("OMARCHY_PATH")
        self.build = os.path.join(ROOT, "build", self.theme, self.name)
        self.layers = os.path.join(self.build, "layers")

    @property
    def wallpaper(self):
        if not self.omarchy:
            die("set --omarchy or $OMARCHY_PATH to an Omarchy checkout")
        path = os.path.join(self.omarchy, "themes", self.theme, "backgrounds", self.cfg["wallpaper"])
        if not os.path.exists(path):
            die(f"wallpaper not found: {path}")
        return path

    @property
    def output(self):
        return os.path.join(self.build, self.pattern["output"].format(name=self.name))


# ---------- commands ----------

def cmd_split(scene):
    sys.path.insert(0, LIB)
    import numpy as np
    from PIL import Image
    from split import LayerWriter

    spec = importlib.util.spec_from_file_location("scene_split", os.path.join(scene.dir, "split.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    image = np.asarray(Image.open(scene.wallpaper).convert("RGB")).astype(np.float64)
    shutil.rmtree(scene.layers, ignore_errors=True)
    writer = LayerWriter(scene.layers, image.shape[1], image.shape[0])
    mod.split(image, writer)
    writer.write()
    print(f"split {len(writer.meta['layers'])} layers into {os.path.relpath(scene.layers)}")


def data_uri(path):
    mime = {"png": "image/png", "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg"}[path.rsplit(".", 1)[1].lower()]
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def cmd_preview(scene, open_page=False):
    meta_path = os.path.join(scene.layers, "layers.json")
    if not os.path.exists(meta_path):
        cmd_split(scene)
    with open(meta_path) as f:
        meta = json.load(f)
    images = {l["name"]: data_uri(os.path.join(scene.layers, l["name"] + ".png")) for l in meta["layers"]}
    images["still"] = data_uri(scene.wallpaper)
    scripts = [os.path.join(LIB, "runtime.js"), os.path.join(LIB, "ease.js"),
               *sorted(glob.glob(os.path.join(LIB, "blocks", "*.js"))), os.path.join(scene.dir, "scene.js")]
    inline = "\n".join(f"<script>\n{open(p).read()}\n</script>" for p in scripts)
    config = {"pattern": scene.pattern_name, "spec": scene.spec, "meta": meta, "images": images}
    with open(os.path.join(LIB, "player.html")) as f:
        page = f.read()
    page = (page.replace("{{TITLE}}", scene.cfg["title"]).replace("{{SCRIPTS}}", inline)
            .replace("{{CONFIG}}", json.dumps(config)))
    out = os.path.join(scene.build, "preview.html")
    with open(out, "w") as f:
        f.write(page)
    print(f"preview: {os.path.relpath(out)}")
    if open_page:
        subprocess.Popen(["xdg-open", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def ensure_node():
    if not os.path.exists(os.path.join(ROOT, "node_modules", "playwright-core")):
        run(["npm", "install", "--silent", "--no-fund", "--no-audit"], cwd=ROOT)


def cmd_render(scene):
    page = cmd_preview(scene)
    ensure_node()
    run(["node", os.path.join(LIB, "render.mjs"), page, os.path.join(scene.build, "frames")])


def cmd_finish(scene, install=False):
    s, req = scene.spec, scene.pattern["requires"]
    frames = os.path.join(scene.build, "frames")
    if not glob.glob(os.path.join(frames, "*.png")):
        die("no frames yet; run `themotion render` first")
    out = scene.output
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # Encoded untagged, BT.709 limited range: what Omarchy's player assumes for HD.
    assert req["color"] == "bt709-tv" and req["codec"] == "h264"
    run(["ffmpeg", "-v", "error", "-y", "-framerate", str(s["fps"]), "-i", os.path.join(frames, "%04d.png"),
         "-vf", f"scale={s['width']}:{s['height']}:flags=bicubic:out_color_matrix=bt709:out_range=tv,format={req['pixel_format']}",
         "-an", "-c:v", "libx264", "-preset", "slow", "-crf", str(s["crf"]), "-profile:v", "high",
         "-pix_fmt", req["pixel_format"], "-movflags", "+faststart", out])
    print(f"video: {os.path.relpath(out)}")
    if install:
        cmd_install(scene, out)
    return out


def cmd_install(scene, out):
    dest = os.path.join(scene.omarchy, "themes", scene.theme, scene.pattern["output"].format(name=scene.name))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(out, dest)
    # Omarchy pairs each intro with the hash of its wallpaper, so a changed
    # wallpaper never plays an intro that ends on the old picture.
    with open(scene.wallpaper, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    with open(os.path.splitext(dest)[0] + ".sha256", "w") as f:
        f.write(digest + "\n")
    print(f"installed: {dest}")


def cmd_check(video, wallpaper, pattern_name, spec=None):
    sys.path.insert(0, LIB)
    from check import check
    pattern = load_pattern(pattern_name)
    ok = check(video, wallpaper, pattern, spec or pattern["defaults"])
    if not ok:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(prog="themotion", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["split", "preview", "render", "finish", "check", "make"])
    ap.add_argument("target")
    ap.add_argument("wallpaper", nargs="?")
    ap.add_argument("--omarchy")
    ap.add_argument("--set", action="append", dest="sets")
    ap.add_argument("--pattern", default="omarchy-intro@1")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()

    if a.command == "check":
        if not a.wallpaper:
            die("usage: themotion check <video> <wallpaper>")
        return cmd_check(a.target, a.wallpaper, a.pattern)

    scene = Scene(a.target, a.omarchy, a.sets)
    if a.command == "split":
        cmd_split(scene)
    elif a.command == "preview":
        cmd_preview(scene, a.open)
    elif a.command == "render":
        cmd_render(scene)
    elif a.command == "finish":
        cmd_finish(scene, a.install)
    elif a.command == "make":
        cmd_split(scene)
        cmd_render(scene)
        out = cmd_finish(scene)
        cmd_check(out, scene.wallpaper, scene.pattern_name, scene.spec)
        if a.install:
            cmd_install(scene, out)


if __name__ == "__main__":
    main()
