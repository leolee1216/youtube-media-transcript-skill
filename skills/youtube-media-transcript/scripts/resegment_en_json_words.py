#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


# Keep sentence meaning intact first, then split long sentences at natural
# clause boundaries. This is a soft readability ceiling, not a hard "always
# split at 15 words" rule.
MAX_WORDS_PER_CUE = 22
COMMA_SPLIT_WORDS = 18
MIN_SPLIT_SIDE_WORDS = 5
MIN_CUE_MS = 350
TOKEN_RE = re.compile(r"\S+")
SENTENCE_END_RE = re.compile(r'[.!?]["\')\]]*$')
SOFT_PUNCT_RE = re.compile(r"[,;:]$")
DANGLING_END_WORDS = {
    "and",
    "a",
    "an",
    "because",
    "but",
    "for",
    "if",
    "in",
    "into",
    "i",
    "like",
    "on",
    "or",
    "of",
    "that",
    "that's",
    "thats",
    "the",
    "to",
    "with",
}
PREFERRED_START_WORDS = {
    "because",
    "but",
    "if",
    "so",
    "that",
    "which",
    "with",
}
SAFE_CONNECTOR_START_WORDS = {
    "and",
    "but",
    "so",
}
UNSAFE_CUE_START_WORDS = {
    "in",
    "into",
    "of",
    "or",
    "to",
    "with",
}


@dataclass
class Word:
    start_ms: int
    end_ms: int
    text: str


@dataclass
class Cue:
    start_ms: int
    end_ms: int
    text: str


