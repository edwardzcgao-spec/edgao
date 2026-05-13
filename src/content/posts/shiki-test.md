---
title: Shiki 测试
kind: notes
date: 2026-05-13
publish: true
slug: shiki-test
reading_time: 2
last_modified: 2026-05-13
---

# Shiki 高亮测试

正文里 inline `code` 应该是浅灰底,跟下面的代码块视觉区分。

## Python

```python
def fibonacci(n: int) -> list[int]:
    """Generate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    sequence = [0, 1]
    for i in range(2, n):
        sequence.append(sequence[i - 1] + sequence[i - 2])
    return sequence[:n]

# 验证 string / number / keyword / comment / decorator 颜色
result = fibonacci(10)
print(f"前 10 项: {result}")
```

## TypeScript

```typescript
interface User {
  id: string;
  name: string;
  email: string | null;
  createdAt: Date;
}

async function fetchUser(id: string): Promise<User | null> {
  const res = await fetch(`/api/users/${id}`);
  if (!res.ok) return null;
  return res.json() as Promise<User>;
}
```

## Bash(测 wrap: false 横滚)

```bash
# 下面这行故意写长,应该出现横向滚动条而不是软换行
git log --pretty=format:'%h %ad | %s%d [%an]' --graph --date=short --all --since="2 weeks ago" | head -20
```

## CSS

```css
.prose__body pre.astro-code {
  background: var(--code-bg);
  padding: 1.2em 1.4em;
  border-radius: 6px;
  overflow-x: auto;
}

@media (prefers-color-scheme: dark) {
  .prose__body pre.astro-code,
  .prose__body pre.astro-code span {
    color: var(--shiki-dark) !important;
    background-color: var(--shiki-dark-bg) !important;
  }
}
```

## 验证 checklist

- [ ] 4 个代码块都有彩色 token(不是单色灰底)
- [ ] inline `code` 跟代码块视觉区分明显
- [ ] Bash 那个长行**横向滚动**,没软换行成两行
- [ ] 切右上角主题按钮 → 代码块背景 + token 颜色都跟着切换
- [ ] 改 macOS 系统外观 → 代码块也跟着切换(在自动模式下)