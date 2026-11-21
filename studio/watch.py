"""Headless CLI / Watcher Mode for PeakCut.

Allows developers and power users to monitor live streams from the terminal or on a
headless VPS without needing to launch or navigate the web dashboard:
    python -m studio.watch <twitch_channel> [--min 5] [--layout stacked] [--ai-hooks] [--out ./clips]
"""
import argparse
import os
import re
import shutil
import signal
import sys
import time
from pathlib import Path

from . import auth, config, creators, ctx, db, jobs, live, render


def normalize_channel(channel: str) -> str:
    channel = channel.strip()
    if channel.startswith(("http://", "https://")):
        return live.normalize(channel)
    # Default to Twitch channel if username given
    clean = re.sub(r"^[@#]", "", channel)
    return f"https://www.twitch.tv/{clean}"


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m studio.watch",
        description="PeakCut Headless Live Stream Watcher: auto-record & clip streams directly from the terminal."
    )
    p.add_argument("channel", help="Channel username (e.g. TenZ) or URL (Twitch, Kick, YouTube)")
    p.add_argument("--min", "--min-users", dest="min_users", type=int, default=5,
                   help="Minimum distinct chat users in 10s to trigger a chat spike (default: 5)")
    p.add_argument("--layout", choices=list(render.LAYOUTS.keys()), default="stacked",
                   help="9:16 layout framing (default: stacked; choices: stacked, gameplay, blur, crop, zoom)")
    p.add_argument("--style", choices=list(render.STYLES.keys()), default="bounce",
                   help="Caption text animation style (default: bounce; choices: bounce, hype, clean)")
    p.add_argument("--no-captions", dest="captions", action="store_false", default=True,
                   help="Disable burned-in video captions")
    p.add_argument("--ai-hooks", dest="ai_hooks", action="store_true", default=True,
                   help="Enable targeted AI viral hook titles & sentence snapping (default: True)")
    p.add_argument("--no-ai-hooks", dest="ai_hooks", action="store_false",
                   help="Disable AI hooks (100%% zero-token detection and clipping)")
    p.add_argument("--ai-every-min", type=int, default=0,
                   help="Periodic AI check interval in minutes (default: 0 = spike-only zero-token mode)")
    p.add_argument("--buffer-min", type=int, default=20,
                   help="Minutes of rolling circular stream buffer to keep on disk (default: 20)")
    p.add_argument("--out", "--output-dir", dest="out_dir", type=str, default="",
                   help="Directory to export completed clips into")
    p.add_argument("--poll-interval", type=int, default=30,
                   help="Seconds to wait between checks when streamer is offline (default: 30)")
    return p.parse_args(argv)


