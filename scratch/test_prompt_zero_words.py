import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.brain import ask_ai, RULES

prompt = (
    "A streamer's viewer clipped an intense gameplay reaction moment on a live stream.\n"
    "Video title: Checking out GTA6. What else is there to put here.\n"
    "Channel: summit1g\n"
    "Game: Grand Theft Auto VI\n"
    "Reaction trigger: Streamer yelled / sudden volume surge during live gameplay (+81% loudness)\n"
    "Spoken words: (non-verbal intense gameplay reaction / yelling)\n\n"
    "Return exactly one item describing this moment with a catchy punchy hook, engaging title, social description, and hashtags tailored to this clip for Instagram/TikTok/Reels.\n"
    "Do NOT use generic placeholders like 'Hype Moment' or technical terms like 'Triggered by loudness'.\n"
    + RULES.format(min_len=0, max_len=0, transcript="[0.0] (intense reaction shouting)")
)
out, m, spent = ask_ai(prompt, purpose="Clip snippet: title and hook")
print("Output with 0 words:", out)
