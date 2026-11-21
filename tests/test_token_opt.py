"""Test Selective AI Token Optimization: sentence boundary refinement and targeted snippet enhancement.

Verifies:
1. Sentence boundary refinement snaps start and end without cutting mid-speech.
2. Snippet-only AI enhancement sends only ~30s of text, achieving >90% token reduction.
3. Zero-token mode completely bypasses AI when ai_hooks=False.
4. Live Session handles decoupled detection and enhancement seamlessly.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-opt-")

from studio import brain, live, jobs

fails = []


def check(name, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(name)


def main():
    # Mock transcript with setup, hype peak, and payoff sentences
    # Setup sentence: "Look at the radar, enemy is flanking from behind." (45.0 - 49.5)
    # Action sentence: "I see him! He is one shot!" (50.0 - 53.0)
    # Peak payoff: "Boom! He got eliminated! Let's go!" (53.5 - 58.0)
    # Next sentence: "Now we need to rotate towards the safe zone." (60.0 - 64.0)
    words = [
        {"w": "Look", "s": 45.0, "e": 45.4},
        {"w": "at", "s": 45.5, "e": 45.7},
        {"w": "the", "s": 45.8, "e": 46.0},
        {"w": "radar,", "s": 46.1, "e": 46.6},
        {"w": "enemy", "s": 46.8, "e": 47.3},
        {"w": "is", "s": 47.4, "e": 47.6},
        {"w": "flanking", "s": 47.7, "e": 48.3},
        {"w": "from", "s": 48.4, "e": 48.7},
        {"w": "behind.", "s": 48.8, "e": 49.5},
        # Action
        {"w": "I", "s": 50.0, "e": 50.2},
        {"w": "see", "s": 50.3, "e": 50.6},
        {"w": "him!", "s": 50.7, "e": 51.1},
        {"w": "He", "s": 51.3, "e": 51.5},
        {"w": "is", "s": 51.6, "e": 51.8},
        {"w": "one", "s": 51.9, "e": 52.2},
        {"w": "shot!", "s": 52.3, "e": 53.0},
        # Payoff
        {"w": "Boom!", "s": 53.5, "e": 54.0},
        {"w": "He", "s": 54.2, "e": 54.5},
        {"w": "got", "s": 54.6, "e": 54.9},
        {"w": "eliminated!", "s": 55.0, "e": 56.2},
        {"w": "Let's", "s": 56.5, "e": 57.0},
        {"w": "go!", "s": 57.1, "e": 58.0},
        # Follow-up
        {"w": "Now", "s": 60.0, "e": 60.3},
        {"w": "we", "s": 60.4, "e": 60.6},
        {"w": "need", "s": 60.7, "e": 61.0},
        {"w": "to", "s": 61.1, "e": 61.3},
        {"w": "rotate.", "s": 61.4, "e": 62.0},
    ]

    # 1. Test Sentence Boundary Refinement
    # Raw candidate around t=54s (t-10 to t+5) -> 44.0 to 59.0
    s_refined, e_refined = brain.refine_spike_boundaries(
        candidate_start=46.0, candidate_end=57.0, words=words,
        min_len=10, max_len=30, duration=70.0
    )
    # The start should snap to the start of the setup sentence (around 45.0 - 0.15 = 44.85)
    check("start boundary snapped to sentence setup start (<= 45.0)", s_refined <= 45.0, True)
    # The end should snap after sentence completion ("eliminated!" at 56.2 -> ~56.45)
    check("end boundary snapped to sentence finish (>= 56.0)", e_refined >= 56.0, True)
    check("boundary length within allowed min_len/max_len", 10 <= (e_refined - s_refined) <= 30, True)

    # 2. Test Zero-Token Enhancement (use_ai=False)
    c_zero, tok_zero = brain.enhance_spike_clip(
        candidate_start=46.0, candidate_end=57.0, words=words,
        title="Apex Tournament", uploader="ProGamer", game="Apex Legends",
        why="Twitch chat spike (3.8x median)", use_ai=False
    )
    check("zero-token mode consumes 0 tokens", tok_zero, 0)
    check("zero-token clip has high viral score", c_zero["score"], 92)
    check("zero-token clip retains trigger reason", "Twitch chat spike" in c_zero["reason"], True)
    check("zero-token clip has fallback hook", len(c_zero["hook"]) > 0, True)

    # 3. Test Targeted AI Enhancement (use_ai=True)
    # Mock ask_ai to verify it ONLY receives the small snippet, and consumes minimal tokens
    mock_ai_output = [{
        "start": 0, "end": 0, "score": 95, "category": "clutch",
        "hook": "ONE SHOT BOOM", "title": "Insane Flank Elimination",
        "description": "Streamer wipes the flanking enemy in clutch timing.",
        "hashtags": ["ApexLegends", "Clutch", "Gaming"],
        "highlight_words": ["Boom", "eliminated"]
    }]

    captured_prompts = []

    def mock_ask_ai(prompt, **kwargs):
        captured_prompts.append(prompt)
        return mock_ai_output, "test-model", 115  # only 115 tokens!

    with patch.object(brain, "ask_ai", side_effect=mock_ask_ai):
        c_ai, tok_ai = brain.enhance_spike_clip(
            candidate_start=46.0, candidate_end=57.0, words=words,
            title="Apex Tournament", uploader="ProGamer", game="Apex Legends",
            why="Twitch chat spike (3.8x median)", use_ai=True
        )

        check("targeted AI enhancement returns exact tokens spent (~115)", tok_ai, 115)
        check("targeted AI hook applied to clip", c_ai["hook"], "ONE SHOT BOOM")
        check("targeted AI title applied to clip", c_ai["title"], "Insane Flank Elimination")
        check("targeted AI hashtags applied to clip", "ApexLegends" in c_ai["hashtags"], True)
        check("targeted AI called ask_ai once", len(captured_prompts), 1)

        # Verify the prompt sent to AI was a short snippet (< 3000 chars vs 20,000+ for whole stream)
        if captured_prompts:
            check("prompt is a compact snippet (under 3000 chars)", len(captured_prompts[0]) < 3000, True)
            check("prompt contains snippet text 'eliminated'", "eliminated" in captured_prompts[0], True)

    # 4. Live Session Integration with Targeted Enhancement
    d = tempfile.mkdtemp(prefix="pc-live-opt-")
    job = {
        "id": "test_opt_job",
        "title": "Valorant Finals",
        "uploader": "TenZ",
        "dir": d,
        "creator": "c_tenz",
        "ai": {},
        "source": {"url": "https://twitch.tv/tenz", "name": "TenZ"},
        "clips": [],
        "options": {"captions": True},
    }
    settings = {
        "style": "bounce",
        "layout": "blur",
        "min_len": 15,
        "max_len": 60,
        "live_per_hour": 6,
        "ai_every_min": 0,
        "ai_hooks": True,  # User enabled AI hooks on spikes
        "min_gap_min": 1,
    }
    s = live.Session(job, settings)
    s.samples = 16000 * 120
    s.words = words
    submitted_renders = []
    jobs.submit_live = lambda fn: submitted_renders.append(fn)

    with patch.object(brain, "ask_ai", side_effect=mock_ask_ai):
        # Fire spike at t=55s
        sp = {"t": 55.0, "why": "Twitch chat spike (4.2x median, 18 chatters)"}
        s._clip_spike(sp)

        check("session created clip from spike", len(job["clips"]), 1)
        clip = job["clips"][0]
        check("session recorded token usage on session object", s.tokens, 115)
        check("session recorded AI check count", s.checks, 1)
        check("session clip got viral hook", clip["hook"], "ONE SHOT BOOM")
        check("clip start was refined to sentence start", clip["start"] <= 45.0, True)

    if fails:
        print(f"\n{len(fails)} checks failed.")
        return 1
    print("\nALL PASSED\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
