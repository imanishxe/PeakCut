import subprocess
import json
from pathlib import Path

p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

# Let's decode 1 frame with trim=start=8.0
cmd_v = [
    "ffmpeg", "-v", "error", "-i", str(p),
    "-vf", "trim=start=8.0:end=8.1,showinfo",
    "-f", "null", "-"
]
res_v = subprocess.run(cmd_v, capture_output=True, text=True)
print("Video showinfo:")
for l in res_v.stderr.splitlines()[:5]:
    print(" ", l)

# Let's decode audio with atrim=start=8.0
cmd_a = [
    "ffmpeg", "-v", "error", "-i", str(p),
    "-af", "atrim=start=8.0:end=8.1,ashowinfo",
    "-f", "null", "-"
]
res_a = subprocess.run(cmd_a, capture_output=True, text=True)
print("Audio ashowinfo:")
for l in res_a.stderr.splitlines()[:5]:
    print(" ", l)
