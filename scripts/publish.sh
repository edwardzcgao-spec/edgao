#!/bin/bash
set -e

VAULT="/Users/apple/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
ASTRO_DIR="$HOME/projects/edward-gao-homepage"
ASTRO_POSTS="$ASTRO_DIR/src/content/posts"

# macOS 通知 helper
notify() {
  local title="$1"
  local message="$2"
  osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null || true
}

# 失败时通知
on_error() {
  notify "Publish failed ✗" "Check terminal for details"
  exit 1
}
trap on_error ERR

echo "→ Scanning vault for publish: true notes..."
python3 "$ASTRO_DIR/scripts/sync-from-vault.py" "$VAULT" "$ASTRO_POSTS"

cd "$ASTRO_DIR"

if git diff --quiet && git diff --cached --quiet; then
  echo "✓ Nothing to publish."
  notify "Publish" "Nothing changed since last sync"
  exit 0
fi

echo "→ Committing..."
git add .
git commit -m "publish: $(date '+%Y-%m-%d %H:%M')"

echo "→ Pushing..."
git push

echo "✓ Published. Vercel redeploy in 1-2 min."
notify "Published ✓" "Vercel will redeploy in 1-2 min"
