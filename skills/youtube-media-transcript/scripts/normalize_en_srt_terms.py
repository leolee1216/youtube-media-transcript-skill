#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


REGEX_REPLACEMENTS = [
    (r"\bcloud code\b", "Claude Code"),
    (r"\bclaude code\b", "Claude Code"),
    (r"\bcloud design\b", "Claude Design"),
    (r"\bclaw design\b", "Claude Design"),
    (r"\bclaude design\b", "Claude Design"),
    (r"\bclaw\.md\b", "CLAUDE.md"),
    (r"\bcloud\.md\b", "CLAUDE.md"),
    (r"\bG SAP\b", "GSAP"),
    (r"\bgsap\b", "GSAP"),
    (r"\bgithub\b", "GitHub"),
    (r"\bopeneyes\b", "OpenAI's"),
    (r"\bopen AI\b", "OpenAI"),
    (r"\bOpenA\b", "OpenAI"),
    (r"\bchat PT\b", "ChatGPT"),
    (r"\bGrinola\b", "Granola"),
    (r"\bshitter notes\b", "share their notes"),
    (r"\bfor sale\b(?= or cloudflare or render)", "Vercel"),
    (r"\btea muxing\b", "tmuxing"),
    (r"\bID extension\b", "IDE extension"),
    (r"\bget work trees\b", "git worktrees"),
    (r"\bDevax\b", "DevEx"),
    (r"\bedited entirely by AR\b", "edited entirely by AI"),
    (r"\bopen AI whisper\b", "OpenAI Whisper"),
    (r"\breactant typescript\b", "React and TypeScript"),
    (r"\bN and N\b", "n8n"),
    (r"\bnext JS\b", "Next.js"),
    (r"\banti gravity\b", "Antigravity"),
    (r"\bdribble\.com\b", "Dribbble.com"),
    (r"\bdribbles\b", "Dribbble is"),
    (r"\bdribble\b", "Dribbble"),
    (r"\bgetdesign\.nd\b", "getdesign.md"),
    (r"\bdesign\.nd\b", "design.md"),
    (r"\bversatile\b", "Vercel"),
    (r"\bversal\.app\b", "vercel.app"),
    (r"\bcloud\b(?= is already opening up a browser)", "Claude Code"),
    (r"\bremotion\b", "Remotion"),
    (r"\bremotions\b", "Remotion"),
    (r"\bplaywright mcp\b", "Playwright MCP"),
    (r"\bplayer at MCP\b", "Playwright MCP"),
    (r"\bplayer MCP\b", "Playwright MCP"),
    (r"\bmcp\b", "MCP"),
    (r"\bMCPs\b", "MCPs"),
    (r"\bnpm\b", "npm"),
    (r"\bnpx\b", "npx"),
    (r"\btailwind CSS\b", "Tailwind CSS"),
    (r"\bopus\b", "Opus"),
    (r"\bsonnet\b", "Sonnet"),
    (r"\bopen 4\.6\b", "Opus 4.6"),
    (r"\bproplexity computer\b", "Perplexity Comet"),
    (r"\bproblexy computer\b", "Perplexity Comet"),
    (r"\bnano-bin and pro\b", "Nano Banana Pro"),
    (r"\bnano-bin and a pro\b", "Nano Banana Pro"),
    (r"\bGPT image 2\.5\b", "GPT Image 2.5"),
    (r"\bremotion out lotty\b", "Remotion add Lottie"),
    (r"\blotty\b", "Lottie"),
    (r"\blottys\b", "Lotties"),
    (r"\bzard schema\b", "Zod schema"),
    (r"\bOpenClub\b", "OpenCode"),
    (r"\bPoid Out Dev\b", "Void.dev"),
    (r"\bDevinore\b", "Envato"),
    (r"\bDevonore\b", "Envato"),
    (r"\breplicate\b", "Replicate"),
    (r"\b11 apps\b", "11labs"),
    (r"\bSVGO stair\b", "SVG logo"),
    (r"\btreaty assets\b", "3D assets"),
    (r"\btreaty asset\b", "3D asset"),
    (r"\bthree assets\b", "3D assets"),
    (r"\bgifts\b", "GIFs"),
]


PHRASE_REPLACEMENTS = [
    ("know edit", "now edit"),
    ("structured, taught", "structured text"),
    ("try to video", "throughout the video"),
    ("simlink", "symlink"),
    ("cloud dash dash dangerously", "claude --dangerously"),
    ("cloud MCP ad playwright", "Claude MCP add Playwright"),
    ("air agents", "AI agents"),
    ("open a Claude Code", "open Claude Code"),
    ("Cloud Core", "Claude Code"),
    ("cloud code", "Claude Code"),
    ("So that are good.", "So that we're good."),
    ("access folder", "assets folder"),
    ("look for this YouTube channel", "look for this YouTube channel"),
    ("telling you to look for this YouTube channel", "telling it to look for this YouTube channel"),
    ("subscribe account", "subscriber count"),
    ("lower turn", "lower third"),
    ("an vato", "Envato"),
    ("lock into Claude Code", "log into Claude Code"),
    ("speak the Claude Code", "speak to Claude Code"),
    ("watch this fair", "watched this far"),
    ("go better", "go to bed"),
    ("npm create video at latest", "npm create video@latest"),
    ("NPM create video at latest", "npm create video@latest"),
    ("NPM I", "npm install"),
    ("npm I", "npm install"),
    ("Remotion dash dev slash skills", "remotion-dev/skills"),
    ("slash MCP", "/mcp"),
    ("slash model", "/model"),
    ("app.larifers.com", "app.lottiefiles.com"),
    ("a Remotion for that", "Remotion for that"),
    ("creative OpenClaw", "creator of OpenCode"),
    ("from OpenClaw", "from OpenCode"),
    ("opa call", "OpenCode"),
    ("the school cursor, Windsor and others", "tools like Cursor, Windsurf and others"),
]


def normalize_terms(text: str) -> str:
    fixed = text
    for pattern, replacement in REGEX_REPLACEMENTS:
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)
    for old, new in PHRASE_REPLACEMENTS:
        fixed = fixed.replace(old, new)
    return fixed


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: normalize_en_srt_terms.py <input.srt> <output.srt>", file=sys.stderr)
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    text = input_path.read_text(encoding="utf-8", errors="replace")
    output_path.write_text(normalize_terms(text), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
