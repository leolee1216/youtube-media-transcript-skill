---
name: youtube-media-transcript
description: Download a YouTube video's media, create an English transcript draft, get user confirmation in chat, then translate to Chinese and get confirmation again before writing final subtitle files. Use when the user gives a YouTube link and wants the transcript/subtitle workflow handled with quality gates.
---

# YouTube Media Transcript

Use this skill when the user gives a YouTube link and wants a careful transcript/subtitle workflow.

The default mode is no longer "generate everything and deliver files." The default mode is staged confirmation:

1. Prepare media and English transcription draft.
2. Write an English draft SRT file and return its clickable file link in chat for user preview/confirmation.
3. Only after English confirmation, translate to Chinese.
4. Write a Chinese draft SRT file and return its clickable file link in chat for user preview/confirmation.
5. Only after Chinese confirmation, write final `.en.srt` and `.zh.srt` files.
6. Before writing final Chinese subtitles, automatically split long Chinese cues into shorter reading-friendly cues.

## First-Use Setup

When this skill is installed from the public GitHub repository on a new machine, do not assume the machine is already configured.

- Cloning or installing this skill copies instructions and bundled helper scripts only. It does not automatically install Homebrew packages, Python packages, Ollama, Ollama models, whisper.cpp ggml models, browser cookies, or Codex command approvals.
- If the user is setting this up for the first time, first ask Codex to clone the repo, run `./install_skill.sh`, and run `./setup_check.sh` from the repo root.
- If setup dependencies are missing, report the concrete missing tools and suggest the README commands. Do not silently install packages or pull large models unless the user approves.
- For local Ollama translation, confirm Ollama is running and `translategemma:4b` is available. If not, suggest `ollama pull translategemma:4b`.
- For Apple Silicon acceleration, prefer a production whisper.cpp model such as `ggml-small.en.bin` under `./models/`, `~/.cache/whisper.cpp/`, or `/opt/homebrew/share/whisper-cpp/`. Do not use Homebrew's `for-tests-ggml-tiny.bin` for production subtitles.
- In Codex Desktop, the first Ollama or whisper.cpp run may need persisted narrow command approval. Prefer these prefixes when prompted: `python3 tools/translate_srt_with_ollama.py`, `tools/run_youtube_media_subtitle_pipeline.sh`, and `/opt/homebrew/bin/whisper-cli`.

## Workspace

Use the user's active project workspace or the cloned repository root. Do not assume the original author's local path exists.

If this repository is present, prefer its `tools/` directory for legacy end-to-end scripts. If only the installed skill is available, use helper scripts from the installed skill's sibling `scripts/` directory.

Store working artifacts under:

`downloads/YYYY-MM-DD/<video-slug>/`

Keep each video's files flat in that folder. Do not create nested `youtube/`, `audio/`, `video/`, `transcripts/`, or `logs/` folders.

## Confirmation-First Workflow

When the user gives a YouTube URL:

1. Download the MP4 and MP3 and extract a transcription WAV from the final MP4.
2. Run Whisper on the WAV with word timestamps and generate an English draft SRT.
3. Run only conservative English cleanup.
4. Return a clickable link to the English draft SRT in chat. Do not paste the full subtitle text unless the user asks.
5. Ask the user to confirm or request edits.
6. After user confirmation, translate the confirmed English SRT into Chinese.
7. Return a clickable link to the Chinese draft SRT in chat. Do not paste the full subtitle text unless the user asks.
8. Ask the user to confirm or request edits.
9. After user confirmation, write final `.en.srt` and `.zh.srt` files and report paths.
10. Final `.zh.srt` should be the split version, not the unsplit draft.

Draft files are expected for confirmation preview. Name them clearly, for example `*.en.draft.srt` and `*.zh.draft.srt`. Do not present draft files as final deliverables. Final subtitle files are written only after both confirmation gates pass.

Only paste subtitle text into chat when the user explicitly asks for inline review of a section. Otherwise, provide clickable file links so the user can open the preview directly.

## English Transcription Standard

English transcript quality is judged by sentence integrity, readability, and audio alignment. The priority order is:

