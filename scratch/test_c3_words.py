import sys
sys.path.insert(0, ".")
from pathlib import Path
import json
from studio import media, transcribe

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4")
with open(job_p / "job.json") as f:
    job = json.load(f)

c3 = job["clips"][2] # clip03
print("Clip 3:", c3["id"], "start:", c3["start"], "end:", c3["end"])
src = Path(c3["src"])
print("src:", src.exists(), src)

wav = Path("scratch/c3.wav")
media.extract_audio(src, wav)
audio = media.load_audio(wav)
wav.unlink(missing_ok=True)

heard = transcribe.transcribe(audio)
print(f"Total heard words in clip03.src.mp4: {len(heard)}")
print("First 10 words in clip03.src.mp4:")
for w in heard[:10]:
    print(f"  '{w['w']}' from {w['s']:.2f} to {w['e']:.2f}")

# Now check words from words.json for clip03 (start=434.33, end=474.8)
with open(job_p / "words.json") as f:
    all_words = json.load(f)

c3_words = [w for w in all_words if 430.0 <= w["s"] <= 445.0]
print("Transcript words around 434.33:")
for w in c3_words[:10]:
    print(f"  '{w['w']}' from {w['s']:.2f} to {w['e']:.2f}")
