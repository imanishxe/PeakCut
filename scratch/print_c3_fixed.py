import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
with open(job_p / "job.json") as f:
    job = json.load(f)

c3 = job["clips"][2]
print("Clip 3 fixed_words:")
for w in c3.get("fixed_words", [])[:10]:
    print(" ", w)
