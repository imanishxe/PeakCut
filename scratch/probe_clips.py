import subprocess
import json
from pathlib import Path

def probe(file_path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(file_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(res.stdout)

base_live = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a\clips")
for c in ["clip001.mp4", "clip002.mp4", "clip003.mp4", "clip004.mp4"]:
    p = base_live / c
    if p.exists():
        info = probe(p)
        v_stream = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
        a_stream = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), {})
        print(f"=== {c} ===")
        print("  Format duration:", info.get("format", {}).get("duration"), "start_time:", info.get("format", {}).get("start_time"))
        print("  Video:", v_stream.get("codec_name"), "start_time:", v_stream.get("start_time"), "duration:", v_stream.get("duration"), "nb_frames:", v_stream.get("nb_frames"))
        print("  Audio:", a_stream.get("codec_name"), "start_time:", a_stream.get("start_time"), "duration:", a_stream.get("duration"))
