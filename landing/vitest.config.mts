import path from "node:path";
import { defineConfig } from "vitest/config";

// Cấu hình vitest cho landing app: chạy trong môi trường node (không cần DOM)
// vì các test chỉ kiểm tra parser/escaping và route handler, và ánh xạ alias
// "@" về "./src" để khớp với tsconfig.json của Next.js.
export default defineConfig({
  test: {
    environment: "node",
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
});
