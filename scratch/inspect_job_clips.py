import json
from pathlib import Path

job_dir = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a")
job_json = job_dir / "job.json"
with open(job_json) as f:
    job = json.load(f)

for c in job["clips"]:
    print(f"=== {c['id']}: {c.get('title')} ===")
    print(f"  start={c.get('start')}, end={c.get('end')}, dur={c.get('end') - c.get('start')}")
    print(f"  src={c.get('src')}")
    print(f"  src_offset={c.get('src_offset')}")
    print(f"  src_end={c.get('src_end')}")
    print(f"  local start={c.get('start') - c.get('src_offset', 0)}, local end={c.get('end') - c.get('src_offset', 0)}")
