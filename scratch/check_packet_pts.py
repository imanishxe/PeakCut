import subprocess
import json
from pathlib import Path

def check_sync(mp4_path):
    # Check packet timestamps of audio vs video in mp4
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "packet=pts_time,dts_time,codec_type",
        "-read_intervals", "%+3", "-print_format", "json", str(mp4_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        packets = json.loads(res.stdout).get("packets", [])
    except Exception as e:
        print("Error parsing packets:", e)
        return
    first_v = next((p for p in packets if p.get("codec_type") == "video"), None)
    first_a = next((p for p in packets if p.get("codec_type") == "audio"), None)
    print(f"Path: {mp4_path.name}")
    print(f"  First video packet pts_time: {first_v.get('pts_time') if first_v else None}")
    print(f"  First audio packet pts_time: {first_a.get('pts_time') if first_a else None}")

job_dir = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a\clips")
for c in job_dir.glob("clip*.mp4"):
    check_sync(c)
