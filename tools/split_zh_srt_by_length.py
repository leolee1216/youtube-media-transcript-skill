#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3}) --> (?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)
CONJUNCTIONS = (
    "但是",
    "不过",
    "然后",
    "因此",
    "所以",
    "而且",
    "并且",
    "如果",
    "因为",
    "就是",
    "比如",
    "例如",
    "同时",
    "然后",
    "而",
    "并",
)
HARD_BREAKS = "，。；：！？、"


@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text: str


def parse_timestamp(value: str) -> int:
    hours, minutes, sec_ms = value.split(":")
    seconds, millis = sec_ms.split(",")
    return (
        int(hours) * 3600000
        + int(minutes) * 60000
        + int(seconds) * 1000
        + int(millis)
    )


def format_timestamp(total_ms: int) -> str:
    hours, rem = divmod(total_ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8").strip()
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        match = TIME_RE.fullmatch(lines[1])
        if not match:
            raise ValueError(f"Invalid timestamp line: {lines[1]}")
        cues.append(
            Cue(
                start_ms=parse_timestamp(match.group("start")),
                end_ms=parse_timestamp(match.group("end")),
                text="".join(lines[2:]).strip(),
            )
        )
    return cues


def find_break_candidates(text: str) -> list[int]:
    candidates: set[int] = set()
    for index, char in enumerate(text[:-1], start=1):
        if char in HARD_BREAKS:
            candidates.add(index)
    for word in CONJUNCTIONS:
        start = 0
        while True:
            found = text.find(word, start)
            if found == -1:
                break
            if found > 0:
                candidates.add(found)
            end = found + len(word)
            if end < len(text):
                candidates.add(end)
            start = found + len(word)
    return sorted(idx for idx in candidates if 0 < idx < len(text))


def choose_break(text: str, limit: int, target: int) -> int:
    candidates = find_break_candidates(text)
    usable = [idx for idx in candidates if 6 <= idx <= min(limit, len(text) - 1)]
    if usable:
        return min(usable, key=lambda idx: (abs(idx - target), -idx))

    fallback_min = max(6, int(limit * 0.55))
    for idx in range(min(limit, len(text) - 1), fallback_min - 1, -1):
        if text[idx - 1].isspace():
            return idx
    return min(limit, len(text) - 1)


def split_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        remaining_parts = max(2, math.ceil(len(remaining) / max_chars))
        target = math.ceil(len(remaining) / remaining_parts)
        limit = min(max_chars, len(remaining) - 1)
        cut = choose_break(remaining, limit=limit, target=target)
        parts.append(remaining[:cut].strip(" ，；：、"))
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    return [part for part in parts if part]


def split_cue(cue: Cue, max_chars: int, min_duration_ms: int) -> list[Cue]:
    parts = split_text(cue.text, max_chars=max_chars)
    if len(parts) == 1:
        return [cue]

    total_duration = cue.end_ms - cue.start_ms
    if total_duration <= 0:
        return [cue]

    lengths = [max(1, len(part)) for part in parts]
    total_length = sum(lengths)

    durations = [max(min_duration_ms, round(total_duration * length / total_length)) for length in lengths]
    duration_sum = sum(durations)
    durations[-1] += total_duration - duration_sum

    if durations[-1] < min_duration_ms and len(durations) > 1:
        deficit = min_duration_ms - durations[-1]
        for index in range(len(durations) - 2, -1, -1):
            room = durations[index] - min_duration_ms
            if room <= 0:
                continue
            moved = min(room, deficit)
            durations[index] -= moved
            durations[-1] += moved
            deficit -= moved
            if deficit == 0:
                break

    current = cue.start_ms
    result: list[Cue] = []
    for index, part in enumerate(parts):
        end = cue.end_ms if index == len(parts) - 1 else current + durations[index]
        result.append(Cue(start_ms=current, end_ms=end, text=part))
        current = end
    return result


def render_srt(cues: list[Cue]) -> str:
    blocks = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_timestamp(cue.start_ms)} --> {format_timestamp(cue.end_ms)}",
                    cue.text,
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Split long Chinese SRT cues into shorter cues.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-chars", type=int, default=30)
    parser.add_argument("--min-duration-ms", type=int, default=900)
    args = parser.parse_args()

    cues = parse_srt(args.source)
    output_cues: list[Cue] = []
    for cue in cues:
        output_cues.extend(split_cue(cue, max_chars=args.max_chars, min_duration_ms=args.min_duration_ms))

    args.output.write_text(render_srt(output_cues), encoding="utf-8")


if __name__ == "__main__":
    main()
