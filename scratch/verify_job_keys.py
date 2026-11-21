import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
job_json = job_p / "job.json"
with open(job_json) as f:
    job = json.load(f)

for k in ["source", "source_file", "file", "path", "video"]:
    if k in job:
        print(k, ":", job[k])
print("Job files in dir:")
for p in job_p.iterdir():
    print(" ", p.name)
