import sys
sys.path.insert(0, ".")
from pathlib import Path
from studio import transcribe, media

p = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips")
for c in [f"clip{i:02d}" for i in range(1, 7)]:
    mp4 = p / f"{c}.mp4"
    ass = p / f"{c}.ass"
    if mp4.exists():
        wav = p / f"test_{c}.wav"
        media.extract_audio(mp4, wav)
        audio = media.load_audio(wav)
        wav.unlink(missing_ok=True)
        heard = transcribe.transcribe(audio)
        first_heard = heard[0] if heard else None
        
        ass_txt = ass.read_text(encoding="utf-8") if ass.exists() else ""
        first_diag = next((line for line in ass_txt.splitlines() if line.startswith("Dialogue:") and "Cap" in line), None)
        print(f"=== {c} ===")
        print(f"  First heard word in MP4: '{first_heard['w']}' at {first_heard['s']:.2f}s" if first_heard else "  No words heard")
        print(f"  First ASS dialogue line: {first_diag}")
