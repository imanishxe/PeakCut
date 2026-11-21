import subprocess
import json
from pathlib import Path

# Let's check words in words.json of job 20261117-211613-e2c30bf5c4
job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
words_file = job_p / "words.json"
with open(words_file) as f:
    words = json.load(f)

# Find words around clip01 (start: 91.69)
c1_words = [w for w in words if 90.0 <= w["s"] <= 100.0]
print("Transcript words around 91.69:")
for w in c1_words[:8]:
    print(" ", w)

# Now in clip01:
# clip['src_offset'] was 83.69
# So in clip01.src.mp4, the word at 91.69 should be at 91.69 - 83.69 = 8.0s!
# Let's transcribe clip01.src.mp4 audio from 0 to 15s to see what time the word is ACTUALLY spoken!
import sys
sys.path.insert(0, ".")
import numpy as np
from studio import transcribe, media

src = job_p / "clips" / "clip01.src.mp4"
wav = job_p / "clips" / "test_c1.wav"
media.extract_audio(src, wav)
audio = media.load_audio(wav)
wav.unlink(missing_ok=True)

heard = transcribe.transcribe(audio)
print("Heard words in clip01.src.mp4:")
for h in heard[:10]:
    print(f"  word: '{h['w']}', start: {h['s']:.2f}, end: {h['e']:.2f}")
