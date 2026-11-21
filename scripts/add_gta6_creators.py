import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import ctx, auth, creators

u = auth.local_user()
uid = getattr(u, 'id', None) or u[0]
ctx.set_uid(uid)

streamers = [
    ("n3on", "https://kick.com/n3on"),
    ("Adin Ross", "https://kick.com/adinross"),
    ("TheBurntPeanut", "https://www.twitch.tv/theburntpeanut"),
    ("jasontheween", "https://www.twitch.tv/jasontheween"),
    ("Lacy", "https://www.twitch.tv/lacy"),
    ("Kreek", "https://www.youtube.com/@kreek/live"),
    ("HutchMF", "https://www.twitch.tv/hutchmf"),
    ("summit1g", "https://www.twitch.tv/summit1g")
]

existing = {c["name"].lower(): c for c in creators.all_creators()}
for name, url in streamers:
    if name.lower() in existing:
        print(f"Already exists: {name}")
    else:
        c = creators.create({
            "name": name,
            "channel": url,
            "layout": "stacked",
            "style": "bounce",
            "captions": True,
            "auto_watch": True,
            "ai_hooks": True,
            "ai_only_on_spike": True,
            "game": "Grand Theft Auto VI"
        })
        print(f"Created: {c['name']} (ID: {c['id']})")

print("Total creators now:", len(creators.all_creators()))
