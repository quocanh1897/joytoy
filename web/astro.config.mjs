import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://joytoy.binscode.site",
  output: "static",
  build: {
    format: "directory",
  },
  compressHTML: true,
  vite: {
    build: {
      cssMinify: "lightningcss",
    },
  },
});
