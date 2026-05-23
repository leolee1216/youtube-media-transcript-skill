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
WHISPER_BACKEND="${WHISPER_BACKEND:-auto}"
WHISPER_CPP_BIN="${WHISPER_CPP_BIN:-/opt/homebrew/bin/whisper-cli}"
WHISPER_CPP_MODEL="${WHISPER_CPP_MODEL:-}"
WHISPER_CPP_THREADS="${WHISPER_CPP_THREADS:-8}"
WHISPER_INITIAL_PROMPT="Claude Code, Remotion, Playwright MCP, Tailwind CSS, Opus 4.6, Sonnet, Nano Banana Pro, GPT Image 2.5, Lottie, Zod schema, OpenCode, Void.dev, Envato, Replicate, 11labs, SVG, 3D assets, GIFs."

find_whisper_cpp_model() {
  local candidates=()
  if [[ -n "$WHISPER_CPP_MODEL" ]]; then
    candidates+=("$WHISPER_CPP_MODEL")
  fi
  candidates+=(
    "$ROOT_DIR/models/ggml-small.en.bin"
    "$ROOT_DIR/models/ggml-small.bin"
    "$ROOT_DIR/models/ggml-base.en.bin"
    "$ROOT_DIR/models/ggml-base.bin"
    "$HOME/.cache/whisper.cpp/ggml-small.en.bin"
    "$HOME/.cache/whisper.cpp/ggml-small.bin"
    "$HOME/.cache/whisper.cpp/ggml-base.en.bin"
    "$HOME/.cache/whisper.cpp/ggml-base.bin"
    "/opt/homebrew/share/whisper-cpp/ggml-small.en.bin"
    "/opt/homebrew/share/whisper-cpp/ggml-small.bin"
    "/opt/homebrew/share/whisper-cpp/ggml-base.en.bin"
    "/opt/homebrew/share/whisper-cpp/ggml-base.bin"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

resolve_whisper_engine() {
  case "$WHISPER_BACKEND" in
    auto|python|whispercpp) ;;
    *)
      echo "Unsupported WHISPER_BACKEND=$WHISPER_BACKEND. Use auto, python, or whispercpp." >&2
      exit 2
      ;;
  esac

  WHISPER_ENGINE="python"
  WHISPER_CPP_MODEL_PATH=""

  if [[ "$WHISPER_BACKEND" == "python" ]]; then
    return 0
  fi

  if [[ ! -x "$WHISPER_CPP_BIN" ]]; then
    if [[ "$WHISPER_BACKEND" == "whispercpp" ]]; then
      echo "Could not find executable whisper.cpp CLI at $WHISPER_CPP_BIN." >&2
      exit 1
    fi
    echo "whisper.cpp CLI not found; falling back to Python Whisper." >&2
    return 0
  fi

  if WHISPER_CPP_MODEL_PATH="$(find_whisper_cpp_model)"; then
    WHISPER_ENGINE="whispercpp"
    return 0
  fi

  if [[ "$WHISPER_BACKEND" == "whispercpp" ]]; then
    echo "Could not find a whisper.cpp ggml model. Set WHISPER_CPP_MODEL to a ggml model path." >&2
    exit 1
  fi

  echo "No whisper.cpp ggml model found; falling back to Python Whisper." >&2
}

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

resolve_whisper_engine

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
  echo "whisper_backend=$WHISPER_ENGINE"
  if [[ "$WHISPER_ENGINE" == "whispercpp" ]]; then
    echo "whisper_cpp_bin=$WHISPER_CPP_BIN"
    echo "whisper_cpp_model=$WHISPER_CPP_MODEL_PATH"
  else
    echo "whisper_bin=$RESOLVED_WHISPER"
  fi
  echo "started_at=$(date '+%Y-%m-%d %H:%M:%S')"
} > "$MANIFEST"

VIDEO_LOG="$LOGS_DIR/video.log"
AUDIO_LOG="$LOGS_DIR/audio.log"
WHISPER_LOG="$LOGS_DIR/whisper.log"
TRANSLATE_LOG="$LOGS_DIR/translate.log"
POLISH_LOG="$LOGS_DIR/polish.log"
SPLIT_LOG="$LOGS_DIR/split.log"

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

RAW_EN_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").srt"
EN_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").en.srt"
ZH_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").zh.srt"
RAW_ZH_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").zh.raw.srt"
POLISHED_ZH_SRT="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").zh.polished.srt"

if [[ "$WHISPER_ENGINE" == "whispercpp" ]]; then
  WHISPER_CPP_OUTPUT_BASE="$TRANSCRIPTS_DIR/$(basename "${AUDIO_FILE%.*}").whispercpp"
  "$WHISPER_CPP_BIN" \
    -m "$WHISPER_CPP_MODEL_PATH" \
    -f "$AUDIO_FILE" \
    -l en \
    -t "$WHISPER_CPP_THREADS" \
    --prompt "$WHISPER_INITIAL_PROMPT" \
    -osrt \
    -of "$WHISPER_CPP_OUTPUT_BASE" 2>&1 | tee "$WHISPER_LOG"
  mv "$WHISPER_CPP_OUTPUT_BASE.srt" "$EN_SRT"
else
  "$RESOLVED_WHISPER" \
    "$AUDIO_FILE" \
    --model small \
    --task transcribe \
    --language en \
    --output_dir "$TRANSCRIPTS_DIR" \
    --output_format srt 2>&1 | tee "$WHISPER_LOG"
  mv "$RAW_EN_SRT" "$EN_SRT"
fi

python3 "$ROOT_DIR/tools/translate_srt_en_to_zh.py" \
  "$EN_SRT" \
  "$RAW_ZH_SRT" 2>&1 | tee "$TRANSLATE_LOG"

python3 "$ROOT_DIR/tools/polish_zh_srt.py" \
  "$RAW_ZH_SRT" \
  "$POLISHED_ZH_SRT" 2>&1 | tee "$POLISH_LOG"

python3 "$ROOT_DIR/tools/split_zh_srt_by_length.py" \
  "$POLISHED_ZH_SRT" \
  "$ZH_SRT" 2>&1 | tee "$SPLIT_LOG"

rm -f "$RAW_ZH_SRT"
rm -f "$POLISHED_ZH_SRT"

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
  echo "split_log=$SPLIT_LOG"
} >> "$MANIFEST"

echo "Saved video to: $VIDEO_FILE"
echo "Saved audio to: $AUDIO_FILE"
echo "Saved English subtitles to: $EN_SRT"
echo "Saved Chinese subtitles to: $ZH_SRT"
