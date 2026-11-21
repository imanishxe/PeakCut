import subprocess
import json
from pathlib import Path

def analyze_sync(mp4_file):
    # Check audio vs video duration and frame timestamps
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration,nb_frames,r_frame_rate",
        "-print_format", "json", str(mp4_file)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(res.stdout)
    print(f"=== {mp4_file.name} ===")
    for s in info.get("streams", []):
        print(f"  Stream {s.get('codec_type')}: start={s.get('start_time')}, dur={s.get('duration')}, frames={s.get('nb_frames')}, fps={s.get('r_frame_rate')}")

d = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a\clips")
for c in ["clip001.mp4", "clip002.mp4", "clip003.mp4", "clip004.mp4"]:
    analyze_sync(d / c)
