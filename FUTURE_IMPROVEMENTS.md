# Future Improvements & Architectural Roadmap

This document outlines key architectural and feature enhancements identified from comparing PeakCut with lightweight stream clipping workflows (e.g., Clip-Watcher), focusing on maximizing performance, output quality, and slashing AI token consumption.

---

## 1. Event-Driven Twitch IRC Spike Gatekeeper (Zero-Token Detection) - [IMPLEMENTED]

### Architecture in PeakCut
- Connected anonymously to Twitch chat via IRC (`irc.chat.twitch.tv:6697` using `NICK justinfan<id>`).
- Sliding 10-second chatter buckets with 3-minute rolling median calculation (`studio/chat_spike.py`).
- Emote/bot deduplication requiring distinct human chatters (`min_users >= 5`, velocity $\ge 2.5\times$ rolling median).
- Integrated into `Session._watch_spikes()` in `studio/live.py`.
- Option to run in pure zero-token mode (`ai_every_min: 0`).
- **Verified**: `tests/test_chat_spike.py` (19/19 checks passed).

---

## 2. Selective AI Token Optimization (90–95% Cost Reduction) - [IMPLEMENTED]

### Architecture in PeakCut
- Decoupled detection from AI analysis:
  1. **Phase 1 (Heuristic Detection)**: IRC spike gatekeeper flags candidate timestamps without any AI tokens.
  2. **Phase 2 (Targeted AI Enhancement)**: If `ai_hooks` is enabled, sends *only* the 30-second transcript snippet (~100 tokens) via `brain.enhance_spike_clip()`.
  3. **Sentence Boundary Snapping**: Refines start and end boundaries to complete sentences.
- **Verified**: `tests/test_token_opt.py` (19/19 checks passed).

---

## 3. High-Performance Local Transcription Pipeline - [IMPLEMENTED]

### Architecture in PeakCut
- Streaming local ASR (`sherpa-onnx` Moonshine/Zipformer) runs with near-zero latency and no GPU requirement.
- Implemented `transcribe.clean_asr_words()` to clean repetition loops and zero-duration artifacts.
- Word-level SubRip (`.srt`) subtitle generator in `studio/render.py` alongside ASS styles.
- Added one-click `.srt` download button in the web UI clip dialog.
- **Verified**: `tests/test_transcribe_pipeline.py` (12/12 checks passed).

---

## 4. Enhanced 9:16 Framing & Visual Composition - [IMPLEMENTED]

### Architecture in PeakCut
- **Smart Facecam Stacked (`stacked`)**:
  - Upper screen ($1080 \times 720$): Cropped streamer facecam.
  - Lower screen ($1080 \times 1200$): Center-cropped gameplay action.
  - Stacked via FFmpeg `vstack=inputs=2`, with divider hook at $Y=720$ and captions at $Y=1500$.
- **Robust Facecam Detection & Fallback**:
  - Fixed short-clip `.ts` framerate calculation and relaxed confidence discard.
  - Added corner motion/stillness fallback (`_corner_fallback`) for borderless or low-contrast facecams (e.g. dark rooms).
  - Added JSON response parsing support for AI vision models.
- **Verified**: `tests/test_framing_layout.py` (27/27 checks passed).

---

## 5. Circular Rolling Buffers vs. Unbounded Disk Storage - [IMPLEMENTED]

### Architecture in PeakCut
- Configurable circular rolling buffer (`SEG_SEC = 6s`, default 20 min).
- Dynamic disk headroom guard: Automatically contracts retention window if disk space drops below 1.5 GB; safely halts if critically low (< 250 MB).
- Pending clip protection: Retains segments required by queued clips until extracted into `clips/{id}.src.ts`.
- Orphan segment scavenger: Unlinks abandoned `.ts` chunks from previous disconnects.
- Real-time buffer footprint accounting (`buffer_mb`) shown on the web UI live card.
- **Verified**: `tests/test_rolling_buffer.py` (13/13 checks passed).

---

## 6. Headless CLI / Watcher Mode (`watch.sh` / `python -m studio.watch`) - [IMPLEMENTED]

### Architecture in PeakCut
- Lightweight terminal watcher CLI in `studio/watch.py` executable as:
  ```bash
  python -m studio.watch <twitch_channel> --min 5 --layout stacked --ai-hooks --out ./clips
  ```
- Provided convenience scripts: `watch.bat` (Windows) and `watch.sh` (Linux/macOS).
- Monitors stream status, connects when live, tracks IRC chat spikes, auto-extracts clips, and exports `.mp4`, `.srt`, `.ass`, and `.jpg` to a target folder.
- Terminal statistics reporting and graceful `Ctrl+C` shutdown.
- **Verified**: `tests/test_watch_cli.py` (21/21 checks passed).
