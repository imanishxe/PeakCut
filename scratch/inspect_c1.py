import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
job_json = job_p / "job.json"
with open(job_json) as f:
    job = json.load(f)

c1 = job["clips"][0]
print("Clip 1 keys and values:")
for k, v in c1.items():
    print(" ", k, ":", v)
