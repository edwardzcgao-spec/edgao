#!/usr/bin/env python3
"""Walk vault, copy publish:true .md files to Astro posts dir.

Features (cumulative):
- Transform [[Name]] / [[Name|Display]] wikilinks → /posts/<slug>; collect backlinks.
- Transform ![[file.png]] image embeds → ![alt](/images/<rel>); mirror copy.
- Transform Obsidian ==text== → <mark>text</mark>.
- Wave 1 D: inject reading_time (min) and last_modified (ISO date) into output frontmatter.
- Wave 1 E: move stale images in public/images/ to public/_trash/<timestamp>/ (no rm).
- Wave 1 F: protect ```fenced``` blocks and `inline` code from all three transforms above.
"""

import sys
import re
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path


# Negative lookbehind so this doesn't match the inner `[[...]]` of an `![[image]]` embed.
WIKILINK_PATTERN = re.compile(r'(?<!!)\[\[([^\[\]|]+?)(?:\|([^\[\]]+?))?\]\]')
# Obsidian image embed: ![[name.png]] or ![[subfolder/name.png|alt text]]
IMAGE_EMBED_PATTERN = re.compile(r'!\[\[([^\[\]|]+?)(?:\|([^\[\]]+?))?\]\]')
IMAGE_EXT_PATTERN = re.compile(r'\.(png|jpe?g|gif|svg|webp)$', re.IGNORECASE)
# CJK Unified Ideographs + Extension A (covers 99% of modern Chinese)
CJK_RE = re.compile(r'[一-鿿㐀-䶿]')

# Phase F:fenced code block(```...```)和 inline code(`...`)的合并 pattern。
# 顺序很重要——先匹配 fenced(三反引号)再 inline,否则 inline 会先咬走单反引号。
CODE_SEGMENT_RE = re.compile(
    r'```[^\n]*\n[\s\S]*?\n```'   # 多行 fenced
    r'|`[^`\n]+`',                  # 单行 inline,无内部反引号、无换行
    re.MULTILINE,
)

# Phase E:在 src/content/posts/*.md 里识别 ![alt](/images/...) 引用
USED_IMAGE_RE = re.compile(r'!\[[^\]]*\]\((/images/[^)\s]+)\)')


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


# ---------------------------------------------------------------------------
# Phase F: code fence detection
# ---------------------------------------------------------------------------

def split_by_code(body):
    """返回 [(kind, text)] 列表,kind in {'code', 'prose'}。
    Code 包含 fenced ```...``` 和 inline `...`,transform 跳过这些段。"""
    parts = []
    last = 0
    for m in CODE_SEGMENT_RE.finditer(body):
        if m.start() > last:
            parts.append(('prose', body[last:m.start()]))
        parts.append(('code', m.group(0)))
        last = m.end()
    if last < len(body):
        parts.append(('prose', body[last:]))
    return parts


def apply_protecting_code(body, *transform_fns):
    """顺序跑一组 transform,只对 prose 段应用,code 段原样保留。"""
    out = []
    for kind, text in split_by_code(body):
        if kind == 'prose':
            for fn in transform_fns:
                text = fn(text)
        out.append(text)
    return ''.join(out)


# ---------------------------------------------------------------------------
# Phase D: reading time + last modified
# ---------------------------------------------------------------------------

def compute_reading_time(body):
    """English 200 wpm + Chinese 300 cpm,向上取整,最少 1 分钟。"""
    cjk_count = len(CJK_RE.findall(body))
    en_text = CJK_RE.sub(' ', body)
    en_words = len([w for w in en_text.split() if w])
    minutes = math.ceil(en_words / 200 + cjk_count / 300)
    return max(1, minutes)


def get_mtime_iso(path):
    """文件 mtime → ISO 8601 date (YYYY-MM-DD,UTC)。"""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


# ---------------------------------------------------------------------------
# Pass 0: image index
# ---------------------------------------------------------------------------

