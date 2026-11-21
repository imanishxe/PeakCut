import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
job_json = job_p / "job.json"
with open(job_json) as f:
    job = json.load(f)

for c in job["clips"][:6]:
    print(f"=== {c['id']}: {c.get('title')} ===")
    print("  start:", c.get("start"), "end:", c.get("end"))
    print("  src_offset:", c.get("src_offset"), "src_end:", c.get("src_end"))
    print("  local start (start - off):", c.get("start") - c.get("src_offset", 0))
    print("  src:", c.get("src"))
