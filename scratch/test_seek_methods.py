import subprocess
import json
from pathlib import Path

# Let's test on data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4
src = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")

# Test 1: with trim/atrim filter (current method)
cmd1 = [
    "ffmpeg", "-y", "-v", "error", "-i", str(src),
    "-filter_complex", "[0:v]trim=start=8.0:end=18.0,setpts=PTS-STARTPTS[v];[0:a:0]atrim=start=8.0:end=18.0,asetpts=PTS-STARTPTS[a]",
    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-c:a", "aac", "scratch/test1_trim.mp4"
]
subprocess.run(cmd1)

# Test 2: with -ss and -to as input options (fast seek)
cmd2 = [
    "ffmpeg", "-y", "-v", "error", "-ss", "8.0", "-to", "18.0", "-i", str(src),
    "-c:v", "libx264", "-c:a", "aac", "scratch/test2_seek.mp4"
]
subprocess.run(cmd2)

# Check stream durations and first packet timestamps of both
for name in ["test1_trim.mp4", "test2_seek.mp4"]:
    p = Path(f"scratch/{name}")
    cmd_probe = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration,nb_frames", "-print_format", "json", str(p)]
    res = subprocess.run(cmd_probe, capture_output=True, text=True)
    print(f"=== {name} ===")
    d = json.loads(res.stdout)
    for s in d["streams"]:
        print(f"  {s['codec_type']}: start={s.get('start_time')}, dur={s.get('duration')}, frames={s.get('nb_frames')}")
