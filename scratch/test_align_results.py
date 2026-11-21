import sys
sys.path.insert(0, ".")
from pathlib import Path
import json
import re
import numpy as np
from studio import transcribe, media

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a")
with open(job_p / "job.json") as f:
    job = json.load(f)

# Load words from the session if there's words.json or check words in job.json
for clip in job["clips"]:
    src = Path(clip["src"])
    if not src.exists():
        continue
    wav = Path(f"scratch/{clip['id']}.wav")
    media.extract_audio(src, wav)
    audio = media.load_audio(wav)
    wav.unlink(missing_ok=True)
    heard = transcribe.transcribe(audio)
    
    # What did the clip think was said at clip['start']?
    print(f"=== {clip['id']} ===")
    print(f"  clip['start']: {clip['start']}, src_offset: {clip.get('src_offset')}")
    print(f"  expected speech in src at: {clip['start'] - clip.get('src_offset', 0):.2f}s")
    print(f"  heard words in src around that time:")
    expected_t = clip['start'] - clip.get('src_offset', 0)
    near_heard = [w for w in heard if expected_t - 5 <= w['s'] <= expected_t + 5]
    for w in near_heard[:6]:
        print(f"    '{w['w']}' at {w['s']:.2f}s - {w['e']:.2f}s")
