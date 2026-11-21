import urllib.request
import json

creators_to_add = [
    {
        "name": "xQc",
        "channel": "https://www.twitch.tv/xqc",
        "channels": {
            "twitch": "https://www.twitch.tv/xqc",
            "kick": "https://kick.com/xqc"
        },
        "layout": "stacked",
        "style": "bounce",
        "captions": True,
        "auto_watch": True,
        "ai_hooks": True,
        "ai_only_on_spike": True,
        "game": "Grand Theft Auto VI"
    },
    {
        "name": "TGG",
        "channel": "https://www.youtube.com/@TGG",
        "channels": {
            "youtube": "https://www.youtube.com/@TGG"
        },
        "layout": "stacked",
        "style": "bounce",
        "captions": True,
        "auto_watch": True,
        "ai_hooks": True,
        "ai_only_on_spike": True,
        "game": "Grand Theft Auto VI"
    }
]

for c in creators_to_add:
    data = json.dumps(c).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8765/api/creators",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"Created: {res.get('name')} (ID: {res.get('id')})")
    except Exception as e:
        print(f"Error adding {c['name']}: {e}")
