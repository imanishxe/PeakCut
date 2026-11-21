import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.brain import ask_ai, RULES

prompt = (
    "A streamer's viewer clipped an intense moment on a live stream.\n"
    "Video title: Checking out GTA6. What else is there to put here.\n"
    "Channel: summit1g\n"
    "Game: Grand Theft Auto VI\n"
    "Trigger: Streamer reacted with loudness +81%\n"
    "Spoken words in this moment: 'look at that explosion bro holy'\n\n"
    "Return exactly one item with hook, title, description, and hashtags tailored to this clip for social media (Instagram/Reels/TikTok).\n"
    "NEVER include generic placeholders like 'Hype Moment' or diagnostic text like 'Triggered by loudness'. Make it an engaging real social post.\n"
    + RULES.format(min_len=0, max_len=0, transcript="[0.0] look at that explosion bro holy")
)
out, m, spent = ask_ai(prompt, purpose="Clip snippet: title and hook")
print("Output:", out)
