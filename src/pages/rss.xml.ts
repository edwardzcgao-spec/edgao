import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const posts = await getCollection(
    'posts',
    ({ data }) => data.publish && (data.kind === 'essay' || data.kind === 'notes')
  );
  return rss({
    title: 'Edward Gao',
    description: 'Writing on history, institutions, and how complicated things work.',
    site: context.site!,
    items: posts
      .sort((a, b) => b.data.date.getTime() - a.data.date.getTime())
      .map((p) => ({
        title: p.data.title,
        pubDate: p.data.date,
        description: p.data.description ?? '',
        link: `/posts/${p.id}/`,
      })),
    customData: `<language>en</language>`,
  });
}