def fmt_ts(total_ms: int) -> str:
    total_ms = max(0, total_ms)
    hh = total_ms // 3_600_000
    total_ms %= 3_600_000
    mm = total_ms // 60_000
    total_ms %= 60_000
    ss = total_ms // 1000
    ms = total_ms % 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def normalize_spaces(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text


def normalize_word_text(text: str) -> str:
    return normalize_spaces(text.strip())


def parse_words(path: Path) -> list[Word]:
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    words: list[Word] = []
    for segment in data.get("segments", []):
        segment_words = segment.get("words") or []
        if segment_words:
            for item in segment_words:
                text = normalize_word_text(str(item.get("word", "")))
                if not text:
                    continue
                start = item.get("start")
                end = item.get("end")
                if start is None or end is None:
                    continue
                words.append(Word(round(float(start) * 1000), round(float(end) * 1000), text))
            continue

        # Fallback for Whisper JSON without word timestamps.
        text = normalize_spaces(str(segment.get("text", "")))
        if not text:
            continue
        tokens = TOKEN_RE.findall(text)
        start_ms = round(float(segment.get("start", 0)) * 1000)
        end_ms = round(float(segment.get("end", 0)) * 1000)
        duration = max(1, end_ms - start_ms)
        for idx, token in enumerate(tokens):
            token_start = start_ms + round(duration * idx / len(tokens))
            token_end = start_ms + round(duration * (idx + 1) / len(tokens))
            words.append(Word(token_start, token_end, token))
    return words


def word_body(text: str) -> str:
    return text.lower().strip("\"'“”‘’()[]{}.,;:!?")


def cue_text(words: list[Word]) -> str:
    return normalize_spaces(" ".join(word.text for word in words))


def should_break_sentence(words: list[Word], next_word: Word | None) -> bool:
    if not words:
        return False
    text = words[-1].text
    if SENTENCE_END_RE.search(text):
        return True
    if (
        next_word
        and next_word.start_ms - words[-1].end_ms >= 700
        and len(words) >= 4
        and word_body(text) not in DANGLING_END_WORDS
        and word_body(next_word.text) not in DANGLING_END_WORDS
    ):
        return True
    return False


def collect_sentences(words: list[Word]) -> list[list[Word]]:
    sentences: list[list[Word]] = []
    current: list[Word] = []
    for idx, word in enumerate(words):
        current.append(word)
        next_word = words[idx + 1] if idx + 1 < len(words) else None
        if should_break_sentence(current, next_word):
            sentences.append(current)
            current = []
    if current:
        if sentences and not SENTENCE_END_RE.search(cue_text(current)):
            sentences[-1].extend(current)
        else:
            sentences.append(current)
    return sentences


def choose_split(words: list[Word], start: int, hard_end: int) -> int:
    end = min(len(words), hard_end)
    if end >= len(words):
        return len(words)

    for idx in range(end - 1, start, -1):
        if SOFT_PUNCT_RE.search(words[idx].text) or SENTENCE_END_RE.search(words[idx].text):
            return idx + 1

    for idx in range(end - 1, start + 2, -1):
        body = word_body(words[idx].text)
        prev_body = word_body(words[idx - 1].text)
        if body in PREFERRED_START_WORDS and prev_body not in DANGLING_END_WORDS and len(words) - idx >= 2:
            return idx

    while (
        end < len(words)
        and end - start > 1
        and word_body(words[end - 1].text) in DANGLING_END_WORDS
    ):
        end -= 1

    return max(start + 1, end)


def is_safe_split_boundary(words: list[Word], idx: int) -> bool:
    if idx <= 0 or idx >= len(words):
        return False
    prev = word_body(words[idx - 1].text)
    current = word_body(words[idx].text)
    next_word = word_body(words[idx + 1].text) if idx + 1 < len(words) else ""

    # Filler asides like ", you know," read poorly as subtitle boundaries.
    if current == "you" and next_word == "know":
        return False
    if prev in DANGLING_END_WORDS:
        return False
    if current in DANGLING_END_WORDS and current not in SAFE_CONNECTOR_START_WORDS:
        return False
    return True


def choose_clause_split(sentence: list[Word]) -> int | None:
    if len(sentence) < COMMA_SPLIT_WORDS:
        return None

    candidates: list[int] = []
    for idx, word in enumerate(sentence[:-1]):
        if not SOFT_PUNCT_RE.search(word.text):
            continue
        split = idx + 1
        left_len = split
        right_len = len(sentence) - split
        if left_len < MIN_SPLIT_SIDE_WORDS or right_len < MIN_SPLIT_SIDE_WORDS:
            continue
        if not is_safe_split_boundary(sentence, split):
            continue
        candidates.append(split)

    if not candidates:
        return None

    target = len(sentence) / 2
    return min(candidates, key=lambda split: abs(split - target))


def split_sentence(sentence: list[Word]) -> list[list[Word]]:
    clause_split = choose_clause_split(sentence)
    if clause_split is not None:
        left = split_sentence(sentence[:clause_split])
        right = split_sentence(sentence[clause_split:])
        return left + right

    if len(sentence) <= MAX_WORDS_PER_CUE:
        return [sentence]

    chunks: list[list[Word]] = []
    start = 0
    while start < len(sentence):
        end = choose_split(sentence, start, start + MAX_WORDS_PER_CUE)
        chunks.append(sentence[start:end])
        start = end

    if len(chunks) >= 2 and len(chunks[-1]) <= 4:
        combined_len = len(chunks[-2]) + len(chunks[-1])
        if combined_len <= MAX_WORDS_PER_CUE + 4:
            chunks[-2].extend(chunks.pop())
        elif len(chunks[-2]) > 1:
            chunks[-1].insert(0, chunks[-2].pop())

    fixed_chunks: list[list[Word]] = []
    for chunk in chunks:
        if (
            fixed_chunks
            and chunk
            and word_body(chunk[0].text) in UNSAFE_CUE_START_WORDS
            and len(fixed_chunks[-1]) + len(chunk) <= MAX_WORDS_PER_CUE + 4
        ):
            fixed_chunks[-1].extend(chunk)
        else:
            fixed_chunks.append(chunk)
    chunks = fixed_chunks
    return chunks


def chunks_to_cues(chunks: list[list[Word]]) -> list[Cue]:
    cues: list[Cue] = []
    previous_end = 0
    for chunk in chunks:
        if not chunk:
            continue
        start_ms = chunk[0].start_ms
        end_ms = max(chunk[-1].end_ms, start_ms + MIN_CUE_MS)
        if cues and start_ms < previous_end:
            start_ms = previous_end
            end_ms = max(end_ms, start_ms + MIN_CUE_MS)
        cues.append(Cue(start_ms, end_ms, cue_text(chunk)))
        previous_end = end_ms
    return cues


def write_srt(path: Path, cues: list[Cue]) -> None:
    blocks = []
    for idx, cue in enumerate(cues, start=1):
        blocks.append(f"{idx}\n{fmt_ts(cue.start_ms)} --> {fmt_ts(cue.end_ms)}\n{cue.text}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: resegment_en_json_words.py <whisper.json> <output.srt>", file=sys.stderr)
        return 2

    words = parse_words(Path(sys.argv[1]))
    sentences = collect_sentences(words)
    chunks = [chunk for sentence in sentences for chunk in split_sentence(sentence)]
    cues = chunks_to_cues(chunks)
    write_srt(Path(sys.argv[2]), cues)
    print(f"word-timestamp resegmented {len(words)} words -> {len(cues)} cues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
