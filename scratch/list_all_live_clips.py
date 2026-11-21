import json
from pathlib import Path

creators_dir = Path("data/users/u_local/creators")
for c_dir in creators_dir.iterdir():
    if not c_dir.is_dir():
        continue
    live_dir = c_dir / "live"
    if not live_dir.exists():
        continue
    for j_dir in live_dir.iterdir():
        j_file = j_dir / "job.json"
        if not j_file.exists():
            continue
        try:
            with open(j_file, encoding="utf-8") as f:
                job = json.load(f)
            clips = job.get("clips", [])
            print(f"Creator: {c_dir.name} | Job: {j_dir.name} | Clips: {len(clips)} | Title: {job.get('title', '')[:50]}")
            for clip in clips:
                print(f"   {clip['id']}: '{clip.get('title')}' (start={clip.get('start')}, end={clip.get('end')}, off={clip.get('src_offset')})")
        except Exception as e:
            pass
