#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from transformers import pipeline


TIME_RE = re.compile(
    r"(\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d)"
)


@dataclass
class Cue:
    index: int
    timing: str
    text: str


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    blocks = [block for block in raw.split("\n\n") if block.strip()]
    cues: list[Cue] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        timing = lines[1].strip()
        if not TIME_RE.fullmatch(timing):
            continue
        text = "\n".join(line.strip() for line in lines[2:]).strip()
        if text:
            cues.append(Cue(index=index, timing=timing, text=text))
    return cues


def write_srt(path: Path, cues: list[Cue]) -> None:
    chunks = []
    for new_index, cue in enumerate(cues, start=1):
        chunks.append(f"{new_index}\n{cue.timing}\n{cue.text}\n")
    path.write_text("\n".join(chunks), encoding="utf-8")


def restore_terms(source: str, translated: str) -> str:
    fixed = translated
    if "codex" in source.lower():
        replacements = [
            ("最终代码", "Codex"),
            ("代码指南", "Codex 指南"),
            ("使用密码", "使用 Codex"),
            ("使用编码", "使用 Codex"),
            ("使用代码", "使用 Codex"),
            ("教代码", "教 Codex"),
            ("编码, 你不需要", "Codex，你不需要"),
            ("编码，你不需要", "Codex，你不需要"),
            ("代码 CLI", "Codex CLI"),
            ("密码 CLI", "Codex CLI"),
            ("代码扩展", "Codex 扩展"),
            ("密码扩展", "Codex 扩展"),
            ("代码", "Codex"),
            ("密码", "Codex"),
        ]
        for old, new in replacements:
            fixed = fixed.replace(old, new)
    if "openai" in source.lower():
        fixed = fixed.replace("开放人工智能", "OpenAI").replace("开放AI", "OpenAI")
    if "vectal" in source.lower():
        fixed = fixed.replace("维克塔尔", "Vectal").replace("vectal", "Vectal")
    if "github" in source.lower():
        fixed = fixed.replace("吉特胡布", "GitHub").replace("github", "GitHub")
    if "cursor" in source.lower():
        fixed = fixed.replace("光标", "Cursor").replace("cursor", "Cursor")
    if "vscode" in source.lower() or "vs code" in source.lower():
        fixed = fixed.replace("视觉工作室代码", "VS Code").replace("vs 代码", "VS Code")
    return fixed


def translate_texts(texts: list[str], model_name: str, batch_size: int) -> list[str]:
    translator = pipeline(
        "translation",
        model=model_name,
        tokenizer=model_name,
        device=-1,
    )

    results: list[str] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        outputs = translator(batch, max_length=512)
        for item in outputs:
            translated = item["translation_text"].strip()
            results.append(translated)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_srt")
    parser.add_argument("output_srt")
    parser.add_argument(
        "--model",
        default="Helsinki-NLP/opus-mt-en-zh",
        help="Hugging Face model name",
    )
    parser.add_argument("--batch-size", type=int, default=12)
    args = parser.parse_args()

    input_path = Path(args.input_srt)
    output_path = Path(args.output_srt)
    cues = parse_srt(input_path)
    translations = translate_texts([cue.text for cue in cues], args.model, args.batch_size)

    translated_cues = []
    for cue, text in zip(cues, translations):
        translated_cues.append(
            Cue(index=cue.index, timing=cue.timing, text=restore_terms(cue.text, text))
        )
    write_srt(output_path, translated_cues)
    print(f"translated {len(cues)} cues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
