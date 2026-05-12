#!/bin/bash
set -e

VAULT="/Users/apple/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
ASTRO_DIR="$HOME/projects/edward-gao-homepage"
ASTRO_POSTS="$ASTRO_DIR/src/content/posts"

notify() {
  local title="$1"
  local message="$2"
  osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null || true
}

on_error() {
  notify "Publish failed ✗" "Check terminal for details"
  exit 1
}
trap on_error ERR

echo "→ Scanning vault for publish: true notes..."
python3 "$ASTRO_DIR/scripts/sync-from-vault.py" "$VAULT" "$ASTRO_POSTS"

cd "$ASTRO_DIR"

# Stage everything FIRST so untracked files are detected
git add .

if git diff --cached --quiet; then
  echo "✓ Nothing to publish (no changes since last sync)."
  notify "Publish" "Nothing changed since last sync"
  exit 0
fi

echo "→ Committing..."
git commit -m "publish: $(date '+%Y-%m-%d %H:%M')"

echo "→ Pushing..."
git push

echo "✓ Published. Vercel redeploy in 1-2 min."
notify "Published ✓" "Vercel will redeploy in 1-2 min"
