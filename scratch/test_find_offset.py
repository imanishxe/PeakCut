import sys
sys.path.insert(0, ".")
from pathlib import Path
import json
import numpy as np
from studio import media

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
with open(job_p / "job.json") as f:
    job = json.load(f)

# Load full audio if it exists, or check where full_audio was loaded
print("Job dir files:")
for f in job_p.iterdir():
    print(" ", f.name)
