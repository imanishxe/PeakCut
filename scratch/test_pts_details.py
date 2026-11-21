import subprocess
import json
from pathlib import Path

src = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

# Let's inspect all video packets and all audio packets for the first 3 seconds of the file
cmd_v = [
    "ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_entries", "packet=pts_time,dts_time,flags",
    "-print_format", "json", str(src)
]
res_v = subprocess.run(cmd_v, capture_output=True, text=True)
v_pkts = json.loads(res_v.stdout).get("packets", [])

cmd_a = [
    "ffprobe", "-v", "error", "-select_streams", "a:0",
    "-show_entries", "packet=pts_time,dts_time,flags",
    "-print_format", "json", str(src)
]
res_a = subprocess.run(cmd_a, capture_output=True, text=True)
a_pkts = json.loads(res_a.stdout).get("packets", [])

print(f"Total video packets: {len(v_pkts)}, total audio packets: {len(a_pkts)}")
print("First 5 video packets:")
for p in v_pkts[:5]:
    print(" ", p)
print("First 5 audio packets:")
for p in a_pkts[:5]:
    print(" ", p)

# Find video packet with pts nearest to 0.0
v_zero = min(v_pkts, key=lambda p: abs(float(p.get("pts_time", 999))))
print("Video packet near 0.0:", v_zero)
