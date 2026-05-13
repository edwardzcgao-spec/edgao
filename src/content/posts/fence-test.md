---
title: Fence Test
kind: notes
date: 2026-05-13
publish: true
slug: fence-test
reading_time: 1
last_modified: 2026-05-13
---

# Fence 测试

正文里 这个 wikilink 应该被处理(指向不存在的笔记,降级为纯文字)。
正文 <mark>这个高光</mark> 应该变 mark。

## 代码块测试

```python
# 下面这些都不应该被 sync 处理
link = "[[SSII]]"
highlight = "==important=="
image = "![[test.png]]"
```

## Inline code 测试

inline 里的 `[[wikilink]]` 和 `==mark==` 和 `![[img.png]]` 都不应该被替换。

正文里的 Home 应该被处理(Home 存在)。