#!/usr/bin/env bash
# Agent Memory Kit — one-command quickstart
# Usage: curl -sL https://raw.githubusercontent.com/aommi/agent-memory-kit/main/scripts/quickstart.sh | bash -s [project-name]
set -euo pipefail

PROJECT="${1:-}"
if [ -z "$PROJECT" ]; then
  echo "Usage: bash quickstart.sh <project-directory>"
  echo "  The directory must exist (e.g. mkdir my-project && cd my-project first)."
  exit 1
fi

if [ ! -d "$PROJECT" ]; then
  echo "Error: '$PROJECT' does not exist. Create it first: mkdir $PROJECT && cd $PROJECT"
  exit 1
fi

KIT_DIR="$PROJECT/.agent/memory-kit"

echo "→ Cloning agent-memory-kit..."
if [ -d "$KIT_DIR" ]; then
  echo "  .agent/memory-kit already exists — skipping clone."
else
  git clone --depth 1 https://github.com/aommi/agent-memory-kit.git "$KIT_DIR" 2>&1 | tail -1
fi

echo "→ Initializing project config..."
cd "$PROJECT"
python3 "$KIT_DIR/generate.py" init << 'EOF'
$PROJECT
Memory kit for $PROJECT

y
n
n
n
n
n
n
EOF

echo "→ Generating agent configs..."
python3 "$KIT_DIR/generate.py" all

echo ""
echo "Done. Memory files created in $PROJECT/memory/"
echo "Agent configs generated:"
ls -1 "$PROJECT"/{CLAUDE.md,AGENTS.md} 2>/dev/null || true
