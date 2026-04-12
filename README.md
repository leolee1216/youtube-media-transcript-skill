# youtube-media-transcript-skill

A shareable Codex workflow for:

- downloading YouTube `mp4` and `mp3`
- generating English `srt` subtitles with Whisper
- translating subtitles into Chinese `srt`
- organizing outputs in dated per-video folders

## What This Repo Contains

- `tools/run_youtube_media_subtitle_pipeline.sh`: the main end-to-end workflow
- `tools/translate_srt_en_to_zh.py`: English-to-Chinese subtitle translation
- `tools/polish_zh_srt.py`: light Chinese subtitle polishing
- `skill-template/SKILL.template.md`: the skill template used during installation
- `install_skill.sh`: installs the skill into `~/.codex/skills`

## Prerequisites

- macOS or Linux
- `yt-dlp`
- `ffmpeg`
- Python 3.9+
- a working `whisper` CLI
- Chrome cookies available for YouTube access

Python packages:

```bash
pip install openai-whisper transformers sentencepiece
```

## Installation

1. Clone this repo somewhere stable:

```bash
git clone <your-repo-url>
cd youtube-media-transcript-skill
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install the Codex skill:

```bash
./install_skill.sh
```

This creates:

`~/.codex/skills/youtube-media-transcript/SKILL.md`

and points it at your cloned repo path.

## Usage In Codex

In a Codex thread, either:

- paste a YouTube link and ask to use the `youtube-media-transcript` skill
- or run the workflow directly from this repo

## Direct CLI Usage

```bash
./tools/run_youtube_media_subtitle_pipeline.sh "<youtube-url>"
```

Optional arguments:

```bash
./tools/run_youtube_media_subtitle_pipeline.sh "<youtube-url>" 2026-04-12 chrome
```

## Output Layout

Outputs are stored in:

`downloads/youtube/YYYY-MM-DD/<video-slug>/`

Inside each item folder:

- `video/`: MP4
- `audio/`: MP3
- `transcripts/`: `*.en.srt` and `*.zh.srt`
- `logs/`: workflow logs
- `manifest.txt`: job metadata and output paths

## Publish To GitHub

After reviewing the repo locally:

```bash
git init
git add .
git commit -m "Add youtube media transcript skill"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
