import subprocess
from pathlib import Path

p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

cmd_v = [
    "ffmpeg", "-v", "info", "-i", str(p),
    "-vf", "trim=start=8.0:end=8.1,showinfo",
    "-f", "null", "-"
]
res_v = subprocess.run(cmd_v, capture_output=True, text=True)
print("Video showinfo:")
for l in [line for line in res_v.stderr.splitlines() if "showinfo" in line][:5]:
    print(" ", l)

cmd_a = [
    "ffmpeg", "-v", "info", "-i", str(p),
    "-af", "atrim=start=8.0:end=8.1,ashowinfo",
    "-f", "null", "-"
]
res_a = subprocess.run(cmd_a, capture_output=True, text=True)
print("Audio ashowinfo:")
for l in [line for line in res_a.stderr.splitlines() if "ashowinfo" in line][:5]:
    print(" ", l)
