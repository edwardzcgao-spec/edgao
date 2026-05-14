// src/utils/slug.ts
// Slug helpers for tag / series URLs.
// 中文字符保留(让 /series/连续性溢价 这种 URL 工作)。

const CJK_RANGE = '一-鿿';

/**
 * Slugify a series name into a URL-safe ID.
 * Examples:
 *   "Civilizational State" → "civilizational-state"
 *   "Seeing Like a State II" → "seeing-like-a-state-ii"
 *   "连续性溢价" → "连续性溢价"
 *   "Foo & Bar?" → "foo-bar"
 */
export function slugifySeries(name: string): string {
  if (!name) return '';
  return name
    .toLowerCase()
    .replace(/[\s_]+/g, '-')
    .replace(new RegExp(`[^a-z0-9${CJK_RANGE}\\-]+`, 'g'), '')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '');
}
