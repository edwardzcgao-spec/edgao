---
title: KaTeX 测试
kind: notes
date: 2026-05-13
publish: true
slug: katex-test
---

# KaTeX 数学公式测试

## Inline

爱因斯坦 $E = mc^2$,勾股 $\sqrt{a^2 + b^2}$,希腊字母 $\alpha, \beta, \gamma, \Sigma, \pi$。

## Display

高斯积分:

$$
\int_0^\infty e^{-x^2} \, dx = \frac{\sqrt{\pi}}{2}
$$

薛定谔方程:

$$
i\hbar \frac{\partial}{\partial t} \Psi(x, t) = -\frac{\hbar^2}{2m} \nabla^2 \Psi + V(x) \Psi
$$

巴塞尔问题:

$$
\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}
$$

## 矩阵

$$
A = \begin{pmatrix}
a & b \\
c & d
\end{pmatrix}
\quad
B = \begin{bmatrix}
1 & 0 \\
0 & 1
\end{bmatrix}
$$

## 多行 align

$$
\begin{aligned}
(a+b)^2 &= a^2 + 2ab + b^2 \\
(a-b)^2 &= a^2 - 2ab + b^2
\end{aligned}
$$

## 美元符号转义

价格 \$10 应该正常显示,不进入 math。如果中间夹着的是普通文字比如 "我有 5 元",**不要**写成 `$5`,会触发 math 模式。

---

## 验证 checklist

- [ ] inline 公式跟正文同行,字号略大不突兀
- [ ] display 公式居中、独占一行
- [ ] 分数线、积分号、根号横线、矩阵括号颜色 = 正文 ink
- [ ] 切右上角主题 → 所有公式元素跟着 ink 切色
- [ ] 长公式(比如薛定谔)在窄屏横向滚动,不撑破 .prose 容器
- [ ] `\$10` 渲染成字面 `$10`,不进 math
- [ ] `aligned` 环境的 `&` 对齐线工作