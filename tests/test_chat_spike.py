"""Test Twitch IRC chat spike detection logic and zero-token hype extraction.

Runs against studio.chat_spike and studio.live.Session directly.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["PEAKCUT_DATA"] = tempfile.mkdtemp(prefix="pc-spike-")

from studio import chat_spike, live, jobs

fails = []


def check(name, got, want=True):
    ok = want(got) if callable(want) else got == want
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   got {got!r}"))
    if not ok:
        fails.append(name)


def main():
    chat_counts = {}
    chat_people = {}

    # 1. Warm-up test: before 60 seconds, no spike should trigger
    for t in range(50):
        chat_counts[t] = 10
        chat_people[t] = {f"user_{i}" for i in range(10)}

    res = chat_spike.evaluate_chat_spike(chat_counts, chat_people, current_sec=45, min_users=5)
    check("no spike during stream warmup (< 60s)", res, None)

    # 2. Steady state: 3 minutes of steady traffic (2 users per 10s bucket)
    chat_counts.clear()
    chat_people.clear()
    for t in range(0, 240):
        if t % 5 == 0:
            chat_counts[t] = 1
            chat_people[t] = {f"regular_{t % 2}"}

    # At t=200, still steady
    res_steady = chat_spike.evaluate_chat_spike(chat_counts, chat_people, current_sec=200, min_users=5)
    check("no spike during steady chat traffic", res_steady, None)

    # 3. Bot spam: single user flooding 60 messages in 10 seconds (t=201 to t=210)
    for t in range(201, 211):
        chat_counts[t] = 6
        chat_people[t] = {"spambot_99"}

    res_bot = chat_spike.evaluate_chat_spike(chat_counts, chat_people, current_sec=210, min_users=5)
    check("bot spam is rejected by user deduplication", res_bot, None)

    # 4. Genuine crowd hype: 12 distinct users cheering at t=211..220
    for i, t in enumerate(range(211, 221)):
        chat_counts[t] = 2
        chat_people[t] = {f"hype_user_{i * 2}", f"hype_user_{i * 2 + 1}"}

    res_hype = chat_spike.evaluate_chat_spike(chat_counts, chat_people, current_sec=220, min_users=5, multiplier=2.5)
    check("genuine crowd hype triggers a spike", res_hype is not None, True)
    if res_hype:
        check("hype spike contains expected ratio >= 2.5", res_hype["ratio"] >= 2.5, True)
        check("hype spike recorded distinct users >= 10", res_hype["users"] >= 10, True)
        check("hype spike has informative reason text", "Twitch chat spike" in res_hype["why"], True)

    # 5. Quiet stream handling: median = 0, but sudden group of 6 users chat
    chat_counts.clear()
    chat_people.clear()
    for t in range(201, 211):
        chat_counts[t] = 1
        chat_people[t] = {f"quiet_viewer_{t - 200}"}

    res_quiet_spike = chat_spike.evaluate_chat_spike(chat_counts, chat_people, current_sec=210, min_users=5)
    check("quiet stream surge with >= min_users triggers", res_quiet_spike is not None, True)

    # 6. Quiet stream with insufficient users: only 3 users
    chat_counts.clear()
    chat_people.clear()
    for t in range(201, 204):
        chat_counts[t] = 1
        chat_people[t] = {f"quiet_viewer_{t}"}
    res_under_min = chat_spike.evaluate_chat_spike(chat_counts, chat_people, current_sec=210, min_users=5)
    check("quiet stream surge below min_users does not trigger", res_under_min, None)

    # 7. Live Session Zero-Token Spike Integration Test
    d = tempfile.mkdtemp(prefix="pc-live-spike-")
    job = {
        "id": "test_spike_job",
        "title": "Hype Championship",
        "uploader": "ApexPro",
        "dir": d,
        "creator": "c_pro",
        "ai": {},
        "source": {"url": "https://twitch.tv/apexpro", "name": "ApexPro"},
        "clips": [],
        "options": {"captions": True},
    }
    settings = {
        "style": "bounce",
        "layout": "blur",
        "min_len": 15,
        "max_len": 60,
        "live_per_hour": 6,
        "ai_every_min": 0,  # Zero-token / spikes-only mode
        "min_gap_min": 1,
        "chat_spike_min_users": 5,
    }
    s = live.Session(job, settings)
    s.samples = 16000 * 250  # 250 seconds of stream
    s.db = [-30.0] * 250     # normal loudness
    s.chat_on = True

    # Seed baseline chat
    for t in range(0, 230):
        if t % 10 == 0:
            s.chat[t] = 1
            s.chat_users[t] = {f"user_{t % 3}"}

    # Seed sudden hype spike at t=240..250 with 12 distinct chatters
    for i, t in enumerate(range(240, 250)):
        s.chat[t] = 2
        s.chat_users[t] = {f"hype_{i}", f"fan_{i}"}

    # Intercept background render submission so we can inspect queued clips without ffmpeg
    submitted_renders = []
    jobs.submit_live = lambda fn: submitted_renders.append(fn)

    # Watch spikes
    s._watch_spikes()
    check("Session._watch_spikes detects Twitch hype spike", s.spike is not None, True)
    if s.spike:
        check("spike reason mentions Twitch chat spike", "Twitch chat spike" in s.spike["why"], True)

        # Stream continues for another 20s as buffer records
        s.samples = 16000 * 270
        # Trigger zero-token clip extraction
        sp = s.spike
        s.spike = None
        s._clip_spike(sp)

        check("zero-token clip is added to job['clips']", len(job["clips"]), 1)
        c = job["clips"][0]
        check("clip start is ~20s before spike", abs(c["start"] - (sp["t"] - 20)) < 0.1, True)
        check("clip end is ~10s after spike", abs(c["end"] - (sp["t"] + 10)) < 0.1, True)
        check("clip score is high viral score (92)", c["score"], 92)
        check("render job was submitted to queue", len(submitted_renders), 1)
        check("zero AI tokens were consumed", s.tokens, 0)
        check("zero AI checks were performed", s.checks, 0)

    # 8. Check that periodic _ai_check does nothing when ai_every_min == 0
    s._ai_check(window=None)
    check("periodic _ai_check is suppressed in zero-token mode", s.checks, 0)

    if fails:
        print(f"\n{len(fails)} checks failed.")
        return 1
    print("\nALL PASSED\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
