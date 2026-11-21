import subprocess
import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips")
for c in ["clip01.mp4", "clip02.mp4", "clip03.mp4"]:
    mp4 = job_p / c
    src = job_p / f"{c[:6]}.src.mp4"
    if src.exists():
        # Check first video pts and first audio pts in src
        cmd_v = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-read_intervals", "%+1", "-print_format", "json", str(src)]
        res_v = subprocess.run(cmd_v, capture_output=True, text=True)
        v_pkts = json.loads(res_v.stdout).get("packets", [])
        v_start = v_pkts[0].get("pts_time") if v_pkts else None

        cmd_a = ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "packet=pts_time", "-read_intervals", "%+1", "-print_format", "json", str(src)]
        res_a = subprocess.run(cmd_a, capture_output=True, text=True)
        a_pkts = json.loads(res_a.stdout).get("packets", [])
        a_start = a_pkts[0].get("pts_time") if a_pkts else None

        print(f"=== {src.name} ===")
        print(f"  First video pts: {v_start}")
        print(f"  First audio pts: {a_start}")
        if v_start and a_start:
            drift = float(a_start) - float(v_start)
            print(f"  --> PTS Difference between Video and Audio: {drift:+.3f} seconds!")
