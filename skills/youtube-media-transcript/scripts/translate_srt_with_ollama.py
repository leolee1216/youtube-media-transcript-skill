#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3}) --> (?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


@dataclass
class Cue:
    index: int
    timing: str
    text: str


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    blocks = [block for block in re.split(r"\n\s*\n", raw) if block.strip()]
    cues: list[Cue] = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines()]
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        timing = lines[1].strip()
        if not TIME_RE.fullmatch(timing):
            continue
        text = " ".join(line.strip() for line in lines[2:] if line.strip()).strip()
        if text:
            cues.append(Cue(index=index, timing=timing, text=text))
    return cues


def write_srt(path: Path, cues: list[Cue]) -> None:
    chunks = []
    for cue in cues:
        chunks.append(f"{cue.index}\n{cue.timing}\n{cue.text}\n")
    path.write_text("\n".join(chunks), encoding="utf-8")


def build_prompt(batch: list[Cue]) -> str:
    instructions = [
        "You are translating English subtitles into natural Simplified Chinese subtitles.",
        "Rules:",
        "1. Translate only the subtitle text, not timestamps.",
        "2. Output exactly one line per input line in the format: <id>TAB<translation>.",
        "3. Keep the same ids and order.",
        "4. Use natural subtitle Chinese, concise and accurate.",
        "5. Translate agent as 智能体, prompt as 提示词, training data as 训练数据.",
        "6. Keep these names in English when they appear: OpenAI, ChatGPT, Codex, Claude Code, Anthropic, GitHub, Cursor, Vercel, Replit, Slack, Linear, Google Drive, MCP, API, SDK, CLI, PM.",
        "7. Do not add comments, code fences, or explanations.",
        "8. Do not merge or split lines.",
        "",
        "Input lines:",
    ]
    for cue in batch:
        instructions.append(f"{cue.index}\t{cue.text}")
    return "\n".join(instructions)


def build_single_prompt(cue: Cue) -> str:
    return "\n".join(
        [
            "Translate the following English subtitle into natural Simplified Chinese.",
            "Return only the Chinese translation with no numbering, no explanations, and no quotes.",
            "Use 智能体 for agent, 提示词 for prompt, 训练数据 for training data.",
            "Keep these names in English when they appear: OpenAI, ChatGPT, Codex, Claude Code, Anthropic, GitHub, Cursor, Vercel, Replit, Slack, Linear, Google Drive, MCP, API, SDK, CLI, PM.",
            "",
            cue.text,
        ]
    )


def ollama_generate_http(model: str, prompt: str, host: str, timeout: int) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 4096,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["response"]


def ollama_generate_cli(model: str, prompt: str, host: str, timeout: int) -> str:
    env = os.environ.copy()
    env["OLLAMA_HOST"] = host
    proc = subprocess.run(
        ["ollama", "run", model, prompt],
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip()
        if "operation not permitted" in detail.lower():
            detail += (
                "\nCodex sandbox blocked local Ollama access. Run this script as the"
                " top-level approved command and persist the prefix:"
                " python3 tools/translate_srt_with_ollama.py"
            )
        raise RuntimeError(f"ollama CLI failed with exit {proc.returncode}: {detail}")
    return proc.stdout.strip()


def ollama_generate(
    model: str,
    prompt: str,
    host: str,
    timeout: int,
    backend: str,
) -> str:
    if backend == "http":
        return ollama_generate_http(model=model, prompt=prompt, host=host, timeout=timeout)
    if backend == "cli":
        return ollama_generate_cli(model=model, prompt=prompt, host=host, timeout=timeout)
    try:
        return ollama_generate_cli(model=model, prompt=prompt, host=host, timeout=timeout)
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired):
        return ollama_generate_http(model=model, prompt=prompt, host=host, timeout=timeout)