def build_image_index(vault):
    """Walk vault for image files. Returns:
      by_path:     {vault-relative posix path → absolute Path}
      by_basename: {lower(filename) → [vault-relative posix paths]} (for bare `![[IMG.png]]`)
    """
    by_path = {}
    by_basename = {}
    for f in vault.rglob('*'):
        if not f.is_file():
            continue
        if not IMAGE_EXT_PATTERN.search(f.name):
            continue
        rel = f.relative_to(vault).as_posix()
        by_path[rel] = f
        by_basename.setdefault(f.name.lower(), []).append(rel)
    return by_path, by_basename


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

def transform_image_embeds(body, source_slug,
                            by_path, by_basename, public_images_dir,
                            missing, ambiguous, copied):
    """Replace ![[file.png]] with ![alt](/images/<vault-rel-path>) and copy file."""
    def repl(match):
        ref = match.group(1).strip()
        alt = (match.group(2) or '').strip()

        if '/' in ref:
            rel = ref
            if rel not in by_path:
                missing.append((source_slug, ref))
                return match.group(0)
        else:
            matches = by_basename.get(ref.lower(), [])
            if not matches:
                missing.append((source_slug, ref))
                return match.group(0)
            if len(matches) > 1:
                ambiguous.append((source_slug, ref, matches))
            rel = matches[0]

        src = by_path[rel]
        dest = public_images_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or src.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(src, dest)
            copied.add(rel)

        if not alt:
            alt = Path(ref).stem
        web_path = '/images/' + rel.replace(' ', '%20')
        return f'![{alt}]({web_path})'

    return IMAGE_EMBED_PATTERN.sub(repl, body)


def transform_wikilinks(body, source_slug, source_title,
                        filename_to_slug, home_filenames, backlinks, unresolved):
    """Replace [[X]] and [[X|Display]] in body. Side effect: populate backlinks/unresolved.
    Home notes (kind: home) resolve to '/' (the rendered homepage)."""
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
        elif target_lower in home_filenames:
            # Home note 被渲染为主页 `/`,wikilink 解析为根路径
            # (不记录 backlink — 主页模板没有 backlinks 区块)
            return f'[{display}](/)'
        else:
            unresolved.append((source_slug, target_name))
            return display

    return WIKILINK_PATTERN.sub(repl, body)


# ---------------------------------------------------------------------------
# Phase E: stale image cleanup
# ---------------------------------------------------------------------------

def cleanup_stale_images(posts_dir, public_images_dir, astro_root):
    """扫 src/content/posts/*.md 收集所有引用的 /images/... 路径,
    跟 public/images/ 实际文件 diff,把多余的移到 public/_trash/<timestamp>/。
    不 rm,人工 review 后再清理。"""
    if not public_images_dir.exists():
        return

    used = set()
    for md in posts_dir.glob('*.md'):
        try:
            text = md.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        for m in USED_IMAGE_RE.finditer(text):
            rel = m.group(1)[len('/images/'):]
            rel = rel.replace('%20', ' ')
            used.add(rel)

    stale = []
    for f in public_images_dir.rglob('*'):
        if f.is_file():
            rel = f.relative_to(public_images_dir).as_posix()
            if rel not in used:
                stale.append((rel, f))

    if not stale:
        print("✓ No stale images.")
        return

    trash_dir = astro_root / 'public' / '_trash' / datetime.now().strftime('%Y%m%d-%H%M%S')
    for rel, src in stale:
        dest = trash_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
    print(f"Moved {len(stale)} stale image(s) to {trash_dir.relative_to(astro_root)}/")


# ---------------------------------------------------------------------------
# Phase F: self-test (跑在 main() 之前,失败 abort)
# ---------------------------------------------------------------------------

