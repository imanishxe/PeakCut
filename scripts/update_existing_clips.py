import sys
import json
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio import ctx, auth, brain, jobs

u = auth.local_user()
uid = getattr(u, "id", None) or u[0]
ctx.set_uid(uid)

print("Scanning for clips with placeholder metadata...")
count = 0

for p in Path("data").rglob("clips/*.json"):
    try:
        clip_data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue

    hook = clip_data.get("hook", "")
    title = clip_data.get("title", "")
    desc = clip_data.get("description", "")

    if "HYPE MOMENT" in hook or "Hype Spike" in title or "Triggered by" in desc:
        job_dir = p.parent.parent
        job_file = job_dir / "job.json"
        if not job_file.exists():
            continue

        try:
            job = json.loads(job_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        cid = p.stem  # e.g. clip001
        print(f"\nProcessing {job.get('creator')} / {job.get('id')} / {cid}...")

        # Load words from words.json if present
        words = []
        words_file = job_dir / "words.json"
        if words_file.exists():
            try:
                words = json.loads(words_file.read_text(encoding="utf-8"))
            except Exception:
                words = []

        c_start = clip_data.get("start", 0.0)
        c_end = clip_data.get("end", 0.0)
        snippet_words = [w for w in words if c_start <= w["s"] <= c_end]
        snippet_text = " ".join(w["w"] for w in snippet_words)

        why_trigger = clip_data.get("reason") or desc

        creator_name = job.get("uploader") or job.get("creator") or "Streamer"
        game_name = job.get("game") or "Grand Theft Auto VI"
        stream_title = job.get("title") or f"{creator_name} live"

        print(f"  Spoken snippet ({len(snippet_words)} words): '{snippet_text[:60]}...'")
        print(f"  Trigger: {why_trigger}")

        # Call AI to describe this specific clip contextually
        ai_meta, _ = brain.describe(
            snippet_text,
            title=stream_title,
            uploader=creator_name,
            game=game_name,
            why=why_trigger,
            return_spent=True
        )

        new_title = ai_meta.get("title") or f"{creator_name} in {game_name}"
        if new_title.lower().startswith("hype spike:"):
            new_title = new_title.split(":", 1)[1].strip()

        new_desc = ai_meta.get("description") or f"Crazy moment on {creator_name}'s stream playing {game_name}! 🔥"
        if any(bad in new_desc.lower() for bad in ("triggered by", "loudness +", "chat spike")):
            new_desc = f"Unbelievable reaction during {creator_name}'s live gameplay in {game_name}! Watch the full moment."

        new_hook = ai_meta.get("hook", "")
        if any(bad in new_hook.lower() for bad in ("hype moment", "hype spike", "triggered by")):
            new_hook = ""

        new_tags = ai_meta.get("hashtags") or [re.sub(r'[^a-zA-Z0-9]', '', t) for t in [game_name, creator_name, "Gaming"] if t]

        print(f"  -> New Title: {new_title}")
        print(f"  -> New Description: {new_desc}")
        print(f"  -> New Hook: '{new_hook}'")

        # Update clip file
        clip_data["title"] = new_title
        clip_data["description"] = new_desc
        clip_data["hook"] = new_hook
        clip_data["hashtags"] = new_tags
        clip_data["reason"] = why_trigger  # Personal info preserved in reason
        p.write_text(json.dumps(clip_data, indent=1), encoding="utf-8")

        # Update job.json
        for jc in job.get("clips", []):
            if jc.get("id") == cid:
                jc["title"] = new_title
                jc["description"] = new_desc
                jc["hook"] = new_hook
                jc["hashtags"] = new_tags
                jc["reason"] = why_trigger

        job_file.write_text(json.dumps(job, indent=1), encoding="utf-8")
        count += 1

print(f"\nSuccessfully updated {count} clips with contextual AI descriptions!")
