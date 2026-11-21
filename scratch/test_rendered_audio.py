import sys
sys.path.insert(0, ".")
from pathlib import Path
from studio import transcribe, media

job_p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips")
mp4 = job_p / "clip01.mp4"
wav = job_p / "test_rendered_c1.wav"
media.extract_audio(mp4, wav)
audio = media.load_audio(wav)
wav.unlink(missing_ok=True)

heard = transcribe.transcribe(audio)
print("Heard words in clip01.mp4:")
for h in heard[:10]:
    print(f"  word: '{h['w']}', start: {h['s']:.2f}, end: {h['e']:.2f}")
