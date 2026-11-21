import subprocess
import json
from pathlib import Path
import sys
sys.path.insert(0, ".")
from studio import transcribe, media

ts = Path(r"C:\Dev\PeakCut\data\users\u_local\creators\ishowspeed\live\20261118-193834-d6072c986a\clips\clip002.src.ts")

# 1. Extract audio with -af "asetpts=PTS-STARTPTS" vs raw
wav_raw = Path("scratch/test_c2_raw.wav")
wav_startpts = Path("scratch/test_c2_startpts.wav")

subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ts), "-vn", "-ac", "1", "-ar", "16000", str(wav_raw)])
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ts), "-vn", "-ac", "1", "-af", "asetpts=PTS-STARTPTS", "-ar", "16000", str(wav_startpts)])

audio_raw = media.load_audio(wav_raw)
audio_startpts = media.load_audio(wav_startpts)

print(f"wav_raw samples: {len(audio_raw)} ({len(audio_raw)/16000:.3f}s)")
print(f"wav_startpts samples: {len(audio_startpts)} ({len(audio_startpts)/16000:.3f}s)")

# Transcribe both
h_raw = transcribe.transcribe(audio_raw)
print("First 3 words in raw:")
for w in h_raw[:3]:
    print(f"  '{w['w']}' from {w['s']:.3f} to {w['e']:.3f}")

# Check video packet timestamps in clip002.src.ts
cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-read_intervals", "%+3", "-print_format", "json", str(ts)]
res = subprocess.run(cmd, capture_output=True, text=True)
v_pkts = json.loads(res.stdout).get("packets", [])
print("First video packet pts_time in ts:", v_pkts[0].get("pts_time"))

cmd_a = ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "packet=pts_time", "-read_intervals", "%+3", "-print_format", "json", str(ts)]
res_a = subprocess.run(cmd_a, capture_output=True, text=True)
a_pkts = json.loads(res_a.stdout).get("packets", [])
print("First audio packet pts_time in ts:", a_pkts[0].get("pts_time"))