1. Timestamps must match the actual audio.
2. Each cue should preserve complete sentence meaning whenever possible.
3. If a sentence is too long for display, split it at natural punctuation or speech pauses.
4. Avoid arbitrary cuts that make a cue depend on the next line to be understood.

Rules:

- Use the final downloaded MP4 as the timing source. Extract its audio to `16kHz mono WAV` and run Whisper on that WAV, not on the standalone MP3.
- Keep the standalone MP3 for archive/listening only. MP3 can have encoder delay or a different time base from the video timeline.
- On Apple Silicon Macs, prefer `whisper.cpp` / `whisper-cli` with Metal acceleration for older automatic end-to-end runs when a real ggml model is available. Use `WHISPER_BACKEND=auto` to prefer `whisper.cpp` and fall back to Python Whisper, `WHISPER_BACKEND=whispercpp` to require it, or `WHISPER_BACKEND=python` for the original word-timestamp path.
- `whisper.cpp` requires a ggml model such as `ggml-small.en.bin`; set `WHISPER_CPP_MODEL=/path/to/ggml-small.en.bin` when the model is not in the default search locations. Do not use the Homebrew `for-tests-ggml-tiny.bin` model for production subtitles.
- In Codex Desktop, `whisper-cli` Metal execution may need the end-to-end pipeline command to run with a persisted narrow approval, similar to the Ollama translation command.
- Run Whisper with `--word_timestamps True` and `--output_format json`.
- Generate English SRT from Whisper JSON word timestamps with `tools/resegment_en_json_words.py`.
- Each cue timestamp must come from the first and last word in that cue. Do not allocate or redistribute cue times by character length, text length, or sentence proportion.
- Prefer full sentences as cue boundaries. A short or medium complete sentence may remain as one cue even if it is longer than older 15-word limits.
- For long sentences, split at punctuation first: `. ? ! ; : ,`.
- If punctuation is unavailable, split at natural clause boundaries such as `because`, `but`, `so`, `if`, `which`, `that`, `when`, `while`, or a clear speech pause.
- Avoid ending a cue with dangling connector words such as `and`, `that`, `for`, `with`, `to`, `because`, `but`, or `of`.
- Avoid isolated one-word cues unless the audio itself is an isolated one-word beat.
- Do not force every cue under 15 words. Use 15 words as a soft readability reference, not a hard rule.
- Prefer a practical cue range around 8-20 English words. Longer cues are acceptable when keeping the sentence intact is clearly better.
- If a cue exceeds roughly 22 English words, inspect it manually and split only where the meaning remains complete.
- For a complete sentence over roughly 18 English words, split on a natural comma, semicolon, or colon when both sides remain meaningful and each side has at least about 5 words.
- Allow natural connector splits such as `, and`, `, but`, or `, so` when the second half is a meaningful phrase of at least about 5 words.
- If a long sentence ends with a short comma-tail that carries the key information by itself, such as a demand, title, amount, slogan, date, or named object, split it into its own cue even if the tail is shorter than 5 words.
- Do not split at punctuation if it creates a dangling ending, a dangling beginning, or a tiny tail cue. Continue to avoid unsafe starts such as `in`, `with`, `to`, `of`, `or`, and `like` unless the phrase is clearly a complete sentence.
- Do not use filler insertions such as `you know` as preferred split points.
- Use real word timestamps for each side of the split; never estimate the split time by text length.

## Conservative Term Cleanup

Term normalization must not override the transcript blindly. It should fix obvious, high-confidence ASR mistakes only.

- Preserve product and proper names when clearly spoken: `OpenAI`, `ChatGPT`, `Codex`, `Claude Code`, `Remotion`, `GitHub`, `Vercel`, `Figma`, `Cursor`, `Windsurf`, `Playwright MCP`, `Lottie`, `Zod schema`, `React`, `TypeScript`, `Next.js`.
- Do not apply context-specific replacements unless the surrounding words support them.
- Do not rewrite ordinary words into product names just because a previous video used that product.
- If uncertain, leave the English transcript closer to the audio and flag the term in the chat for user review.

## Chinese Translation Standard

Translate only after the user confirms the English SRT draft.

Default translation method:

