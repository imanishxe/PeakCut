import subprocess
import json
from pathlib import Path

# Inspect rendered clip01.mp4
p_rendered = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.mp4")
cmd = [
    "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration",
    "-show_entries", "format=start_time,duration", "-print_format", "json", str(p_rendered)
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Rendered clip01.mp4:", res.stdout)

# Check first packet PTS
cmd2 = [
    "ffprobe", "-v", "error", "-show_entries", "packet=codec_type,pts_time",
    "-read_intervals", "%+1", "-print_format", "json", str(p_rendered)
]
res2 = subprocess.run(cmd2, capture_output=True, text=True)
pkts = json.loads(res2.stdout).get("packets", [])
print("First packets in clip01.mp4:")
for pkt in pkts[:6]:
    print(" ", pkt)
