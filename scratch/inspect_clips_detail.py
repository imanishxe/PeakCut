import subprocess
import json
from pathlib import Path

p = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a\clips")

# Let's inspect the concat list for each clip if it was saved, or how src.ts was built
for c in ["clip001", "clip002", "clip003", "clip004"]:
    src = p / f"{c}.src.ts"
    mp4 = p / f"{c}.mp4"
    ass = p / f"{c}.ass"
    # Check start and end of video stream vs audio stream in mp4
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration,start_time",
        "-show_entries", "stream=index,codec_type,start_time,duration",
        "-print_format", "json", str(mp4)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"=== {c}.mp4 ===")
    data = json.loads(res.stdout)
    for s in data["streams"]:
        print(f"  Stream {s['codec_type']}: start_time={s.get('start_time')}, duration={s.get('duration')}")
