import json
from pathlib import Path
import subprocess

speed_dir = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live")
for job_p in speed_dir.iterdir():
    if not job_p.is_dir():
        continue
    job_json = job_p / "job.json"
    if not job_json.exists():
        continue
    with open(job_json, "r", encoding="utf-8") as f:
        job = json.load(f)
    print(f"=== JOB {job_p.name} ({job.get('title')}) ===")
    for c in job.get("clips", []):
        mp4 = job_p / "clips" / f"{c['id']}.mp4"
        src = job_p / "clips" / f"{c['id']}.src.ts"
        print(f"  Clip: {c['id']} | title: {c.get('title')} | start: {c.get('start')} | end: {c.get('end')} | src_offset: {c.get('src_offset')}")
        print(f"    mp4 exists: {mp4.exists()} (size: {mp4.stat().st_size if mp4.exists() else 0})")
        print(f"    src.ts exists: {src.exists()} (size: {src.stat().st_size if src.exists() else 0})")
