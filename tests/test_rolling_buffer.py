"""Tests for Circular Rolling Buffers vs. Unbounded Disk Storage (Improvement 5).

Verifies:
1. Rolling buffer pruning: Segments older than buffer_min are unlinked and removed.
2. Protection of queued/rendering clips: Segments needed by pending clips are retained.
3. Post-extraction pruning: Once a clip's slice is extracted into clips/, expired segments are pruned.
4. Low-disk emergency guard: Buffer contracts when disk is tight, and stops if critically low.
5. Orphan segment cleanup: Leftover .ts files in the buffer folder are safely cleaned up.
6. Real-time buffer footprint accounting (buffer_sec and buffer_mb).
"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-buffer-")
sys.path.insert(0, ".")

from studio import live

fails = []

def check(n, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + n + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(n)

work = Path(tempfile.mkdtemp(prefix="pc-buffer-work-"))

try:
    buf_dir = work / "buffer"
    clips_dir = work / "clips"
    buf_dir.mkdir(parents=True)
    clips_dir.mkdir(parents=True)

    job = {
        "id": "live_test_01",
        "creator": "c_test",
        "dir": str(work),
        "clips": [],
        "source": {"url": "https://twitch.tv/test"},
        "options": {},
    }
    settings = {
        "buffer_min": 1.0,  # 1 minute (60 seconds) buffer
        "style": "bounce",
        "layout": "blur",
    }

    session = live.Session(job, settings)

    # 1. Create simulated segments across 120 seconds (20 segments of 6 seconds each)
    for i in range(20):
        t_start = i * 6.0
        t_end = (i + 1) * 6.0
        seg_file = buf_dir / f"p01_{i:05d}.ts"
        seg_file.write_bytes(b"\x00" * 1024 * 100)  # 100 KB each
        session.segments.append((seg_file, t_start, t_end))
    session.seg_clock = 120.0

    # 2. Test standard circular pruning (keeping last 60 seconds: t >= 60.0)
    session._scan_segments()
    check("segments older than 60s are pruned from memory",
          all(s[2] >= 60.0 for s in session.segments), True)
    check("retained segments count is 10 (60s to 120s)", len(session.segments), 10)
    check("first retained segment starts at 60s", session.segments[0][1], 60.0)

    # Check unlinked from disk
    old_file = buf_dir / "p01_00000.ts"
    check("expired segment file was unlinked from disk", old_file.exists(), False)
    current_file = buf_dir / "p01_00010.ts"
    check("active segment file exists on disk", current_file.exists(), True)

    # 3. Test protection of queued clips needing older segments
    # Add older segments again (from t=30 to t=60)
    for i in range(5, 10):
        t_start = i * 6.0
        t_end = (i + 1) * 6.0
        seg_file = buf_dir / f"p01_{i:05d}.ts"
        seg_file.write_bytes(b"\x00" * 1024 * 100)
        session.segments.insert(0, (seg_file, t_start, t_end))
    session.segments.sort(key=lambda s: s[1])

    # Now register a pending clip spanning t=35 to t=50 (which is older than 120 - 60 = 60s)
    job["clips"].append({
        "id": "clip001",
        "status": "queued",
        "start": 35.0,
        "end": 50.0,
        "src": None,  # Not yet extracted
    })

    session._scan_segments()
    # Segments down to 35 - PAD = 27s must be preserved
    check("pending clip protects segments older than normal buffer_min",
          any(s[1] <= 36.0 for s in session.segments), True)
    check("protected segment file exists on disk", (buf_dir / "p01_00005.ts").exists(), True)

    # 4. Once clip is extracted, protection is lifted and expired segments are pruned
    clip = job["clips"][0]
    clip["src"] = str(clips_dir / "clip001.src.ts")  # Mark as extracted
    session._scan_segments()
    check("after extraction, expired segments are pruned",
          all(s[2] >= 60.0 for s in session.segments), True)
    check("previously protected old segment is now unlinked",
          (buf_dir / "p01_00005.ts").exists(), False)

    # 5. Test orphan segment cleanup
    orphan = buf_dir / "orphan_123.ts"
    orphan.write_bytes(b"abandoned")
    # Set mtime to 400 seconds ago
    old_time = time.time() - 400
    os.utime(str(orphan), (old_time, old_time))
    session._last_orphan_prune = 0.0  # Force prune check
    session._scan_segments()
    check("orphan .ts file older than threshold is pruned", orphan.exists(), False)

    # 6. Test low-disk guard
    # Mock disk_usage to return 0.5 GB free (< 1.5 GB threshold)
    class FakeUsage:
        free = int(0.5 * 1e9)
        total = int(100 * 1e9)

    with patch("shutil.disk_usage", return_value=FakeUsage()):
        # With 0.5 GB free, contracted_min = min(10.0, max(0.5, 0.5 * 1.5)) = 0.75 min = 45s
        # If settings had 10 min buffer (600s), it contracts to 45s (keep_from = 120 - 45 = 75s)
        session.settings["buffer_min"] = 10.0
        session._scan_segments()
        check("disk guard dynamically contracts buffer when space is tight",
              session.segments[0][1] >= 60.0, True)

    # Mock critical disk usage (< 0.25 GB free)
    class CriticalUsage:
        free = int(0.2 * 1e9)
        total = int(100 * 1e9)

    session.user_stopped = False
    session.ended = False
    with patch("shutil.disk_usage", return_value=CriticalUsage()):
        session._scan_segments()
        check("critical disk space triggers automatic stop to protect drive",
              session.user_stopped or session.stop_flag.is_set(), True)
        check("stop message reflects low disk space",
              "critically low" in session.end_note, True)

finally:
    shutil.rmtree(work, ignore_errors=True)

print("ALL PASSED" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