- Use LLM semantic translation as the default Chinese subtitle translation workflow.
- Default local Chinese subtitle translation model should be `translategemma:4b`.
- Run Chinese translation through `tools/translate_srt_with_ollama.py` with the Ollama CLI backend, for example `--model translategemma:4b --backend cli --batch-size 8`. Do not call `http://127.0.0.1:11434` directly from an ad-hoc Python snippet during normal skill use.
- In Codex Desktop, local network access to `127.0.0.1:11434` is blocked inside the normal workspace sandbox even when macOS Local Network permission is enabled. The working path is to run the translation script as the top-level command with a persisted narrow prefix approval.
- Use the persisted command prefix `python3 tools/translate_srt_with_ollama.py` for this workflow so future subtitle translations can run automatically while keeping the approval scope limited. If the prefix is missing and the translation script reports `operation not permitted`, request that exact persisted prefix once; do not switch models or rewrite the translation workflow.
- Do not use `tools/translate_srt_en_to_zh.py` / `Helsinki-NLP/opus-mt-en-zh` as the default path, because it is prone to inaccurate wording, weak context handling, and subtitle artifacts.
- Treat the Helsinki local model only as an offline fallback when the user explicitly accepts lower quality or no LLM/network option is available.
- Translate in batches if needed, but preserve each SRT cue number and timestamp exactly.
- Use the confirmed English SRT as the source of truth. Do not translate from Whisper logs, raw transcript text, or already-polished Chinese output.
- Prefer natural Chinese meaning over word-for-word translation, while keeping product names and technical terms stable.

Chinese subtitle requirements:

- Keep exactly the same cue numbers and timestamps as the confirmed English SRT.
- Translate meaning naturally, not word by word.
- Do not merge, delete, or renumber cues.
- Do not change timestamps during translation.
- Avoid machine-translation artifacts such as `，。`, repeated `。。`, duplicated phrases, or residual English sentence fragments.
- In AI/Codex/Claude contexts, translate `agent` as `智能体`, not `代理` or `特工`.
- In AI contexts, translate `training data` as `训练数据`, not `培训数据`.
- In AI/product contexts, translate `prompt` as `提示词`, not `快速`.
- In technical AI/model contexts, preserve `token` as the English word `token`. Do not translate it as `标记`.
- Preserve `GitHub` as the English product name.
- Preserve product names where natural: `OpenAI`, `ChatGPT`, `Codex`, `Claude Code`, `Remotion`, `Vercel`, `Figma`, `Cursor`, `Windsurf`, `React`, `TypeScript`, `Next.js`.

## Chinese Split Subtitle Standard

After the Chinese translation is confirmed and polished, generate the final Chinese subtitle as a split-reading version.

- The final Chinese `.zh.srt` is allowed to have more cues than the English `.en.srt`.
- Do not change the total time range of the video.
- Any Chinese cue longer than about `30` visible characters should be split into smaller consecutive cues.
- Treat `30` visible characters as a readability target, not a hard guillotine. A slightly longer cue is better than a semantically broken split.
- Prefer semantic-safe breakpoints first: `，` `。` `；` `：` and natural connector phrases such as `但是` `不过` `然后` `所以` `因此` `而且` `并且` `如果` `因为` `比如` `例如`.
- Give comma/clause boundaries higher priority than mechanically balanced length. For sentences like `..., 但...`, `..., 因为...`, `..., 然后...`, or `..., 而...`, split at the comma/clause boundary when both sides are meaningful, even if the two sides are uneven in length.
- Keep short but complete setup phrases when they introduce a clear second clause. Examples: `流程包括设置 Git， / 然后连接到 GitHub...`, `另外，存储也是一个环节， / 因为...`, `这次我会在浏览器中打开应用程序， / 因为...`.
- Prefer splitting immediately before strong semantic starts such as `开始时`, `名为 ...`, `选择了 ...`, `API 密钥 ...`, and `Claude Code ...` when that keeps the technical term or named object intact.
- Avoid breaking in places that leave a dangling fragment with incomplete meaning.
- Do not end a split Chinese cue with a bare connector such as `并` `并且` `而` `但` `和` `或` `与` `及` `且`.
- Do not create a split Chinese cue that is reduced to a connector-led fragment with little standalone meaning just because it fit the length limit.
- Avoid splitting product names, tool names, filenames, code identifiers, or mixed ASCII terms in the middle, such as `Higgs Field Cinema Studio`, `Claude Code`, `OpenRouter`, `CLAUDE.md`, `.env.local`, `futurefuel-can.png`, `API key`, or version labels.
- Do not leave quote/opening-marker fragments such as `名为“` or `一个叫` by themselves. Keep the quoted/named object with the phrase that introduces it.
- If a connector phrase is immediately followed by an English product/tool name, prefer ending the previous cue with the connector phrase and keeping the next cue as the full product/tool name, instead of leaving a connector-led fragment attached to the English name.
- Do not force-split a mildly long cue, roughly `31-35` visible characters, if the only available split would create a tiny tail, a pure punctuation cue, a broken product/file name, or an awkward fragment. In that case, keep it as one cue and flag it only if visual density becomes a real issue.
- For split cues, assign consecutive timestamps inside the original cue range. The combined split cue durations must exactly equal the original Chinese cue duration.
- When distributing time across split cues, use text-length proportion with a minimum-duration safeguard rather than equal splits.
- The split step should run with `tools/split_zh_srt_by_length.py` unless the user asks for a different rule.