def _self_test():
    sample = (
        "Prose with [[Note-A]] and ==hi==.\n\n"
        "```python\n"
        "x = '[[Note-B]]'\n"
        "y = '==literal=='\n"
        "z = '![[image.png]]'\n"
        "```\n\n"
        "Inline: `[[Note-C]]` should stay literal.\n"
    )
    out = split_by_code(sample)
    kinds = [k for k, _ in out]
    assert kinds == ['prose', 'code', 'prose', 'code', 'prose'], \
        f"split kind sequence mismatch: {kinds}"
    assert '[[Note-B]]' in out[1][1]
    assert '==literal==' in out[1][1]
    assert '![[image.png]]' in out[1][1]
    assert '[[Note-C]]' in out[3][1]

    # Reading time:200 EN words → 1 min
    assert compute_reading_time('word ' * 200) == 1
    # 300 CJK chars → 1 min
    assert compute_reading_time('字' * 300) == 1
    # 600 CJK chars → 2 min
    assert compute_reading_time('字' * 600) == 2


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

    astro_root = posts.parent.parent.parent
    public_images_dir = astro_root / 'public' / 'images'
    public_images_dir.mkdir(parents=True, exist_ok=True)

    # Pass 0: index all images in vault (for ![[image]] resolution)
    by_path, by_basename = build_image_index(vault)
    print(f"Indexed {len(by_path)} image file(s) in vault.")

    # Pass 1: collect all publishable notes; build filename → slug map
    # 普通笔记进 filename_to_slug → /posts/<slug>;home 笔记进 home_filenames → /
    publishable = []
    filename_to_slug = {}
    home_filenames = set()

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

        basename_lower = basename.lower()
        if fm.get('kind') == 'home':
            home_filenames.add(basename_lower)
        else:
            if basename_lower in filename_to_slug:
                print(f"⚠ duplicate filename: '{basename}.md' appears multiple times; "
                      f"keeping first", file=sys.stderr)
                continue
            filename_to_slug[basename_lower] = slug

    print(f"Found {len(publishable)} publishable note(s).")

    # Pass 2: transform body content — image embeds, wikilinks, highlights
    # (Phase F: 包一层 apply_protecting_code,fenced 和 inline code 不参与替换)
    backlinks = {}
    unresolved = []
    missing_images = []
    ambiguous_images = []
    copied_images = set()
    transformed = []

    for item in publishable:
        title = item['fm'].get('title', item['basename'])
        slug = item['slug']

        def img_xform(text, _slug=slug):
            return transform_image_embeds(
                text, _slug, by_path, by_basename, public_images_dir,
                missing_images, ambiguous_images, copied_images,
            )

        def wl_xform(text, _slug=slug, _title=str(title)):
            return transform_wikilinks(
                text, _slug, _title,
                filename_to_slug, home_filenames, backlinks, unresolved,
            )

        def hl_xform(text):
            return re.sub(r'==(.+?)==', r'<mark>\1</mark>', text)

        new_body = apply_protecting_code(item['body'], img_xform, wl_xform, hl_xform)

        # Phase D: 算 reading_time + last_modified,注入 fm
        item['fm']['reading_time'] = compute_reading_time(item['body'])
        item['fm']['last_modified'] = get_mtime_iso(item['md'])

        transformed.append({**item, 'new_body': new_body, 'title': str(title)})

    if copied_images:
        print(f"Copied/updated {len(copied_images)} image(s) to public/images/.")

    if ambiguous_images:
        print(f"\n⚠ {len(ambiguous_images)} ambiguous image embed(s) (multiple files share basename, "
              f"picked first; use ![[subfolder/name.png]] to disambiguate):", file=sys.stderr)
        for source, ref, matches in ambiguous_images[:10]:
            print(f"  in '{source}': ![[{ref}]] → {matches[0]}  (also: {', '.join(matches[1:5])})",
                  file=sys.stderr)
        if len(ambiguous_images) > 10:
            print(f"  ... and {len(ambiguous_images) - 10} more", file=sys.stderr)
        print()

    if missing_images:
        print(f"\n⚠ {len(missing_images)} image embed(s) not found in vault "
              f"(left as raw ![[...]] in markdown):", file=sys.stderr)
        for source, ref in missing_images[:20]:
            print(f"  in '{source}': ![[{ref}]]", file=sys.stderr)
        if len(missing_images) > 20:
            print(f"  ... and {len(missing_images) - 20} more", file=sys.stderr)
        print()

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

    # Pass 4: remove stale .md files
    existing_files = {p.name for p in posts.glob('*.md')}
    stale = existing_files - target_filenames
    for name in stale:
        (posts / name).unlink()
        print(f"  − removed {name}")

    # Pass 5: cleanup stale images (Phase E)
    cleanup_stale_images(posts, public_images_dir, astro_root)

    print("Sync complete.")


if __name__ == '__main__':
    _self_test()
    main()