def parse_translations(raw: str, expected_ids: list[int]) -> dict[int, str]:
    result: dict[int, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        idx_str, text = line.split("\t", 1)
        idx_str = idx_str.strip()
        text = text.strip()
        if not idx_str.isdigit() or not text:
            continue
        idx = int(idx_str)
        result[idx] = text
    missing = [idx for idx in expected_ids if idx not in result]
    if missing:
        raise ValueError(f"missing ids: {missing[:10]}")
    return result


def translate_batch(
    batch: list[Cue],
    model: str,
    host: str,
    timeout: int,
    retries: int,
    backend: str,
) -> list[Cue]:
    prompt = build_prompt(batch)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            raw = ollama_generate(
                model=model,
                prompt=prompt,
                host=host,
                timeout=timeout,
                backend=backend,
            )
            translated = parse_translations(raw, [cue.index for cue in batch])
            return [
                Cue(index=cue.index, timing=cue.timing, text=translated[cue.index])
                for cue in batch
            ]
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            RuntimeError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ) as exc:
            last_error = exc
            time.sleep(min(2 * attempt, 6))
    raise RuntimeError(f"batch {batch[0].index}-{batch[-1].index} failed: {last_error}")


def translate_batch_resilient(
    batch: list[Cue],
    model: str,
    host: str,
    timeout: int,
    retries: int,
    backend: str,
) -> list[Cue]:
    try:
        return translate_batch(
            batch=batch,
            model=model,
            host=host,
            timeout=timeout,
            retries=retries,
            backend=backend,
        )
    except RuntimeError:
        if len(batch) == 1:
            raw = ollama_generate(
                model=model,
                prompt=build_single_prompt(batch[0]),
                host=host,
                timeout=timeout,
                backend=backend,
            ).strip()
            raw = raw.strip().strip('"').strip()
            if not raw:
                raise
            return [Cue(index=batch[0].index, timing=batch[0].timing, text=raw)]
        mid = len(batch) // 2
        left = translate_batch_resilient(
            batch=batch[:mid],
            model=model,
            host=host,
            timeout=timeout,
            retries=retries,
            backend=backend,
        )
        right = translate_batch_resilient(
            batch=batch[mid:],
            model=model,
            host=host,
            timeout=timeout,
            retries=retries,
            backend=backend,
        )
        return left + right


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_srt", type=Path)
    parser.add_argument("output_srt", type=Path)
    parser.add_argument("--model", default="translategemma:4b")
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--backend",
        choices=["cli", "http", "auto"],
        default="cli",
        help=(
            "Use ollama CLI by default. In Codex Desktop, approve and persist the"
            " top-level command prefix once: python3 tools/translate_srt_with_ollama.py."
        ),
    )
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--start-index", type=int)
    parser.add_argument("--end-index", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    cues = parse_srt(args.input_srt)
    selected = [
        cue
        for cue in cues
        if (args.start_index is None or cue.index >= args.start_index)
        and (args.end_index is None or cue.index <= args.end_index)
    ]
    if not selected:
        print("no cues selected", file=sys.stderr)
        return 2

    out: list[Cue] = []
    done_ids: set[int] = set()
    if args.resume and args.output_srt.exists():
        existing = parse_srt(args.output_srt)
        out.extend(existing)
        done_ids = {cue.index for cue in existing}
        print(f"resuming with {len(done_ids)} cues already translated", file=sys.stderr, flush=True)

    for offset in range(0, len(selected), args.batch_size):
        batch = selected[offset : offset + args.batch_size]
        batch = [cue for cue in batch if cue.index not in done_ids]
        if not batch:
            continue
        translated_batch = translate_batch_resilient(
            batch=batch,
            model=args.model,
            host=args.host,
            timeout=args.timeout,
            retries=args.retries,
            backend=args.backend,
        )
        out.extend(translated_batch)
        out.sort(key=lambda cue: cue.index)
        write_srt(args.output_srt, out)
        print(
            f"translated {translated_batch[0].index}-{translated_batch[-1].index}",
            file=sys.stderr,
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
