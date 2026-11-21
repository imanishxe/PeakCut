import subprocess
import json
from pathlib import Path

src = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

# Let's extract frames and audio at specific PTS
# Check packet PTS of video around 8.0s and audio around 8.0s
cmd = [
    "ffprobe", "-v", "error", "-show_entries", "packet=codec_type,pts_time,dts_time",
    "-read_intervals", "7.9%8.2", "-print_format", "json", str(src)
]
res = subprocess.run(cmd, capture_output=True, text=True)
data = json.loads(res.stdout)
for pkt in data.get("packets", [])[:10]:
    print(pkt)
