#!/bin/bash
set -e

# Shortcut / launchd 启动的 minimal shell 默认 PATH 极简,显式设置
# (homebrew 在 Apple Silicon 是 /opt/homebrew/bin,Intel 是 /usr/local/bin,两个都写上)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Git credential helper:Shortcut 后台 shell 拿不到 Keychain user session,
# 用 store 从 ~/.git-credentials 读 PAT
# (用户需先在 Terminal 用 PAT 触发一次 push 写入 cache,见 publish.sh 同目录的说明 / README)
git config --global credential.helper store

# 凭证缺失时立刻报错,而不是 hang 等输入(Shortcut 永远不会输入)
export GIT_TERMINAL_PROMPT=0

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

echo "→ [1/4] Scanning vault for publish: true notes..."
python3 "$ASTRO_DIR/scripts/sync-from-vault.py" "$VAULT" "$ASTRO_POSTS"

cd "$ASTRO_DIR"

echo "→ [2/4] Staging..."
# Stage everything FIRST so untracked files are detected
git add .

if git diff --cached --quiet; then
  echo "✓ Nothing to publish (no changes since last sync)."
  notify "Publish" "Nothing changed since last sync"
  exit 0
fi

echo "→ [3/4] Committing..."
git commit -m "publish: $(date '+%Y-%m-%d %H:%M')"

echo "→ [4/4] Pushing..."
git push

echo "✓ Published. Vercel redeploy in 1-2 min."
notify "Published ✓" "Vercel will redeploy in 1-2 min"