## Quality Checks Before Chat Confirmation

Before returning the English draft in chat:

- Cue numbers are sequential.
- Timestamps are strictly valid: `end > start`, no backwards timestamps.
- Spot-check early, middle, and late sections for timing plausibility.
- Check long cues manually. Split only if it improves readability without breaking meaning.
- Search for obvious ASR term errors, but keep corrections conservative.

Before returning the Chinese draft in chat:

- Chinese cue count equals confirmed English cue count.
- Every Chinese cue timestamp exactly matches the English cue timestamp.
- Search for `，。`, `。。`, repeated characters, repeated phrases, residual English fragments, `代理`, `特工`, `培训数据`, and `快速`.
- Search for technical mistranslations such as `token -> 标记`, and restore `token` where the source cue is discussing model context, attention, memory, or training.
- Check product/technical terms manually in context, especially `prompt`, `agent`, `training data`, `GitHub`, `OpenAI`, `ChatGPT`, `Codex`, and video/image-generation terms.
- Scan for likely truncated Chinese cues after translation or splitting. Treat very short fragments ending in incomplete phrasing such as `与。`, `的。`, `可以看到`, `这些就像。`, or obviously missing noun phrases as defects, and repair them against the same-time English cue.
- If a Chinese defect is found, repair that cue by comparing against the same-numbered English cue. Do not change cue numbers or timestamps.

Before writing final Chinese subtitles after confirmation:

- Run the split step for long Chinese cues.
- Verify the final split Chinese SRT has no cue text longer than `30` visible characters unless the user explicitly asked to keep longer lines.
- Verify the final split Chinese SRT still begins and ends at the same timestamps as the pre-split Chinese draft.
- Scan the final split Chinese SRT for dangling connector tails such as a cue ending in `并` or `并且`, and repair them before handoff.
- Scan the final split Chinese SRT for split artifacts and repair them before handoff: pure punctuation cues, one-character tails, opening-quote fragments, filename/product-name fragments, and Chinese words visibly cut in half.
- When a user gives split-review feedback, compare it against the previous automatic split and update the split rules if the feedback reveals a repeated preference rather than a one-off correction.

## If Timing Drift Is Reported

- Do not keep tweaking translated text first.
- Return to the transcription layer.
- Re-extract WAV from MP4.
- Re-run Whisper word-level transcription if needed.
- Rebuild English SRT from word timestamps.
- Return a clickable link to the rebuilt English draft SRT for confirmation before translating.

## Legacy End-to-End Pipeline

`tools/run_youtube_media_subtitle_pipeline.sh` exists for older fully automated runs. Do not use it as the default for this skill unless the user explicitly asks for automatic end-to-end generation without confirmation.

For this skill's default behavior, use the same underlying tools step by step and keep confirmation gates in the chat.
