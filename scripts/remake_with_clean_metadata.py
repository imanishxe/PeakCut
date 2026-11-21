import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Query running server for all clips
req = urllib.request.urlopen("http://127.0.0.1:8765/api/sync")
data = json.loads(req.read().decode("utf-8"))

clips_to_fix = []
for j in data.get("jobs", []):
    jid = j["id"]
    for c in j.get("clips", []):
        cid = c["id"]
        hook = c.get("hook", "")
        title = c.get("title", "")
        desc = c.get("description", "")
        if "HYPE MOMENT" in hook or "Hype Spike" in title or "Triggered by" in desc:
            clips_to_fix.append((jid, cid, j.get("creator"), j.get("game"), j.get("title"), c))

print(f"Found {len(clips_to_fix)} clips on running server needing cleanup.")

for jid, cid, creator, game, stream_title, clip in clips_to_fix:
    # Check if we already have the updated metadata in clips/{cid}.json on disk
    clip_file = None
    for p in Path("data").rglob(f"live/{jid}/clips/{cid}.json"):
        clip_file = p
        break

    if clip_file and clip_file.exists():
        updated = json.loads(clip_file.read_text(encoding="utf-8"))
        new_title = updated.get("title", "")
        new_desc = updated.get("description", "")
        new_hook = updated.get("hook", "")
    else:
        new_title = f"{creator or 'Streamer'} - {game or 'GTA 6'}"
        new_desc = f"Insane moment on {creator or 'stream'} playing {game or 'GTA 6'}! 🔥"
        new_hook = ""

    if new_title.lower().startswith("hype spike:"):
        new_title = new_title.split(":", 1)[1].strip()
    if any(bad in new_desc.lower() for bad in ("triggered by", "loudness +", "chat spike")):
        new_desc = f"Wild reaction during live gameplay in {game or 'GTA 6'}!"
    if any(bad in new_hook.lower() for bad in ("hype moment", "hype spike")):
        new_hook = ""

    print(f"\nUpdating {creator} / {jid} / {cid}:")
    print(f"  Title: {new_title}")
    print(f"  Desc:  {new_desc[:60]}...")
    print(f"  Hook:  '{new_hook}'")

    body = {
        "title": new_title,
        "description": new_desc,
        "hook": new_hook,
        "layout": clip.get("layout", "stacked"),
        "style": clip.get("style", "bounce"),
        "captions": clip.get("captions", True),
        "start": clip.get("start"),
        "end": clip.get("end")
    }

    url = f"http://127.0.0.1:8765/api/jobs/{jid}/clips/{cid}/render"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"  -> Successfully requested remake! Status {resp.status}")
    except urllib.error.HTTPError as e:
        print(f"  -> Error: {e.code} - {e.read().decode('utf-8', 'replace')}")

print("\nDone!")
