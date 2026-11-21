import subprocess
import json
from pathlib import Path

# Let's inspect job 20261117-211613-e2c30bf5c4
job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
job_json = job_p / "job.json"
with open(job_json) as f:
    job = json.load(f)

source_path = Path(job["source_path"])
print("Source path exists:", source_path.exists(), source_path)

c1 = job["clips"][0]
print("Clip 1:", c1["id"], "start:", c1["start"], "end:", c1["end"])
coarse = c1["start"] - 10.0 if c1["start"] > 15.0 else 0.0
print("coarse seek:", coarse)

# Run ffprobe on source video around coarse
cmd = [
    "ffprobe", "-v", "error", "-select_streams", "v:0",
    "-show_frames", "-show_entries", "frame=pkt_pts_time,key_frame",
    "-read_intervals", f"{coarse}%+5", "-print_format", "json", str(source_path)
]
res = subprocess.run(cmd, capture_output=True, text=True)
frames = json.loads(res.stdout).get("frames", [])
keyframes = [f for f in frames if f.get("key_frame") == 1]
print("Keyframes around coarse:")
for k in keyframes[:5]:
    print("  keyframe at pts:", k.get("pkt_pts_time"))
