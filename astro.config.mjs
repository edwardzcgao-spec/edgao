// @ts-check
import { defineConfig } from 'astro/config';

// https://docs.astro.build/en/reference/configuration-reference/
export default defineConfig({
  site: 'https://edgao.dev', // TODO: 改成你最终的域名;Vercel 给的 *.vercel.app 也可以
  output: 'static',
});
