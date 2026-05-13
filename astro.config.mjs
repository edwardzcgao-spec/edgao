// @ts-check
import { defineConfig } from 'astro/config';

// https://docs.astro.build/en/reference/configuration-reference/
export default defineConfig({
  site: 'https://edwardgao.vercel.app', // TODO: 改成你最终的域名;Vercel 给的 *.vercel.app 也可以
  output: 'static',
  markdown: {
    // Shiki dual-theme:输出 inline style 为 light 主题,带 --shiki-dark CSS 变量;
    // global.css 里的 dark mode 规则把 dark 变量翻成实际颜色。
    shikiConfig: {
      themes: {
        light: 'vitesse-light',
        dark: 'vitesse-dark',
      },
      wrap: false,
    },
  },
});
