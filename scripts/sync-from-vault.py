#!/usr/bin/env python3
"""Walk vault recursively, copy .md files with `publish: true` to Astro posts dir.

Removes files in posts dir that no longer correspond to publishable vault files
(so changing publish: true → false on a note removes it from the site)."""

import sys
import shutil
from pathlib import Path


def parse_frontmatter(text):
    """Minimal frontmatter parser. Returns dict or None."""
    if not text.startswith('---\n'):
        return None
    end = text.find('\n---', 4)
    if end < 0:
        return None
    block = text[4:end]
    result = {}
    for line in block.split('\n'):
        if ':' not in line:
            continue
        key, _, value = line.partition(':')
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        result[key] = value
    return result


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <vault_path> <astro_posts_path>", file=sys.stderr)
        sys.exit(1)

    vault = Path(sys.argv[1])
    posts = Path(sys.argv[2])

    if not vault.is_dir():
        print(f"Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    posts.mkdir(parents=True, exist_ok=True)

    # Find publishable files
    targets = {}  # destination filename → source path
    for md in vault.rglob('*.md'):
        try:
            text = md.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        fm = parse_frontmatter(text)
        if not fm or fm.get('publish') is not True:
            continue
        slug = fm.get('slug')
        filename = f"{slug}.md" if isinstance(slug, str) and slug else md.name
        if filename in targets:
            print(f"⚠ filename collision: '{filename}' appears in multiple notes; "
                  f"keeping first ({targets[filename]}), skipping {md}", file=sys.stderr)
            continue
        targets[filename] = md

    print(f"Found {len(targets)} publishable note(s).")

    # Remove stale files in posts/
    existing = {p.name for p in posts.glob('*.md')}
    stale = existing - set(targets.keys())
    for name in stale:
        (posts / name).unlink()
        print(f"  − removed {name}")

    # Copy publishable files (only if newer)
    for filename, src in targets.items():
        dest = posts / filename
        if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(src, dest)
            print(f"  + {filename}")

    print("Sync complete.")


if __name__ == '__main__':
    main()
