import subprocess
import json
from pathlib import Path

p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

cmd = [
    "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration",
    "-show_entries", "format=start_time,duration", "-print_format", "json", str(p)
]
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)

# Check first 5 packets of audio and video
cmd2 = [
    "ffprobe", "-v", "error", "-show_entries", "packet=codec_type,pts_time,dts_time",
    "-read_intervals", "%+2", "-print_format", "json", str(p)
]
res2 = subprocess.run(cmd2, capture_output=True, text=True)
data = json.loads(res2.stdout)
packets = data.get("packets", [])
v_pkts = [pkt for pkt in packets if pkt.get("codec_type") == "video"][:3]
a_pkts = [pkt for pkt in packets if pkt.get("codec_type") == "audio"][:3]
print("First video packets:", v_pkts)
print("First audio packets:", a_pkts)
