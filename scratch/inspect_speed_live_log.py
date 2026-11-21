import subprocess
import json
from pathlib import Path

p = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a")

# Check ffmpeg.log in this session
errlog = p / "ffmpeg.log"
if errlog.exists():
    print("=== ffmpeg.log last 50 lines ===")
    lines = errlog.read_bytes().splitlines()
    for l in lines[-50:]:
        print(l.decode("utf-8", errors="replace"))

# Check job.json
with open(p / "job.json") as f:
    job = json.load(f)

for c in job["clips"]:
    print(f"Clip {c['id']}: start={c['start']}, end={c['end']}, off={c.get('src_offset')}")
