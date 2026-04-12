#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.codex/skills/youtube-media-transcript"
TEMPLATE="$REPO_ROOT/skill-template/SKILL.template.md"
TARGET_FILE="$TARGET_DIR/SKILL.md"

mkdir -p "$TARGET_DIR"
sed "s|__REPO_ROOT__|$REPO_ROOT|g" "$TEMPLATE" > "$TARGET_FILE"

echo "Installed skill to: $TARGET_FILE"
