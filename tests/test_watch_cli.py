"""Tests for Headless CLI / Watcher Mode (Improvement 6).

Verifies:
1. Argument parsing (--min, --layout, --style, --ai-hooks, --out, etc.).
2. Channel URL normalization for Twitch names, URLs, and platforms.
3. Creator workspace generation and settings synchronization.
4. Clip export mechanism to custom output directory upon clip generation.
5. Watcher lifecycle and graceful shutdown via stop event.
"""
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-watch-")
sys.path.insert(0, ".")

from studio import creators, jobs, watch

fails = []

def check(n, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(n)

work = Path(tempfile.mkdtemp(prefix="pc-watch-work-"))

try:
    # 1. Test channel normalization
    check("bare username to twitch url", watch.normalize_channel("tenz"), "https://www.twitch.tv/tenz")
    check("@username to twitch url", watch.normalize_channel("@shroud"), "https://www.twitch.tv/shroud")
    check("full twitch url preserved", watch.normalize_channel("https://twitch.tv/tbone_gaming"), "https://twitch.tv/tbone_gaming")
    check("kick url preserved", watch.normalize_channel("https://kick.com/xqc"), "https://kick.com/xqc")

    # 2. Test argument parsing
    args = watch.parse_args(["tenz", "--min", "8", "--layout", "stacked", "--style", "hype",
                             "--no-captions", "--no-ai-hooks", "--buffer-min", "30", "--out", str(work / "export")])
    check("arg channel parsed", args.channel, "tenz")
    check("arg min_users parsed", args.min_users, 8)
    check("arg layout parsed", args.layout, "stacked")
    check("arg style parsed", args.style, "hype")
    check("arg captions disabled", args.captions, False)
    check("arg ai_hooks disabled", args.ai_hooks, False)
    check("arg buffer_min parsed", args.buffer_min, 30)
    check("arg out_dir parsed", args.out_dir, str(work / "export"))

    # 3. Test watcher setup & clip export callback
    export_dir = work / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    stop_event = threading.Event()

    # Create dummy clip source in a mock job dir
    mock_job_dir = work / "job_mock"
    mock_clips_dir = mock_job_dir / "clips"
    mock_clips_dir.mkdir(parents=True)

    dummy_mp4 = mock_clips_dir / "clip001.mp4"
    dummy_mp4.write_bytes(b"dummy_mp4_bytes")
    dummy_srt = mock_clips_dir / "clip001.srt"
    dummy_srt.write_text("1\n00:00:00,000 --> 00:00:05,000\nHello\n", encoding="utf-8")
    dummy_jpg = mock_clips_dir / "clip001.jpg"
    dummy_jpg.write_bytes(b"dummy_jpg_bytes")

    # Mock live.resolve to raise NotLive after setting stop_event
    with patch("studio.live.resolve", side_effect=lambda url: stop_event.set()):
        # Run watcher with a stop event that triggers immediately
        stop_event.set()
        res = watch.run_watcher(args, stop_event=stop_event)
        check("run_watcher completes successfully", res, 0)

    # 4. Check creator was created and synchronized
    url = watch.normalize_channel("tenz")
    c = next((x for x in creators.all_creators() if x.get("channel") == url), None)
    check("creator profile created for watched channel", bool(c), True)
    check("creator layout set to stacked", c.get("layout"), "stacked")
    check("creator chat_spike_min_users set", c.get("chat_spike_min_users"), 8)
    check("creator ai_hooks set", c.get("ai_hooks"), False)
    check("creator buffer_min set", c.get("buffer_min"), 30)

    # 5. Check clip export callback triggered by on_clip_ready
    mock_clip = {
        "id": "clip001",
        "file": "clip001.mp4",
        "srt": "clip001.srt",
        "ass": "clip001.ass",
        "cover": "clip001.jpg",
        "start": 10.0,
        "end": 25.0,
        "score": 92,
        "title": "INSANE CLUTCH",
    }
    mock_job = {
        "id": "job_01",
        "creator": c["id"],
        "dir": str(mock_job_dir),
    }

    # Trigger callbacks registered by watch
    for cb in jobs.on_clip_ready:
        cb(mock_job, mock_clip)

    check("exported mp4 exists in export dir", (export_dir / "clip001.mp4").is_file(), True)
    check("exported srt exists in export dir", (export_dir / "clip001.srt").is_file(), True)
    check("exported jpg exists in export dir", (export_dir / "clip001.jpg").is_file(), True)

finally:
    shutil.rmtree(work, ignore_errors=True)

print("ALL PASSED" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
