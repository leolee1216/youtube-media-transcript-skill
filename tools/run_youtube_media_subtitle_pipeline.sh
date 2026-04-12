#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
  echo "Usage: $0 <youtube-url> [date-folder] [browser]" >&2
  echo "Example: $0 'https://www.youtube.com/watch?v=hoCWD1aI60Y' 2026-04-12 chrome" >&2
  exit 2
fi

URL="$1"
DATE_FOLDER="${2:-$(date +%F)}"
BROWSER="${3:-chrome}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DAY_DIR="$ROOT_DIR/downloads/youtube/$DATE_FOLDER"

if [[ -n "${WHISPER_BIN:-}" ]]; then
  RESOLVED_WHISPER="$WHISPER_BIN"
elif command -v whisper >/dev/null 2>&1; then
  RESOLVED_WHISPER="$(command -v whisper)"
elif [[ -x "$HOME/Library/Python/3.9/bin/whisper" ]]; then
  RESOLVED_WHISPER="$HOME/Library/Python/3.9/bin/whisper"
else
  echo "Could not find whisper CLI. Set WHISPER_BIN or install openai-whisper." >&2
  exit 1
fi

mkdir -p "$DAY_DIR"
TITLE="$(yt-dlp --cookies-from-browser "$BROWSER" --get-title "$URL" | tail -n 1 | tr -d '\r')"

if [[ -z "$TITLE" ]]; then
  echo "Failed to resolve title for $URL" >&2
  exit 1
fi

SLUG="$(
TITLE="$TITLE" python3 - <<'PY'
import os
import re
title = os.environ["TITLE"].strip().lower()
title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
title = re.sub(r"[-\s]+", "-", title).strip("-")
print(title or "youtube-item")
PY
)"

ITEM_DIR="$DAY_DIR/$SLUG"
VIDEO_DIR="$ITEM_DIR/video"
AUDIO_DIR="$ITEM_DIR/audio"
TRANSCRIPTS_DIR="$ITEM_DIR/transcripts"
LOGS_DIR="$ITEM_DIR/logs"
MANIFEST="$ITEM_DIR/manifest.txt"

mkdir -p "$VIDEO_DIR" "$AUDIO_DIR" "$TRANSCRIPTS_DIR" "$LOGS_DIR"

{
  echo "date=$DATE_FOLDER"
  echo "title=$TITLE"
  echo "slug=$SLUG"
  echo "url=$URL"
  echo "browser=$BROWSER"
  echo "started_at=$(date '+%Y-%m-%d %H:%M:%S')"
} > "$MANIFEST"

VIDEO_LOG="$LOGS_DIR/video.log"
AUDIO_LOG="$LOGS_DIR/audio.log"
WHISPER_LOG="$LOGS_DIR/whisper.log"
TRANSLATE_LOG="$LOGS_DIR/translate.log"
POLISH_LOG="$LOGS_DIR/polish.log"

VIDEO_FILE="$(
  yt-dlp \
    --cookies-from-browser "$BROWSER" \
    --no-progress \
    -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b" \
    --merge-output-format mp4 \
    --print after_move:filepath \
    -o "$VIDEO_DIR/%(title)s.%(ext)s" \
    "$URL" 2>&1 | tee "$VIDEO_LOG" | tail -n 1
)"

AUDIO_FILE="$(
  yt-dlp \
    --cookies-from-browser "$BROWSER" \
    --no-progress \
    -x \
    --audio-format mp3 \
    --print after_move:filepath \
    -o "$AUDIO_DIR/%(title)s.%(ext)s" \
    "$URL" 2>&1 | tee "$AUDIO_LOG" | tail -n 1
)"

"$RESOLVED_WHISPER" \
  "$AUDIO_FILE" \
  --model base \
  --task transcribe \
  --language en \
  --output_dir "$TRANSCRIPTS_DIR" \
  --output_format srt 2>&1 | tee "$WHISPER_LOG"

RAW_EN_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").srt"
EN_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").en.srt"
ZH_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").zh.srt"
RAW_ZH_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").zh.raw.srt"

mv "$RAW_EN_SRT" "$EN_SRT"

python3 "$ROOT_DIR/tools/translate_srt_en_to_zh.py" \
  "$EN_SRT" \
  "$RAW_ZH_SRT" 2>&1 | tee "$TRANSLATE_LOG"

python3 "$ROOT_DIR/tools/polish_zh_srt.py" \
  "$RAW_ZH_SRT" \
  "$ZH_SRT" 2>&1 | tee "$POLISH_LOG"

rm -f "$RAW_ZH_SRT"

{
  echo "finished_at=$(date '+%Y-%m-%d %H:%M:%S')"
  echo "video_file=$VIDEO_FILE"
  echo "audio_file=$AUDIO_FILE"
  echo "en_srt=$EN_SRT"
  echo "zh_srt=$ZH_SRT"
  echo "video_log=$VIDEO_LOG"
  echo "audio_log=$AUDIO_LOG"
  echo "whisper_log=$WHISPER_LOG"
  echo "translate_log=$TRANSLATE_LOG"
  echo "polish_log=$POLISH_LOG"
} >> "$MANIFEST"

echo "Saved video to: $VIDEO_FILE"
echo "Saved audio to: $AUDIO_FILE"
echo "Saved English subtitles to: $EN_SRT"
echo "Saved Chinese subtitles to: $ZH_SRT"
