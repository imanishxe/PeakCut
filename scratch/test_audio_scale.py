import sys
sys.path.insert(0, ".")
from pathlib import Path
from studio import media
import numpy as np

src1 = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip01.src.mp4")
src2 = Path(r"C:\Dev\PeakCut\data\users\u_local\jobs\20261117-211613-e2c30bf5c4\clips\clip02.src.mp4")

wav1 = Path("scratch/s1.wav")
media.extract_audio(src1, wav1)
a1 = media.load_audio(wav1)
wav1.unlink(missing_ok=True)

print("a1 shape:", a1.shape, "dtype:", a1.dtype, "mean abs:", float(np.abs(a1).mean()))
