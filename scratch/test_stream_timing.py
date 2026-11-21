import subprocess
import json
from pathlib import Path

src = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

# Check format and streams in detail
cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-print_format", "json", str(src)]
res = subprocess.run(cmd, capture_output=True, text=True)
data = json.loads(res.stdout)
for s in data["streams"]:
    print(f"Stream {s['codec_type']}:")
    print(f"  start_time: {s.get('start_time')}, start_pts: {s.get('start_pts')}, time_base: {s.get('time_base')}")
    print(f"  duration: {s.get('duration')}")
