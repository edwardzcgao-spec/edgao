import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// posts 集合:src/content/posts/*.md
// 每篇文章的 frontmatter 必须有 title, date, kind
const posts = defineCollection({
  loader: glob({ base: './src/content/posts', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(),
    // 日期字符串(YYYY-MM-DD)会被自动转成 Date 对象
    date: z.coerce.date(),
    // 文章类型:essay 是长文,notes 是读书笔记/片段
    kind: z.enum(['essay', 'notes']),
    // 可选:摘要,用于未来的 RSS / OG meta
    description: z.string().optional(),
    // 可选:是否发布(false 时不出现在列表里,但 dev 模式仍可访问)
    draft: z.boolean().default(false),
  }),
});

export const collections = { posts };
