import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a")
job_json = job_p / "job.json"
with open(job_json) as f:
    job = json.load(f)

for c in job["clips"]:
    print(f"=== {c['id']}: {c.get('title')} ===")
    print("  keys:", list(c.keys()))
    print("  start:", c.get("start"), "end:", c.get("end"))
    print("  src_offset:", c.get("src_offset"), "src_end:", c.get("src_end"))
    print("  layout:", c.get("layout"), "facecam:", c.get("facecam"))
    print("  captions:", c.get("captions"))
