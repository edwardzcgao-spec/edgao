#!/usr/bin/env python3
"""Walk vault, copy publish:true .md files to Astro posts dir.

Phase 2 features:
- Transform [[Name]] and [[Name|Display]] wikilinks to standard markdown links.
- Build backlinks index and inject as frontmatter `incoming_links` field.
- Wikilinks targeting unpublished notes degrade to plain text (no broken links).
- Wikilinks targeting kind:home notes also degrade (home has no /posts/<slug> URL).
"""

import sys
import re
from pathlib import Path


WIKILINK_PATTERN = re.compile(r'\[\[([^\[\]|]+?)(?:\|([^\[\]]+?))?\]\]')


def parse_frontmatter(text):
    """Return (fm_dict, body) or (None, text) if no frontmatter."""
    if not text.startswith('---\n'):
        return None, text
    end = text.find('\n---', 4)
    if end < 0:
        return None, text
    block = text[4:end]
    rest = text[end + 4:].lstrip('\n')

    result = {}
    for line in block.split('\n'):
        if ':' not in line:
            continue
        # Skip list-style lines (starts with whitespace + '-')
        if line.lstrip().startswith('-'):
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
    return result, rest


def serialize_frontmatter(fm, incoming_links):
    """Write frontmatter dict back to YAML, append incoming_links list if any."""
    lines = ['---']
    for key, value in fm.items():
        if key == 'incoming_links':
            continue  # written separately
        if isinstance(value, bool):
            lines.append(f'{key}: {"true" if value else "false"}')
        elif isinstance(value, str):
            if ':' in value or '#' in value or value.startswith('['):
                escaped = value.replace('"', '\\"')
                lines.append(f'{key}: "{escaped}"')
            else:
                lines.append(f'{key}: {value}')
        else:
            lines.append(f'{key}: {value}')

    if incoming_links:
        lines.append('incoming_links:')
        for link in incoming_links:
            slug_str = str(link['slug']).replace('"', '\\"')
            title_str = str(link['title']).replace('"', '\\"')
            lines.append(f'  - slug: "{slug_str}"')
            lines.append(f'    title: "{title_str}"')

    lines.append('---')
    return '\n'.join(lines)


def transform_wikilinks(body, source_slug, source_title,
                        filename_to_slug, backlinks, unresolved):
    """Replace [[X]] and [[X|Display]] in body. Side effect: populate backlinks/unresolved."""
    def repl(match):
        target_name = match.group(1).strip()
        display = match.group(2).strip() if match.group(2) else target_name
        target_lower = target_name.lower()
        if target_lower in filename_to_slug:
            target_slug = filename_to_slug[target_lower]
            if target_slug != source_slug:
                backlinks.setdefault(target_slug, []).append({
                    'slug': source_slug,
                    'title': source_title,
                })
            return f'[{display}](/posts/{target_slug})'
        else:
            unresolved.append((source_slug, target_name))
            return display

    return WIKILINK_PATTERN.sub(repl, body)


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

    # Pass 1: collect all publishable notes; build filename → slug map
    # (excludes kind:home from being a wikilink target — no /posts/<slug> URL)
    publishable = []  # list of dicts
    filename_to_slug = {}

    for md in vault.rglob('*.md'):
        try:
            text = md.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        fm, body = parse_frontmatter(text)
        if not fm or fm.get('publish') is not True:
            continue

        basename = md.stem
        slug = fm.get('slug') or basename
        if not isinstance(slug, str) or not slug:
            slug = basename

        publishable.append({
            'md': md, 'fm': fm, 'body': body,
            'basename': basename, 'slug': slug,
        })

        # Only non-home notes are wikilink TARGETS
        if fm.get('kind') != 'home':
            basename_lower = basename.lower()
            if basename_lower in filename_to_slug:
                print(f"⚠ duplicate filename: '{basename}.md' appears multiple times; "
                      f"keeping first", file=sys.stderr)
                continue
            filename_to_slug[basename_lower] = slug

    print(f"Found {len(publishable)} publishable note(s).")

    # Pass 2: transform wikilinks in bodies; collect backlinks
    backlinks = {}
    unresolved = []
    transformed = []

    for item in publishable:
        title = item['fm'].get('title', item['basename'])
        new_body = transform_wikilinks(
            item['body'], item['slug'], str(title),
            filename_to_slug, backlinks, unresolved,
        )
        # Obsidian ==highlight== → <mark>highlight</mark>
        new_body = re.sub(r'==(.+?)==', r'<mark>\1</mark>', new_body)
        transformed.append({**item, 'new_body': new_body, 'title': str(title)})

    if unresolved:
        print(f"\n⚠ {len(unresolved)} wikilink(s) target unpublished/missing notes "
              f"(rendered as plain text):", file=sys.stderr)
        for source, target in unresolved[:20]:
            print(f"  in '{source}': [[{target}]]", file=sys.stderr)
        if len(unresolved) > 20:
            print(f"  ... and {len(unresolved) - 20} more", file=sys.stderr)
        print()

    # Pass 3: write output files (only if content changed)
    target_filenames = set()
    for item in transformed:
        filename = f"{item['slug']}.md"
        target_filenames.add(filename)

        incoming = backlinks.get(item['slug'], [])
        # Dedupe by source slug
        seen = set()
        deduped = []
        for link in incoming:
            if link['slug'] not in seen:
                seen.add(link['slug'])
                deduped.append(link)

        new_text = serialize_frontmatter(item['fm'], deduped) + '\n\n' + item['new_body']
        dest = posts / filename

        if dest.exists() and dest.read_text(encoding='utf-8') == new_text:
            continue
        dest.write_text(new_text, encoding='utf-8')
        print(f"  + {filename}")

    # Pass 4: remove stale files
    existing_files = {p.name for p in posts.glob('*.md')}
    stale = existing_files - target_filenames
    for name in stale:
        (posts / name).unlink()
        print(f"  − removed {name}")

    print("Sync complete.")


if __name__ == '__main__':
    main()
