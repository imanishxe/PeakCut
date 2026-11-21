import subprocess
import json
from pathlib import Path

def inspect_src_ts(ts_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration",
        "-print_format", "json", str(ts_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(f"TS: {ts_path.name}")
    try:
        data = json.loads(res.stdout)
        for s in data.get("streams", []):
            print(f"  {s.get('codec_type')}: start_time={s.get('start_time')}, duration={s.get('duration')}")
    except Exception as e:
        print("Error:", e)

job_dir = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a\clips")
for c in job_dir.glob("clip*.src.ts"):
    inspect_src_ts(c)
