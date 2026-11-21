import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.live import resolve, NotLive

candidates = [
    ("xQc Twitch", "https://www.twitch.tv/xqc"),
    ("xQc Kick", "https://kick.com/xqc"),
    ("TGG YouTube", "https://www.youtube.com/@TGG"),
    ("TGG YouTube live", "https://www.youtube.com/@TGG/live"),
    ("TGG Twitch", "https://www.twitch.tv/tgg"),
    ("TheFeedski Twitch", "https://www.twitch.tv/thefeedski")
]

for label, url in candidates:
    try:
        res = resolve(url)
        print("[LIVE]", label, url, res.get("title", ""))
    except NotLive as e:
        print("[OFFLINE]", label, url, str(e))
    except Exception as e:
        print("[ERROR]", label, url, str(e))
