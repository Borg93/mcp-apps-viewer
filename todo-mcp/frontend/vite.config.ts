import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  plugins: [
    svelte(),
    // Inlines all JS and CSS into index.html — required because the server
    // serves a single self-contained HTML string. No external src= refs allowed.
    viteSingleFile(),
  ],
  build: {
    // Disable chunk splitting — singlefile needs everything in one file
    assetsInlineLimit: Infinity,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
