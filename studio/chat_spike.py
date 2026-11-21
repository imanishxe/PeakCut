"""Twitch chat spike detection: find hype moments from chat velocity without using AI tokens.

Measures chat messages and distinct chatters in sliding 10-second buckets against a rolling
3-minute median. Spikes trigger when velocity jumps at least 2.5x above the median and reaches
a minimum number of distinct people talking, filtering out bot spam and repetitive emotes.
"""
import collections
import statistics
from typing import Dict, List, Optional, Set


def get_bucket(chat_counts: Dict[int, int], chat_people: Dict[int, Set[str]], start_sec: int, end_sec: int):
    """Count messages and distinct chatters between start_sec and end_sec (inclusive).

    Counts unique usernames so ten people saying "W" counts as 10 chatters, while one bot
    repeating "W" 50 times counts as 1 chatter.
    """
    msgs = 0
    users: Set[str] = set()
    for t in range(int(start_sec), int(end_sec) + 1):
        msgs += chat_counts.get(t, 0)
        p = chat_people.get(t)
        if p:
            users.update(p)
    return msgs, users


def evaluate_chat_spike(chat_counts: Dict[int, int], chat_people: Dict[int, Set[str]], current_sec: int,
                        bucket_sec: int = 10, window_sec: int = 180, multiplier: float = 2.5,
                        min_users: int = 5, min_messages: int = 5) -> Optional[dict]:
    """Check if the last bucket_sec seconds contain a statistically significant chat spike.

    Returns a dict with spike details if a spike occurred, or None otherwise.

    Rules:
    1. Needs at least 60 seconds of history before evaluating.
    2. Compares the current bucket against the median of all non-overlapping buckets in the prior window.
    3. Requires current velocity >= multiplier * median (or baseline for quiet chats).
    4. Requires distinct chatters in the current bucket >= min_users (prevents bot spam).
    5. Requires total messages in the current bucket >= min_messages.
    """
    cur_t = int(current_sec)
    if cur_t < 60:
        return None  # Stream just started; warming up

    # 1. Current bucket: [cur_t - bucket_sec + 1, cur_t]
    cur_start = cur_t - bucket_sec + 1
    cur_msgs, cur_users = get_bucket(chat_counts, chat_people, cur_start, cur_t)
    num_users = len(cur_users) if cur_users else cur_msgs

    if num_users < min_users or cur_msgs < min_messages:
        return None

    # 2. Historical window: prior window_sec ending right before cur_start
    hist_end = cur_start - 1
    hist_start = max(0, hist_end - window_sec + 1)
    if hist_end - hist_start < bucket_sec:
        return None

    # Slice into consecutive historical buckets
    hist_buckets: List[float] = []
    t = hist_end
    while t - bucket_sec + 1 >= hist_start:
        b_msgs, b_users = get_bucket(chat_counts, chat_people, t - bucket_sec + 1, t)
        val = len(b_users) if cur_users else b_msgs
        hist_buckets.append(float(val))
        t -= bucket_sec

    if not hist_buckets:
        return None

    med = statistics.median(hist_buckets)
    # Effective baseline: even in completely silent chats (median=0), require a modest baseline
    effective_base = max(med, 1.0)
    ratio = num_users / effective_base

    if ratio >= multiplier and cur_msgs >= max(min_messages, int(med * multiplier)):
        return {
            "spike": True,
            "time": cur_t,
            "ratio": round(ratio, 2),
            "median": round(med, 2),
            "users": num_users,
            "messages": cur_msgs,
            "why": f"Twitch chat spike ({round(ratio, 1)}x median, {num_users} chatters)",
        }

    return None
