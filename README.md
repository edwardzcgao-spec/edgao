# edward-gao-homepage

Personal site built with [Astro 6](https://astro.build).
Design ported from a Claude Design mockup.

## Local dev

Requires Node.js ≥ 20.3.0.

```bash
npm install
npm run dev          # http://localhost:4321
npm run build        # 输出到 dist/
npm run preview      # 本地预览 build 结果
```

## 添加新文章

在 `src/content/posts/` 下新建 `.md` 文件,文件名就是 URL slug。例:

```
src/content/posts/2026-05-on-archives.md
```

会生成 `/posts/2026-05-on-archives`。

每篇必须有 frontmatter:

```yaml
---
title: "On archives, and what they erase"
date: 2026-05-12
kind: essay          # 或 notes
description: "Optional. Used for meta tags."
draft: false         # 可选,默认 false。true 时不出现在列表里
---
```

## 项目结构

```
src/
├── content.config.ts        ← 文章 schema 定义(zod)
├── content/posts/*.md       ← 文章本体
├── pages/
│   ├── index.astro          ← 主页(hero + 最近 3 篇)
│   ├── writing.astro        ← 全部文章列表
│   └── posts/[...slug].astro ← 单篇文章页(自动生成)
├── layouts/
│   ├── BaseLayout.astro     ← HTML 外壳 + 字体加载
│   └── PostLayout.astro     ← 单篇文章页布局
├── components/
│   ├── Hero.astro
│   ├── ArticleList.astro
│   └── ArticleRow.astro
└── styles/
    └── global.css           ← 所有样式,设计 tokens 在顶部
```

## 部署

push 到 GitHub → 在 Vercel import,无需任何配置(Astro 静态站,Vercel 自动识别)。
