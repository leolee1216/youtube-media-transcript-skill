# YouTube Media Transcript Skills

Shareable Codex skills for a YouTube subtitle workflow:

- `youtube-media-transcript`: download YouTube media, create an English SRT draft, translate to Chinese, and write final subtitle files after confirmation.
- `burn-bilingual-subtitles`: burn confirmed Chinese and English subtitles into an MP4 with the established bilingual style.

The workflow is designed for careful staged review: English draft first, Chinese draft second, final files only after confirmation.

## Repository Layout

```text
skills/
  youtube-media-transcript/
    SKILL.md
    scripts/
      resegment_en_json_words.py
      split_zh_srt_by_length.py
      translate_srt_with_ollama.py
      polish_zh_srt.py
      normalize_en_srt_terms.py
      clean_srt_rollup.py
  burn-bilingual-subtitles/
    SKILL.md
    scripts/
      render_bilingual_overlay.swift
    agents/
      openai.yaml
install_skill.sh
setup_check.sh
requirements.txt
```

## Requirements

Recommended environment:

- macOS
- Codex desktop app
- Python 3.9+
- `yt-dlp`
- `ffmpeg` and `ffprobe`
- OpenAI Whisper CLI
- Optional but recommended on Apple Silicon: `whisper.cpp` CLI (`whisper-cli`) plus a production ggml model such as `ggml-small.en.bin`
- Ollama with `translategemma:4b`

Codex can help run these checks and commands, but cloning this repository does not automatically install Homebrew packages, Python packages, Ollama models, browser access, or Codex command approvals. A new user should expect a one-time setup pass before the first real video job.

Install common dependencies:

```bash
brew install yt-dlp ffmpeg whisper-cpp
pip3 install -r requirements.txt
ollama pull translategemma:4b
```

Keep Ollama running before asking Codex to translate Chinese subtitles. In Codex Desktop, use the persisted narrow command prefix `python3 tools/translate_srt_with_ollama.py` for this workflow; direct sandbox access to `127.0.0.1:11434` may be blocked.

For whisper.cpp acceleration, place a production ggml model in one of these locations:

```text
./models/ggml-small.en.bin
~/.cache/whisper.cpp/ggml-small.en.bin
/opt/homebrew/share/whisper-cpp/ggml-small.en.bin
```

The Homebrew test model `for-tests-ggml-tiny.bin` is only for smoke tests and should not be used for production subtitles.

## Install Skills

Clone this repo and run:

```bash
./install_skill.sh
```

This copies both skills into:

```text
~/.codex/skills/
```

Then restart Codex or start a new Codex thread if the skills do not appear immediately.

## Check Setup

Run:

```bash
./setup_check.sh
```

The check verifies the main command-line tools and confirms whether Ollama can see `translategemma:4b`.

## First Run In Codex

Give Codex the GitHub URL and ask it to clone the repo, install the skills, and run the setup check. A useful prompt is:

```text
Clone https://github.com/leolee1216/youtube-media-transcript-skill, run ./install_skill.sh, run ./setup_check.sh, and tell me what dependencies or models still need setup.
```

On the first actual job, Codex may ask for narrow persisted approvals. Prefer allowing these exact prefixes when prompted:

```text
python3 tools/translate_srt_with_ollama.py
tools/run_youtube_media_subtitle_pipeline.sh
/opt/homebrew/bin/whisper-cli
```

These approvals let Codex reach local Ollama and run Metal-accelerated whisper.cpp without asking every time.

## Usage

For transcription and translation, paste a YouTube URL into Codex and ask it to use `youtube-media-transcript`.

The default flow is:

1. Download MP4 and MP3.
2. Extract WAV from the final MP4.
3. Run Whisper with word timestamps.
4. Generate an English draft SRT.
5. Wait for user confirmation.
6. Translate to Chinese with `translategemma:4b`.
7. Wait for user confirmation.
8. Write final `.en.srt` and split `.zh.srt`.

For hard-subtitled video export, ask Codex to use `burn-bilingual-subtitles` with a video plus matching `.en.srt` and `.zh.srt`.

## Notes

- The Chinese translation path currently favors quality over speed and uses `translategemma:4b`.
- Automatic end-to-end runs support `WHISPER_BACKEND=auto|whispercpp|python`. On Apple Silicon, `auto` prefers `whisper-cli` with Metal acceleration when a ggml model is available, then falls back to Python Whisper.
- Set `WHISPER_CPP_MODEL=/path/to/ggml-small.en.bin` when the ggml model is not under `./models`, `~/.cache/whisper.cpp`, or `/opt/homebrew/share/whisper-cpp`.
- Codex should run Chinese translation through `tools/translate_srt_with_ollama.py --backend cli`; approve and persist the prefix `python3 tools/translate_srt_with_ollama.py` once if prompted.
- Technical terms are intentionally protected, including `agent -> 智能体`, `prompt -> 提示词`, `training data -> 训练数据`, and preserving `token`, `GitHub`, `OpenAI`, `ChatGPT`, `Codex`, and `Claude Code`.
- Final Chinese subtitles are split for readability, with checks to avoid dangling connector fragments such as a cue ending with `并` or `并且`.
- The bilingual burn skill uses native `ffmpeg` subtitle rendering when available and a bundled Swift/AppKit overlay fallback on macOS.
