"""Tests for Enhanced 9:16 Framing & Visual Composition (Improvement 4).

Verifies:
1. LAYOUTS dictionary definitions including 'stacked'.
2. Geometry calculations for stacked and PIP layouts.
3. FFmpeg filter graph generation for Smart Facecam Stacked (1080x720 top + 1080x1200 bot).
4. Graceful fallback when facecam is absent.
5. End-to-end rendering producing valid 1080x1920 output with captions and hook.
6. Multi-format AI facecam detection parsing (regex & JSON).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-framing-")
sys.path.insert(0, ".")

from studio import brain, facecam, media, render, ai as _ai

fails = []

def check(n, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(n)

work = Path(tempfile.mkdtemp(prefix="pc-framing-work-"))

try:
    # 1. LAYOUTS dictionary
    check("stacked layout in LAYOUTS", "stacked" in render.LAYOUTS, True)
    check("gameplay layout in LAYOUTS", "gameplay" in render.LAYOUTS, True)
    check("blur layout in LAYOUTS", "blur" in render.LAYOUTS, True)
    check("crop layout in LAYOUTS", "crop" in render.LAYOUTS, True)

    # 2. Geometry calculations
    lay, fg_h, hook_y, cap_y = render.geometry(1920, 1080, "stacked")
    check("geometry stacked layout name", lay, "stacked")
    check("geometry stacked hook at seam", hook_y, 720)
    check("geometry stacked caption y", cap_y, 1500)

    # 3. Filter graph generation for stacked layout
    fc_box = [100, 80, 480, 360]
    filt = render._filter("stacked", 608, fc_box)
    check("stacked filter has top crop", "crop=480:360:100:80" in filt, True)
    check("stacked filter scales top to 1080x720", "scale=1080:720" in filt, True)
    check("stacked filter scales bot to 1080x1200", "scale=1080:1200" in filt, True)
    check("stacked filter uses vstack inputs=2", "[top][bot]vstack=inputs=2[v0]" in filt, True)

    # 4. Filter graph fallback when facecam is None
    filt_noface = render._filter("stacked", 608, None)
    check("stacked fallback has boxblur background", "boxblur=6:2" in filt_noface, True)
    check("stacked fallback does not use vstack", "vstack" not in filt_noface, True)

    # 5. Hook Y position calculation
    check("hook_y for stacked is at seam 720", render._hook_y("stacked", 300, fc_box), 720)
    check("hook_y for stacked without facecam is 720", render._hook_y("stacked", 300, None), 720)

    # 6. JSON & Text facecam response parsing in brain.py
    with patch.object(_ai, "see", return_value=('{"box": [0.05, 0.08, 0.25, 0.30]}', 0, 0)):
        res_json = brain.look_for_facecam(b"dummy")
        check("vision AI JSON parsing looked", res_json["looked"], True)
        check("vision AI JSON box coords", res_json["box"], (0.05, 0.08, 0.25, 0.30))

    with patch.object(_ai, "see", return_value=('CAM x=12% y=15% w=22% h=25%', 0, 0)):
        res_txt = brain.look_for_facecam(b"dummy")
        check("vision AI text regex parsed correctly", res_txt["box"], (0.12, 0.15, 0.22, 0.25))

    # 7. End-to-end Video Render Test
    test_src = work / "source.mp4"
    # Create 3-second 1920x1080 test video with audio
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
        "-t", "3", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", str(test_src)
    ], check=True)

    out_dir = work / "output"
    clip_def = {
        "id": "clip_test_stacked",
        "start": 0.5,
        "end": 2.5,
        "layout": "stacked",
        "facecam": [10, 10, 320, 240],
        "hook": "TEST HOOK TITLE",
        "style": "bounce",
        "captions": True,
    }
    words = [
        {"w": "Hello", "s": 0.6, "e": 1.0},
        {"w": "gamers", "s": 1.1, "e": 1.5},
        {"w": "welcome", "s": 1.6, "e": 2.2},
    ]

    res = render.render_clip(test_src, out_dir, "clip_test_stacked", clip_def, words, 1920, 1080)
    check("render_clip returned mp4 file", (out_dir / res["file"]).exists(), True)
    check("render_clip returned jpg cover", (out_dir / res["cover"]).exists(), True)
    check("render_clip returned srt subtitles", (out_dir / res["srt"]).exists(), True)
    check("render_clip returned ass subtitles", (out_dir / res["ass"]).exists(), True)

    meta = media.probe(out_dir / res["file"])
    check("output video width is 1080", meta["width"], 1080)
    check("output video height is 1920", meta["height"], 1920)

    # 8. Stacked rendering fallback when facecam is missing
    clip_noface = {
        "id": "clip_test_noface",
        "start": 0.5,
        "end": 2.5,
        "layout": "stacked",
        "facecam": None,
        "hook": "NO FACECAM FALLBACK",
        "style": "bounce",
        "captions": False,
    }
    res_noface = render.render_clip(test_src, out_dir, "clip_test_noface", clip_noface, [], 1920, 1080)
    check("render_clip fallback produced mp4", (out_dir / res_noface["file"]).exists(), True)
    meta_noface = media.probe(out_dir / res_noface["file"])
    check("fallback video width is 1080", meta_noface["width"], 1080)
    check("fallback video height is 1920", meta_noface["height"], 1920)

finally:
    shutil.rmtree(work, ignore_errors=True)

print("ALL PASSED" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
