#!/usr/bin/env bash
set -euo pipefail

missing=0

check_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    echo "OK   $name: $(command -v "$name")"
  else
    echo "MISS $name"
    missing=1
  fi
}

check_cmd python3
check_cmd yt-dlp
check_cmd ffmpeg
check_cmd ffprobe
check_cmd whisper
check_cmd ollama
check_cmd swift

echo
if command -v whisper-cli >/dev/null 2>&1; then
  echo "OK   whisper.cpp CLI available for WHISPER_BACKEND=whispercpp"
  if find "$PWD/models" "$HOME/.cache/whisper.cpp" "/opt/homebrew/share/whisper-cpp" \
    -maxdepth 1 \
    \( -name 'ggml-small.en.bin' -o -name 'ggml-small.bin' -o -name 'ggml-base.en.bin' -o -name 'ggml-base.bin' \) \
    -print -quit 2>/dev/null | grep -q .; then
    echo "OK   whisper.cpp ggml model found"
  else
    echo "WARN No production whisper.cpp ggml model found."
    echo "     Set WHISPER_CPP_MODEL=/path/to/ggml-small.en.bin or place it under ./models or ~/.cache/whisper.cpp."
  fi
fi

echo
if command -v ollama >/dev/null 2>&1; then
  if ollama list 2>/dev/null | grep -q 'translategemma:4b'; then
    echo "OK   Ollama model: translategemma:4b"
  else
    echo "WARN Ollama model translategemma:4b was not found."
    echo "     Run: ollama pull translategemma:4b"
  fi
fi

if [[ "$missing" -ne 0 ]]; then
  echo
  echo "Some required commands are missing. Install them before using the skills."
  exit 1
fi

echo
echo "Setup check completed."
