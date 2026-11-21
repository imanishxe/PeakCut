import json
from pathlib import Path

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
with open(job_p / "words.json") as f:
    words = json.load(f)

for w in words:
    if "icebox" in w.get("w", "").lower() or "khelta" in w.get("w", "").lower() or "snd" in w.get("w", "").lower():
        print(w)
