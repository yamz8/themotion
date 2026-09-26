"""Check a video against a pattern's requirements.

Each requirement in the pattern's [requires] table has a check here, with its
thresholds in the pattern's [check] table. Prints one line per check and
returns True when all pass.
"""
import json
import subprocess

import numpy as np


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,pix_fmt,width,height,r_frame_rate,color_space,color_range:format=duration",
                          "-of", "json", video], check=True, capture_output=True, text=True).stdout
    j = json.loads(out)
    return j["streams"][0], float(j["format"]["duration"])


def frames(video, width, height, pix_fmt="gray", extra=()):
    """Decode to raw frames of the given pixel format as a uint8 array."""
    raw = subprocess.run(["ffmpeg", "-v", "error", *extra, "-i", video, "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"],
                         check=True, capture_output=True).stdout
    size = width * height * (1 if pix_fmt == "gray" else 3) // (1 if pix_fmt == "gray" else 2)
    return np.frombuffer(raw, np.uint8).reshape(-1, size)


def still_as_video_frame(wallpaper, width, height, pix_fmt):
    """The wallpaper encoded the way an intro's last frame is: scaled, BT.709 limited range.

    Decoded with Pillow (libwebp), like the renderer and Omarchy's shell;
    ffmpeg's own WebP decoder lands 1-2 levels off.
    """
    from PIL import Image
    img = Image.open(wallpaper).convert("RGB")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{img.width}x{img.height}",
                          "-i", "-", "-vf", f"scale={width}:{height}:flags=bicubic:out_color_matrix=bt709:out_range=tv,format={pix_fmt}",
                          "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"], input=img.tobytes(), check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8)


def check(video, wallpaper, pattern, spec):
    req, th = pattern["requires"], pattern["check"]
    stream, duration = probe(video)
    w, h = stream["width"], stream["height"]
    fps = eval(stream["r_frame_rate"])  # e.g. "30/1"
    results = []

    def report(name, ok, detail):
        results.append(ok)
        print(f"{'pass' if ok else 'FAIL'}  {name:<12} {detail}")

    lo, hi = req["length_range"]
    report("length", lo <= duration <= hi + 0.5 / fps, f"{duration:.2f} s (allowed {lo}-{hi} s)")
    report("codec", stream["codec_name"] == req["codec"] and stream["pix_fmt"] == req["pixel_format"],
           f"{stream['codec_name']} {stream['pix_fmt']}")
    from PIL import Image
    with Image.open(wallpaper) as im:
        ww, wh = im.size
    shape = abs(w / h - ww / wh) / (ww / wh)
    report("shape", shape <= th["shape_max_diff"], f"{w}x{h} for a {ww}x{wh} wallpaper ({shape * 100:.1f}% off its proportions)")
    tagged = stream.get("color_space", "unknown")
    report("color", tagged in ("unknown", "bt709"), f"colour matrix {tagged or 'untagged'} (Omarchy reads HD as BT.709)")

    # Start: near black, then a smooth fade (no single-frame jumps).
    head = frames(video, w, h, "gray", ["-t", str(spec["fade_in"] + 0.5)])
    # ffmpeg expands limited-range video to full-range gray, so 0 is black.
    luma = head.reshape(len(head), -1).mean(1).astype(np.float64)
    step = float(np.abs(np.diff(luma)).max()) if len(luma) > 1 else 0.0
    report("start", luma[0] <= th["first_frame_max_luma"], f"first frame luma {luma[0]:.1f} (max {th['first_frame_max_luma']})")
    report("fade", step <= th["fade_max_step"], f"largest step {step:.1f} per frame (max {th['fade_max_step']})")

    # End: the last frame matches the wallpaper encoded the same way.
    tail = frames(video, w, h, "yuv420p", ["-sseof", "-0.2"])[-1].astype(np.int16)
    still = still_as_video_frame(wallpaper, w, h, "yuv420p").astype(np.int16)
    diff = np.abs(tail - still)
    report("end", diff.mean() <= th["end_max_mean_diff"] and diff.max() <= th["end_max_diff"],
           f"last frame vs wallpaper: mean {diff.mean():.2f}, max {int(diff.max())} "
           f"(max {th['end_max_mean_diff']} / {th['end_max_diff']})")
    return all(results)
