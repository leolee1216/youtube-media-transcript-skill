---
name: burn-bilingual-subtitles
description: "Burn bilingual Chinese and English subtitles into video files after transcription and translation. Use when the user asks to @burn-bilingual-subtitles, burn/hardcode/烧制/嵌入中英文字幕, export a subtitled MP4 from a video plus .zh.srt and .en.srt files, or reproduce the established style: large yellow Chinese subtitle above smaller white English subtitle with thick black outlines."
---

# Burn Bilingual Subtitles

## Workflow

Use this skill to produce a final hard-subtitled MP4 after transcription and translation are complete.

1. Locate inputs.
   - Prefer files explicitly provided by the user.
   - Otherwise search the working folder for one video file plus matching `.zh.srt` and `.en.srt`.
   - Typical names are `Title.webm`, `Title.zh.srt`, and `Title.en.srt`.

2. Inspect before encoding.
   - Run `ffprobe` on the video for width, height, frame rate, duration, codecs, and audio stream.
   - Inspect the first and last few SRT entries to confirm timing overlap and final subtitle end time.
   - Check fonts with `fc-match`: prefer `PingFang SC` for Chinese and `Arial Black` for English.

3. Choose the burn path.
   - If `ffmpeg -filters` includes `subtitles`, use ffmpeg's native `subtitles` filter.
   - If `subtitles` is unavailable but `overlay` is available, use `scripts/render_bilingual_overlay.swift` to render a transparent subtitle layer, then overlay it with ffmpeg.
   - Do not stop just because `subtitles` is missing; the overlay fallback is the expected macOS path for ffmpeg builds without libass.

4. Preview first.
   - Render a 10-15 second preview and extract a PNG frame.
   - Verify Chinese is yellow, bold, black outlined, centered near the bottom, above the English line.
   - Verify English is white, bold, black outlined, centered below Chinese.
   - Fix placement or wrapping before exporting the full video.

5. Export final MP4.
   - Use H.264 video, AAC audio, `yuv420p`, and `-movflags +faststart`.
   - Default quality: `-crf 18 -preset medium -c:a aac -b:a 192k`.
   - Suggested output suffix: `.bilingual-burned.mp4`.

6. Verify final output.
   - Run `ffprobe` on the exported MP4.
   - Extract frames from early, middle, and late timestamps to check subtitle position and timing.
   - Report the final file path, duration, codecs, dimensions, and file size.

## Native ffmpeg Style

When `subtitles` is available, use two subtitle filters with this style baseline:

```bash
subtitles='INPUT.zh.srt':force_style='Fontname=PingFang SC,Fontsize=46,Bold=1,PrimaryColour=&H0000E6FF,OutlineColour=&H00000000,BorderStyle=1,Outline=5,Shadow=0,Alignment=2,MarginV=112',
subtitles='INPUT.en.srt':force_style='Fontname=Arial Black,Fontsize=34,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=52'
```

Be careful with spaces and quoting in filenames. If quoting becomes fragile, prefer the overlay fallback.

## Overlay Fallback

Use the bundled Swift renderer when native subtitle burning is unavailable:

```bash
env CLANG_MODULE_CACHE_PATH=/private/tmp/codex-swift-module-cache \
  swift /path/to/skill/scripts/render_bilingual_overlay.swift \
  "INPUT.zh.srt" "INPUT.en.srt" "_subtitle_render_full" VIDEO_DURATION_SECONDS "_subtitle_render_full/concat.txt" VIDEO_WIDTH VIDEO_HEIGHT

ffmpeg -y -f concat -safe 0 -i "_subtitle_render_full/concat.txt" \
  -fps_mode vfr -pix_fmt argb -c:v qtrle "_subtitle_render_full/subtitle_overlay.mov"

ffmpeg -y -i "INPUT_VIDEO" -i "_subtitle_render_full/subtitle_overlay.mov" \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]" \
  -map "[v]" -map 0:a:0 \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k -movflags +faststart \
  "OUTPUT.bilingual-burned.mp4"
```

Use the real duration from `ffprobe format=duration`. Keep temporary render folders beside the source unless the user asks for cleanup.

## Style Rules

- Chinese: `PingFang SC`, semibold if possible, size about `46` at 1080p, fill `#FFE600`, black outline `5px`.
- English: `Arial Black`, size about `34` at 1080p, fill white, black outline `4px`.
- Layout: bottom centered, English closest to bottom, Chinese above it with a small gap.
- For non-1080p videos, scale font sizes and bottom margins proportionally to video height.
- Preserve the original audio unless transcoding is required for MP4 compatibility.

## User Interaction

If the user says "先分析，确认后执行", stop after the inspection and preview plan until they confirm. Otherwise proceed through preview, full export, and verification in the same turn when feasible.
