import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from studio.brain import ask_ai, _safe, _game_rules, RULES, _tidy

def test_describe(text, title="", uploader="", game=None, why=""):
    spoken = _safe(text, 8000) if len(text.split()) >= 3 else "(Intense gameplay reaction / streamer shouting)"
    trigger_desc = f"\nReaction trigger: {_safe(why)}" if why else ""
    prompt = (
        f"A streamer's viewer clipped an intense moment on a live stream.\n"
        f"Video title: {_safe(title) or 'unknown'}\n"
        f"Channel: {_safe(uploader) or 'unknown'}\n"
        f"Game: {_safe(game) or 'Gaming'}{trigger_desc}\n"
        f"Spoken words: {spoken}\n\n"
        f"Return exactly one item with hook, title, description, and hashtags tailored to this clip for social media (Instagram Reels, TikTok, YouTube Shorts).\n"
        f"CRITICAL RULES FOR SOCIAL MEDIA:\n"
        f"- The 'title' must be catchy and natural (e.g. '{uploader or 'Streamer'} Loses It in {game or 'GTA 6'}'). NEVER start with 'Hype Spike:' or technical prefixes.\n"
        f"- The 'description' must be a captivating caption for social media viewers about what happens in the clip. NEVER include technical diagnostics like 'Triggered by loudness' or 'chat spike'.\n"
        f"- The 'hook' (big text on video) should only be a short 2-4 word punchy phrase if there is a real highlight (e.g. 'NO WAY', 'CRAZY REACTION'). If nothing specific, leave it empty \"\". NEVER use '🔥 HYPE MOMENT' or generic placeholders.\n"
        + _game_rules(game)
        + RULES.format(min_len=0, max_len=0, transcript=spoken)
    )
    out, _m, spent = ask_ai(prompt, purpose="Clip snippet: title and hook")
    if out:
        c = _tidy(out[0], 0, 0, game)
        return c, spent
    return None, spent

print("--- Test 1 (Adin Ross, loudness +86%, 0 words) ---")
c1, _ = test_describe("", title="PLAYING GTA 6 NOW", uploader="Adin Ross", game="Grand Theft Auto VI", why="loudness +86%")
print(c1)

print("\n--- Test 2 (n3on, loudness +81%, few words) ---")
c2, _ = test_describe("yo bro watch out", title="PLAYING GTA 6 EARLY", uploader="n3on", game="Grand Theft Auto VI", why="loudness +81%")
print(c2)
