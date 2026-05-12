#!/bin/bash
set -e

VAULT="/Users/apple/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian Vault"
ASTRO_DIR="$HOME/projects/edward-gao-homepage"
ASTRO_POSTS="$ASTRO_DIR/src/content/posts"

echo "→ Scanning vault for publish: true notes..."
python3 "$ASTRO_DIR/scripts/sync-from-vault.py" "$VAULT" "$ASTRO_POSTS"

cd "$ASTRO_DIR"

if git diff --quiet && git diff --cached --quiet; then
  echo "✓ Nothing to publish (no changes since last sync)."
  exit 0
fi

echo "→ Committing..."
git add .
git commit -m "publish: $(date '+%Y-%m-%d %H:%M')"

echo "→ Pushing..."
git push

echo "✓ Published. Vercel will redeploy in 1-2 min."
