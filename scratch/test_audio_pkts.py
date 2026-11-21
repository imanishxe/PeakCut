import subprocess
import json
from pathlib import Path

p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

cmd2 = [
    "ffprobe", "-v", "error", "-show_entries", "packet=codec_type,pts_time,dts_time",
    "-select_streams", "a:0",
    "-read_intervals", "%+5", "-print_format", "json", str(p)
]
res2 = subprocess.run(cmd2, capture_output=True, text=True)
data = json.loads(res2.stdout)
packets = data.get("packets", [])
print("First audio packets count:", len(packets))
for pkt in packets[:5]:
    print("  audio pkt:", pkt)