def run_watcher(args, stop_event=None) -> int:
    url = normalize_channel(args.channel)
    m = re.search(r"^https?://(?:www\.)?[^/]+/([^/?#]+)", url)
    name = m.group(1) if m else "streamer"

    print("=" * 65)
    print("  PeakCut Headless Stream Watcher")
    print(f"  Target:     {url}")
    print(f"  Layout:     {args.layout} ({render.LAYOUTS.get(args.layout)})")
    print(f"  Captions:   {args.style if args.captions else 'Disabled'}")
    print(f"  AI Hooks:   {'Enabled (~100 tokens/clip)' if args.ai_hooks else 'Disabled (Zero-Token Mode)'}")
    print(f"  Chat Spike: >= {args.min_users} distinct chatters (2.5x volume)")
    print(f"  Buffer:     {args.buffer_min} minutes rolling circular buffer")
    if args.out_dir:
        print(f"  Export dir: {Path(args.out_dir).resolve()}")
    print("=" * 65, flush=True)

    db.init()
    render.install_fonts()
    user = auth.local_user()
    uid = getattr(user, "id", None) or user[0]
    ctx.set_uid(uid)
    jobs.start()

    # Find or create creator profile
    existing = [c for c in creators.all_creators() if c.get("channel") == url]
    if existing:
        c = existing[0]
        creators.update(c["id"], {
            "layout": args.layout,
            "style": args.style,
            "captions": args.captions,
            "ai_hooks": args.ai_hooks,
            "ai_every_min": args.ai_every_min,
            "chat_spike_min_users": args.min_users,
            "buffer_min": args.buffer_min,
        })
        creator = creators.get(c["id"])
    else:
        creator = creators.create({
            "name": name.title() or "Streamer",
            "channel": url,
            "layout": args.layout,
            "style": args.style,
            "captions": args.captions,
            "ai_hooks": args.ai_hooks,
            "ai_every_min": args.ai_every_min,
            "chat_spike_min_users": args.min_users,
            "buffer_min": args.buffer_min,
        })

    out_target = Path(args.out_dir) if args.out_dir else None
    if out_target:
        out_target.mkdir(parents=True, exist_ok=True)

    def on_ready(job, clip):
        if job.get("creator") == creator["id"]:
            print(f"\n[CLIP READY] {clip['id']} | Length: {round(clip['end'] - clip['start'], 1)}s | Score: {clip.get('score', 0)}")
            print(f"  Title:    {clip.get('title') or clip.get('hook') or 'Untitled'}")
            if clip.get("reason"):
                print(f"  Reason:   {clip['reason']}")
            clip_dir = Path(job["dir"]) / "clips"
            print(f"  Video:    {clip_dir / clip.get('file', '')}")
            if clip.get("srt"):
                print(f"  Subs:     {clip_dir / clip.get('srt', '')}")
            if out_target:
                for ext in ("mp4", "jpg", "srt", "ass"):
                    f = clip_dir / f"{clip['id']}.{ext}"
                    if f.exists():
                        dest = out_target / f.name
                        shutil.copyfile(f, dest)
                print(f"  Exported: {out_target / (clip['id'] + '.mp4')}")
            print(flush=True)

    jobs.on_clip_ready.append(on_ready)

    running = True
    session = None
    sess_job = None

    def handle_signal(sig, frame):
        nonlocal running
        print("\n[Watcher] Stopping watcher...", flush=True)
        running = False
        if session:
            session.stop("Watcher stopped by user")

    try:
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)
    except (ValueError, AttributeError):
        pass

    while running and (stop_event is None or not stop_event.is_set()):
        try:
            print(f"[Watcher] Checking if {url} is live...", flush=True)
            try:
                live.resolve(url)
            except live.NotLive as e:
                print(f"[Watcher] Stream is offline ({e}). Waiting {args.poll_interval}s... (Ctrl+C to quit)", flush=True)
                for _ in range(args.poll_interval):
                    if not running or (stop_event and stop_event.is_set()):
                        break
                    time.sleep(1)
                continue

            print(f"[Watcher] Stream is LIVE! Connecting...", flush=True)
            sess_job = live.start_session(creator, url)
            session = live.SESSIONS.get(sess_job["id"])

            last_report = 0.0
            while running and session and not session.ended and (stop_event is None or not stop_event.is_set()):
                time.sleep(2)
                now = time.time()
                if now - last_report > 15:
                    last_report = now
                    j_live = sess_job.get("live") or {}
                    elapsed_min = round((session.samples / live.SR) / 60, 1)
                    buf_min = round(j_live.get("buffer_sec", 0) / 60, 1)
                    buf_mb = j_live.get("buffer_mb", 0)
                    clips_n = len(sess_job.get("clips", []))
                    sys.stdout.write(f"\r[Watcher Active] Recorded: {elapsed_min}m | Buffer: {buf_min}m ({buf_mb} MB) | Clips: {clips_n}   ")
                    sys.stdout.flush()

            if session and session.ended:
                print(f"\n[Watcher] Stream session ended: {session.end_note}", flush=True)
                session = None
                sess_job = None

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n[Watcher Error] {e}", flush=True)
            time.sleep(10)

    if session:
        session.stop("Watcher terminated")
    print("\n[Watcher] Shutdown complete. Goodbye.")
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    return run_watcher(args)


if __name__ == "__main__":
    sys.exit(main())
