#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


TIME_RE = re.compile(
    r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)"
)


@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text: str


def parse_ts(parts: tuple[str, str, str, str]) -> int:
    hh, mm, ss, ms = map(int, parts)
    return ((hh * 60 + mm) * 60 + ss) * 1000 + ms


def fmt_ts(total_ms: int) -> str:
    hh = total_ms // 3_600_000
    total_ms %= 3_600_000
    mm = total_ms // 60_000
    total_ms %= 60_000
    ss = total_ms // 1000
    ms = total_ms % 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    cues: list[Cue] = []
    lines = raw.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.isdigit():
            i += 1
            if i >= len(lines):
                break
            line = lines[i].strip()
        match = TIME_RE.fullmatch(line)
        if not match:
            i += 1
            continue
        start_ms = parse_ts(match.groups()[:4])
        end_ms = parse_ts(match.groups()[4:])
        i += 1
        text_lines: list[str] = []
        while i < len(lines):
            current = lines[i]
            stripped = current.strip()
            if stripped.isdigit() and i + 1 < len(lines) and TIME_RE.fullmatch(lines[i + 1].strip()):
                break
            if TIME_RE.fullmatch(stripped):
                break
            text_lines.append(current)
            i += 1
        text = normalize_text("\n".join(text_lines))
        if text:
            cues.append(Cue(start_ms, end_ms, text))
    return cues


def common_prefix_len(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    idx = 0
    while idx < limit and a[idx] == b[idx]:
        idx += 1
    return idx


def trim_prefixed_text(prev: str, current: str) -> str:
    prefix_len = common_prefix_len(prev, current)
    if prefix_len == 0:
        return current

    shared = current[:prefix_len]
    # Only trim when the current cue is mostly a roll-up extension of the previous one.
    if len(shared.strip()) < 8:
        return current
    if prefix_len < max(12, int(len(current) * 0.45)):
        return current

    trimmed = current[prefix_len:]
    trimmed = trimmed.lstrip(" \n")
    if trimmed.startswith((".", ",", "!", "?", ";", ":", "，", "。", "！", "？", "；", "：")):
        trimmed = trimmed[1:].lstrip()
    return trimmed or current


def clean_cues(cues: list[Cue]) -> list[Cue]:
    cleaned: list[Cue] = []
    prev_text = ""
    for cue in cues:
        duration_ms = cue.end_ms - cue.start_ms
        text = cue.text.replace("\n \n", "\n").strip()
        if not text:
            continue

        # Drop tiny transitional cues that just repeat the previous subtitle.
        if duration_ms <= 80 and prev_text and (
            text == prev_text or prev_text.endswith(text) or text.endswith(prev_text)
        ):
            continue

        if prev_text:
            text = trim_prefixed_text(prev_text, text)

        if cleaned and text == cleaned[-1].text:
            cleaned[-1].end_ms = cue.end_ms
            prev_text = cleaned[-1].text
            continue

        cleaned.append(Cue(cue.start_ms, cue.end_ms, text))
        prev_text = text
    return cleaned


def write_srt(path: Path, cues: list[Cue]) -> None:
    chunks = []
    for idx, cue in enumerate(cues, start=1):
        chunks.append(
            f"{idx}\n{fmt_ts(cue.start_ms)} --> {fmt_ts(cue.end_ms)}\n{cue.text}\n"
        )
    path.write_text("\n".join(chunks), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: clean_srt_rollup.py <input.srt> <output.srt>", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    cues = parse_srt(input_path)
    cleaned = clean_cues(cues)
    write_srt(output_path, cleaned)
    print(f"cleaned {len(cues)} -> {len(cleaned)} cues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
