"""Re-finish an existing intro's ending onto the exact wallpaper.

Footage intros made elsewhere often end on a copy of the wallpaper that is a
level or two off (a different WebP decoder, a lossy encode). This keeps every
frame as it is and only blends the last `blend` seconds into the wallpaper,
encoded exactly as `themotion check` expects, then holds it. It works on the
video's own YUV frames, so nothing before the blend is converted or touched
beyond a single re-encode.
"""
import subprocess

import numpy as np

from check import probe, still_as_video_frame


def fit(video, wallpaper, out, spec, blend=0.4, hold=0.1, fade_in=0.0):
    stream, duration = probe(video)
    w, h = stream["width"], stream["height"]
    num, den = (int(v) for v in stream["r_frame_rate"].split("/"))
    fps = num / den
    size = w * h * 3 // 2
    still = still_as_video_frame(wallpaper, w, h, "yuv420p").astype(np.float32)

    frames = round(duration * fps)
    # An optional fade up from black over the first `fade_in` seconds, for
    # footage that opens above black: black is Y 16, U and V 128.
    black = np.concatenate([np.full(w * h, 16, np.float32), np.full(w * h // 2, 128, np.float32)])
    fade_frames = round(fade_in * fps)
    ramp_from = frames - round((blend + hold) * fps)
    ramp_to = frames - round(hold * fps)
    settled = max(0, frames - round(max(blend + hold, 0.5) * fps))

    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                           stdout=subprocess.PIPE)
    # The frames are already BT.709 limited range: tag the input as such so
    # ffmpeg passes them through instead of converting them for the output.
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{w}x{h}",
                            "-framerate", stream["r_frame_rate"], "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-color_range", "tv", "-i", "-", "-an", "-c:v", "libx264", "-preset", "slow",
                            "-crf", str(spec["crf"]), "-x264-params", f"zones={settled},{frames - 1},q={spec['settled_q']}",
                            "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    i = 0
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        frame = np.frombuffer(buf, np.uint8)
        if i < fade_frames:
            k = i / fade_frames  # linear, so no frame jumps more than the rest
            frame = np.round(black * (1 - k) + frame * k).astype(np.uint8)
        if i >= ramp_from:
            k = 1.0 if i >= ramp_to else (i - ramp_from + 1) / (ramp_to - ramp_from + 1)
            # Smoothstep, so the blend neither starts nor stops abruptly.
            k = k * k * (3 - 2 * k)
            frame = np.round(frame * (1 - k) + still * k).astype(np.uint8)
        enc.stdin.write(frame.tobytes())
        i += 1
    enc.stdin.close()
    dec.wait()
    if enc.wait() != 0 or dec.returncode != 0:
        raise RuntimeError("ffmpeg failed while re-finishing the video")
    return i
