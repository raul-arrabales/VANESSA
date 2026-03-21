import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.indexOf("node_modules") === -1) {
            return;
          }

          const syntaxHighlighterPackages = [
            "react-syntax-highlighter",
            "refractor",
            "prismjs",
          ];

          if (syntaxHighlighterPackages.some((segment) => id.indexOf(segment) >= 0)) {
            return "syntax-highlighter-vendor";
          }

          const markdownPackages = [
            "react-markdown",
            "remark-",
            "rehype-",
            "unified",
            "micromark",
            "mdast-",
            "hast-",
            "property-information",
            "decode-named-character-reference",
            "character-entities",
            "comma-separated-tokens",
            "space-separated-tokens",
          ];

          if (markdownPackages.some((segment) => id.indexOf(segment) >= 0)) {
            return "markdown-vendor";
          }

          if (id.indexOf("react-router-dom") >= 0 || id.indexOf("@remix-run/router") >= 0) {
            return "router-vendor";
          }

          if (id.indexOf("react-i18next") >= 0 || id.indexOf("i18next") >= 0) {
            return "i18n-vendor";
          }
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: {
      "/api": {
        target: "http://backend:5000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
