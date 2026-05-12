import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  loader: glob({ base: './src/content/posts', pattern: '**/*.md' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    kind: z.enum(['essay', 'notes', 'home']),
    description: z.string().optional(),
    publish: z.boolean().default(false),
    slug: z.string().optional(),
    incoming_links: z.array(z.object({
      slug: z.string(),
      title: z.string(),
    })).optional(),
  }),
});

export const collections = { posts };
